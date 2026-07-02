const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const tempDir = path.join(__dirname, '../scratch');
if (!fs.existsSync(tempDir)) {
  fs.mkdirSync(tempDir);
}

const mappings = [
  {
    id: 'CgeLinkedinIndividualPosts',
    db: path.join(tempDir, 'db_CgeLinkedinIndividualPosts.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_retrieval/cge_linkedin_individual_posts.json')
  },
  {
    id: 'AiSummaryContentMarketing',
    db: path.join(tempDir, 'db_AiSummaryContentMarketing.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_summary/ai_summary_content_marketing.json')
  },
  {
    id: 'AiSummaryEvents',
    db: path.join(tempDir, 'db_AiSummaryEvents.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_summary/ai_summary_events.json')
  },
  {
    id: 'AiSummarySlack',
    db: path.join(tempDir, 'db_AiSummarySlack.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_summary/ai_summary_slack.json')
  },
  {
    id: 'AiSummarySubstack',
    db: path.join(tempDir, 'db_AiSummarySubstack.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_summary/ai_summary_substack.json')
  },
  {
    id: 'SlackApprovalCallback',
    db: path.join(tempDir, 'db_SlackApprovalCallback.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_retrieval/helpers/slack_approval_callback.json')
  },
  {
    id: 'ContentMarketingDraftsReminder',
    db: path.join(tempDir, 'db_ContentMarketingDraftsReminder.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_retrieval/content_marketing_drafts_reminder.json')
  }
];

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

function cleanWorkflow(wf) {
  const cleaned = {
    id: wf.id,
    name: wf.name,
    active: wf.active,
    settings: wf.settings || {},
    nodes: (wf.nodes || []).map(n => ({
      id: n.id,
      name: n.name,
      type: n.type,
      typeVersion: n.typeVersion,
      position: n.position,
      parameters: n.parameters || {},
      credentials: n.credentials || {}
    })).sort((a, b) => a.id.localeCompare(b.id)),
    connections: wf.connections || {}
  };
  return cleaned;
}

function isEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

let hasMismatches = false;

for (const map of mappings) {
  console.log(`\n========================================`);
  console.log(`Comparing DB: ${path.basename(map.db)} with File: ${path.basename(map.file)}`);
  if (!fs.existsSync(map.db)) {
    console.log(`DB dump not found: ${map.db}`);
    continue;
  }
  if (!fs.existsSync(map.file)) {
    console.log(`Source file not found: ${map.file}`);
    continue;
  }

  const dbData = JSON.parse(fs.readFileSync(map.db, 'utf8'));
  const fileData = JSON.parse(fs.readFileSync(map.file, 'utf8'));

  const dbClean = cleanWorkflow(dbData);
  const fileClean = cleanWorkflow(fileData);

  let fileMismatch = false;

  if (dbClean.name !== fileClean.name) {
    console.log(`Name Mismatch! DB: "${dbClean.name}" vs File: "${fileClean.name}"`);
    fileMismatch = true;
  }
  if (dbClean.active !== fileClean.active) {
    console.log(`Active Mismatch! DB: ${dbClean.active} vs File: ${fileClean.active}`);
    fileMismatch = true;
  }
  if (!isEqual(dbClean.settings, fileClean.settings)) {
    console.log(`Settings Mismatch!`);
    fileMismatch = true;
  }
  if (!isEqual(dbClean.connections, fileClean.connections)) {
    console.log(`Connections Mismatch!`);
    fileMismatch = true;
  }

  const dbNodesMap = new Map(dbClean.nodes.map(n => [n.name, n]));
  const fileNodesMap = new Map(fileClean.nodes.map(n => [n.name, n]));

  for (const name of dbNodesMap.keys()) {
    if (!fileNodesMap.has(name)) {
      console.log(`Node "${name}" exists in DB but not in File.`);
      fileMismatch = true;
    }
  }
  for (const name of fileNodesMap.keys()) {
    if (!dbNodesMap.has(name)) {
      console.log(`Node "${name}" exists in File but not in DB.`);
      fileMismatch = true;
    }
  }

  for (const [name, dbNode] of dbNodesMap.entries()) {
    const fileNode = fileNodesMap.get(name);
    if (!fileNode) continue;

    if (dbNode.type !== fileNode.type || dbNode.typeVersion !== fileNode.typeVersion) {
      console.log(`Node "${name}" type/version mismatch.`);
      fileMismatch = true;
    }

    if (!isEqual(dbNode.credentials, fileNode.credentials)) {
      console.log(`Node "${name}" credentials mismatch.`);
      fileMismatch = true;
    }

    if (!isEqual(dbNode.parameters, fileNode.parameters)) {
      const fileParamsStr = JSON.stringify(fileNode.parameters);
      
      const hasUsp = fileParamsStr.includes('usp_market_positioning.md');
      const hasContentStrategy = fileParamsStr.includes('content_strategy.md');
      
      if (hasUsp || hasContentStrategy) {
        // Expected changes
      } else {
        console.log(`Node "${name}" parameters mismatch.`);
        console.log(`  DB parameters: ${JSON.stringify(dbNode.parameters)}`);
        console.log(`  File parameters: ${fileParamsStr}`);
        fileMismatch = true;
      }
    }
  }

  if (fileMismatch) {
    hasMismatches = true;
  } else {
    console.log('No mismatches found (excluding custom markdown prompt integrations).');
  }
}

if (hasMismatches) {
  console.log('\nDifferences detected between DB and local JSON files.');
  console.log('Run `node scripts/sync-workflows.js` to update files from DB while preserving prompts.');
  process.exit(1);
} else {
  console.log('\nAll checked workflows are in sync!');
}
