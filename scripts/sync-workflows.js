const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const tempDir = path.join(__dirname, '../scratch');
if (!fs.existsSync(tempDir)) {
  fs.mkdirSync(tempDir);
}

const workflowsDir = path.join(__dirname, '../src/n8n/workflows');

function getJsonFiles(dir, files = []) {
  const list = fs.readdirSync(dir);
  for (const item of list) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      getJsonFiles(fullPath, files);
    } else if (item.endsWith('.json')) {
      files.push(fullPath);
    }
  }
  return files;
}

const jsonFiles = getJsonFiles(workflowsDir);
const mappings = jsonFiles.map(file => {
  const content = JSON.parse(fs.readFileSync(file, 'utf8'));
  
  const jsNodeNames = ['Format Context for LLM', 'Format Data for LLM', 'Format Events for LLM', 'Format Posts for LLM'];
  const llmNodeNames = ['Generate Proposal Post', 'Summarize via Ollama Cloud'];
  
  const jsNode = (content.nodes || []).find(n => jsNodeNames.some(name => name.toLowerCase() === n.name.toLowerCase()));
  const llmNode = (content.nodes || []).find(n => llmNodeNames.some(name => name.toLowerCase() === n.name.toLowerCase()));
  
  return {
    id: content.id,
    db: path.join(tempDir, `db_${content.id}.json`),
    file: file,
    jsNodeName: jsNode ? jsNode.name : undefined,
    llmNodeName: llmNode ? llmNode.name : undefined
  };
});

console.log('Dumping current workflows from local database...');
for (const map of mappings) {
  try {
    const cmd = `docker compose exec -T db psql -U jager -d n8n -t -A -c "SELECT json_build_object('id', id, 'name', name, 'nodes', nodes, 'connections', connections, 'active', active, 'settings', settings) FROM workflow_entity WHERE id = '${map.id}';"`;
    const output = execSync(cmd, { encoding: 'utf8' }).trim();
    if (output) {
      fs.writeFileSync(map.db, output);
    } else {
      console.warn(`Warning: No workflow found in DB for ID "${map.id}"`);
    }
  } catch (err) {
    console.error(`Error dumping workflow "${map.id}":`, err.message);
  }
}

for (const map of mappings) {
  console.log(`\nProcessing ${path.basename(map.file)}...`);
  if (!fs.existsSync(map.db)) {
    console.log(`DB file not found: ${map.db}`);
    continue;
  }
  if (!fs.existsSync(map.file)) {
    console.log(`File not found: ${map.file}`);
    continue;
  }

  const dbWf = JSON.parse(fs.readFileSync(map.db, 'utf8'));
  const fileWf = JSON.parse(fs.readFileSync(map.file, 'utf8'));

  if (!map.jsNodeName || !map.llmNodeName) {
    fs.writeFileSync(map.file, JSON.stringify(dbWf, null, 2) + '\n');
    console.log(`Successfully updated ${map.file} directly from DB`);
    continue;
  }

  const fileJsNode = fileWf.nodes.find(n => n.name.toLowerCase() === map.jsNodeName.toLowerCase());
  const fileLlmNode = fileWf.nodes.find(n => n.name.toLowerCase() === map.llmNodeName.toLowerCase());

  if (!fileJsNode) {
    console.error(`Error: JS node "${map.jsNodeName}" not found in File.`);
    continue;
  }
  if (!fileLlmNode) {
    console.error(`Error: LLM node "${map.llmNodeName}" not found in File.`);
    continue;
  }

  let updatedJsNode = false;
  let updatedLlmNode = false;

  for (const dbNode of dbWf.nodes) {
    if (dbNode.name.toLowerCase() === map.jsNodeName.toLowerCase()) {
      dbNode.parameters.jsCode = fileJsNode.parameters.jsCode;
      updatedJsNode = true;
    }
    if (dbNode.name.toLowerCase() === map.llmNodeName.toLowerCase()) {
      if (dbNode.parameters.messages && dbNode.parameters.messages.values && dbNode.parameters.messages.values[0]) {
        dbNode.parameters.messages.values[0].content = fileLlmNode.parameters.messages.values[0].content;
        updatedLlmNode = true;
      }
    }
  }

  if (!updatedJsNode) {
    console.error(`Error: JS node "${map.jsNodeName}" not found in DB.`);
  }
  if (!updatedLlmNode) {
    console.error(`Error: LLM node "${map.llmNodeName}" not found in DB.`);
  }

  if (updatedJsNode && updatedLlmNode) {
    fs.writeFileSync(map.file, JSON.stringify(dbWf, null, 2) + '\n');
    console.log(`Successfully merged and updated ${map.file}`);
  }
}
