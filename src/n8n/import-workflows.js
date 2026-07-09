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
          'SELECT name, nodes, connections, settings, "updatedAt", active FROM workflow_entity WHERE id = $1',
          [workflowId]
        );

        if (res.rows.length > 0) {
          const dbWorkflow = res.rows[0];
          
          if (dbWorkflow.active) {
            console.log(`Workflow "${localWorkflow.name}" (${workflowId}) is active in database. Skipping import.`);
            shouldImport = false;
          } else {
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

  // After all imports, repair any workflow that has a stale/orphaned versionId
  // with no matching workflow_published_version row.  This can happen if a
  // previous import cycle ran with active:true before this guard was added.
  await repairPublishedVersions();

  await client.end();
}

/**
 * For every workflow_entity row whose versionId does not exist in
 * workflow_published_version, find the latest real workflow_history entry and
 * insert the missing row.  This is idempotent and safe to run on every startup.
 */
async function repairPublishedVersions() {
  const n8nTableExists = await client.query(`
    SELECT EXISTS (
      SELECT FROM information_schema.tables
      WHERE table_schema = 'public'
      AND table_name = 'workflow_published_version'
    )
  `);
  if (!n8nTableExists.rows[0].exists) return;

  // Find workflows whose current versionId has no published_version record.
  const broken = await client.query(`
    SELECT we.id, we."versionId"
    FROM workflow_entity we
    LEFT JOIN workflow_published_version wpv ON wpv."workflowId" = we.id
    WHERE wpv."workflowId" IS NULL
  `);

  if (broken.rows.length === 0) return;

  console.log(`Repairing workflow_published_version for ${broken.rows.length} workflow(s)...`);

  for (const row of broken.rows) {
    const workflowId = row.id;

    // Find the latest non-autosaved history entry for this workflow.
    const histRes = await client.query(`
      SELECT "versionId" FROM workflow_history
      WHERE "workflowId" = $1
      ORDER BY "createdAt" DESC
      LIMIT 1
    `, [workflowId]);

    if (histRes.rows.length === 0) {
      console.warn(`  Skipping ${workflowId}: no workflow_history entries found.`);
      continue;
    }

    const latestVersionId = histRes.rows[0].versionId;
    const now = new Date().toISOString();

    // Sync workflow_entity.versionId to the real latest history entry.
    await client.query(
      `UPDATE workflow_entity SET "versionId" = $1 WHERE id = $2`,
      [latestVersionId, workflowId]
    );

    // Insert the missing workflow_published_version row.
    await client.query(
      `INSERT INTO workflow_published_version ("workflowId", "publishedVersionId", "createdAt", "updatedAt")
       VALUES ($1, $2, $3, $3)
       ON CONFLICT DO NOTHING`,
      [workflowId, latestVersionId, now]
    );

    console.log(`  Repaired ${workflowId} → publishedVersionId=${latestVersionId}`);
  }
}

function importWorkflow(filePath) {
  let importPath = filePath;
  let tempPath = null;
  try {
    // Strip tags and force active:false before importing.
    //
    // WHY active:false: n8n 2.29+ uses a workflow_published_version table to
    // track the live published version snapshot. When `n8n import:workflow`
    // imports a workflow with active:true it writes a versionId to
    // workflow_entity but does NOT create the matching workflow_published_version
    // row, leaving an orphaned versionId. The UI then throws
    // "Workflow could not be published: Version not found" because the publish
    // path looks up that row and finds nothing.
    //
    // By always importing as inactive the CLI skips the activation path
    // entirely. workflow_published_version gets populated correctly the first
    // time the user (or our repair step below) activates the workflow through
    // the proper n8n activation path.
    const workflowData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    const needsTemp = (workflowData.tags && workflowData.tags.length > 0) || workflowData.active === true;
    if (needsTemp) {
      const stripped = { ...workflowData, tags: [], active: false };
      tempPath = filePath + '.tmp.json';
      fs.writeFileSync(tempPath, JSON.stringify(stripped));
      importPath = tempPath;
    }
  } catch (err) {
    console.warn(`Could not strip tags/active from ${filePath}, importing as-is:`, err.message);
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
