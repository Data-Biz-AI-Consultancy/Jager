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
    file: path.join(__dirname, '../src/n8n/workflows/ai_retrieval/cge_linkedin_individual_posts.json'),
    jsNodeName: 'Format Context for LLM',
    llmNodeName: 'Generate Proposal Post'
  },
  {
    id: 'AiSummaryContentMarketing',
    db: path.join(tempDir, 'db_AiSummaryContentMarketing.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_summary/ai_summary_content_marketing.json'),
    jsNodeName: 'Format Data for LLM',
    llmNodeName: 'Summarize via Ollama Cloud'
  },
  {
    id: 'AiSummaryEvents',
    db: path.join(tempDir, 'db_AiSummaryEvents.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_summary/ai_summary_events.json'),
    jsNodeName: 'Format Events for LLM',
    llmNodeName: 'Summarize via Ollama Cloud'
  },
  {
    id: 'AiSummarySlack',
    db: path.join(tempDir, 'db_AiSummarySlack.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_summary/ai_summary_slack.json'),
    jsNodeName: 'Format Posts for LLM',
    llmNodeName: 'Summarize via Ollama Cloud'
  },
  {
    id: 'AiSummarySubstack',
    db: path.join(tempDir, 'db_AiSummarySubstack.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_summary/ai_summary_substack.json'),
    jsNodeName: 'Format Posts for LLM',
    llmNodeName: 'Summarize via Ollama Cloud'
  },
  {
    id: 'SlackApprovalCallback',
    db: path.join(tempDir, 'db_SlackApprovalCallback.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_summary/slack_approval_callback.json')
  },
  {
    id: 'ContentMarketingDraftsReminder',
    db: path.join(tempDir, 'db_ContentMarketingDraftsReminder.json'),
    file: path.join(__dirname, '../src/n8n/workflows/ai_summary/content_marketing_drafts_reminder.json')
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
