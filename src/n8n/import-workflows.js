const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const pgPath = require.resolve('pg', { paths: ['/usr/local/lib/node_modules/n8n'] });
const { Client } = require(pgPath);

const client = new Client({
  host: process.env.DB_POSTGRESDB_HOST || 'db',
  port: parseInt(process.env.DB_POSTGRESDB_PORT || '5432', 10),
  database: process.env.DB_POSTGRESDB_DATABASE || 'n8n',
  user: process.env.DB_POSTGRESDB_USER || 'jager',
  password: process.env.DB_POSTGRESDB_PASSWORD || 'jager',
});

function isEqual(obj1, obj2) {
  if (obj1 === obj2) return true;
  if (obj1 == null || obj2 == null) return obj1 === obj2;
  if (typeof obj1 !== typeof obj2) return false;
  if (typeof obj1 !== 'object') return obj1 === obj2;
  
  if (Array.isArray(obj1)) {
    if (!Array.isArray(obj2) || obj1.length !== obj2.length) return false;
    for (let i = 0; i < obj1.length; i++) {
      if (!isEqual(obj1[i], obj2[i])) return false;
    }
    return true;
  }
  
  if (Array.isArray(obj2)) return false;
  
  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);
  
  if (keys1.length !== keys2.length) return false;
  
  for (const key of keys1) {
    if (!keys2.includes(key) || !isEqual(obj1[key], obj2[key])) return false;
  }
  
  return true;
}

function getJsonFilesRecursively(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  list.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    if (stat && stat.isDirectory()) {
      results = results.concat(getJsonFilesRecursively(filePath));
    } else if (file.endsWith('.json')) {
      results.push(filePath);
    }
  });
  return results;
}

async function run() {
  await client.connect();

  const tableCheck = await client.query(`
    SELECT EXISTS (
      SELECT FROM information_schema.tables 
      WHERE table_schema = 'public' 
      AND table_name = 'workflow_entity'
    )
  `);

  const tableExists = tableCheck.rows[0].exists;

  const workflowsDir = '/etc/n8n/workflows';
  if (!fs.existsSync(workflowsDir)) {
    console.log('Workflows directory not found, skipping workflow import.');
    await client.end();
    return;
  }

  const filePaths = getJsonFilesRecursively(workflowsDir);

  for (const filePath of filePaths) {
    const file = path.basename(filePath);
    let localWorkflow;
    try {
      localWorkflow = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (err) {
      console.error(`Error parsing JSON file ${file}:`, err.message);
      continue;
    }

    const workflowId = localWorkflow.id;
    if (!workflowId) {
      console.log(`Workflow file ${file} does not have an ID. Importing...`);
      importWorkflow(filePath);
      continue;
    }

    let shouldImport = true;

    if (tableExists) {
      try {
        const res = await client.query(
          'SELECT name, nodes, connections, settings, "updatedAt" FROM workflow_entity WHERE id = $1',
          [workflowId]
        );

        if (res.rows.length > 0) {
          const dbWorkflow = res.rows[0];
          const nodesMatch = isEqual(localWorkflow.nodes, dbWorkflow.nodes);
          const connectionsMatch = isEqual(localWorkflow.connections, dbWorkflow.connections);
          const settingsMatch = isEqual(localWorkflow.settings || {}, dbWorkflow.settings || {});
          const nameMatch = localWorkflow.name === dbWorkflow.name;

          if (nodesMatch && connectionsMatch && settingsMatch && nameMatch) {
            console.log(`Workflow "${localWorkflow.name}" (${workflowId}) already exists in database and is up-to-date. Skipping import.`);
            shouldImport = false;
          } else {
            const isProduction = process.env.N8N_ENV === 'production';
            if (!isProduction) {
              console.log(`Workflow "${localWorkflow.name}" (${workflowId}) has local changes. In development, forcing import.`);
            } else {
              const dbUpdatedAt = dbWorkflow.updatedAt ? new Date(dbWorkflow.updatedAt) : new Date(0);
              const fileStats = fs.statSync(filePath);
              const fileMtime = new Date(fileStats.mtime);

              if (fileMtime > dbUpdatedAt) {
                console.log(`Workflow "${localWorkflow.name}" (${workflowId}) has local changes and Git file is newer (File: ${fileMtime.toISOString()} > DB: ${dbUpdatedAt.toISOString()}). Importing.`);
              } else {
                console.log(`Workflow "${localWorkflow.name}" (${workflowId}) has local differences but database version is newer (DB: ${dbUpdatedAt.toISOString()} >= File: ${fileMtime.toISOString()}). Skipping import to preserve newer changes.`);
                shouldImport = false;
              }
            }
          }
        } else {
          console.log(`Workflow "${localWorkflow.name}" (${workflowId}) does not exist in database. Importing.`);
        }
      } catch (err) {
        console.error(`Error querying database for workflow ${workflowId}:`, err.message);
      }
    } else {
      console.log(`workflow_entity table does not exist yet. Importing "${localWorkflow.name}"...`);
    }

    if (shouldImport) {
      importWorkflow(filePath);
    }
  }

  await client.end();
}

function importWorkflow(filePath) {
  let importPath = filePath;
  let tempPath = null;
  try {
    // Strip tags from workflow JSON to avoid FK violations on workflows_tags
    // (tags are UI-managed state; tag IDs in JSON may not exist in the n8n DB)
    const workflowData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    if (workflowData.tags && workflowData.tags.length > 0) {
      const stripped = { ...workflowData, tags: [] };
      tempPath = filePath + '.tmp.json';
      fs.writeFileSync(tempPath, JSON.stringify(stripped));
      importPath = tempPath;
    }
  } catch (err) {
    console.warn(`Could not strip tags from ${filePath}, importing as-is:`, err.message);
  }

  try {
    console.log(`Importing workflow: ${filePath}`);
    execSync(`n8n import:workflow --input "${importPath}"`, { stdio: 'inherit' });
  } catch (err) {
    console.error(`Failed to import workflow ${filePath}:`, err.message);
  } finally {
    if (tempPath && fs.existsSync(tempPath)) {
      fs.unlinkSync(tempPath);
    }
  }
}

run().catch(err => {
  console.error('Fatal error in import-workflows script:', err);
  process.exit(1);
});
