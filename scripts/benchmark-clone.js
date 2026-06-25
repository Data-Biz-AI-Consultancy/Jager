#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');

const PROD_JAGER_URL = process.env.PROD_DATABASE_URL || "postgresql://jager:jager@192.168.178.164:5432/jager";
const PROD_N8N_URL = PROD_JAGER_URL.replace(/\/jager(\?|$)/, '/n8n$1');

let dockerComposeCmd = 'docker compose';
try {
  execSync('docker compose version', { stdio: 'ignore' });
} catch (e) {
  dockerComposeCmd = 'docker-compose';
}

// Table list for n8n to benchmark (from \dt output)
const allTables = [
  'agent_chat_subscriptions', 'agent_checkpoints', 'agent_execution', 'agent_execution_threads',
  'agent_files', 'agent_history', 'agent_task_definition', 'agent_task_run_lock',
  'agent_task_snapshot', 'agents', 'agents_memory_entries', 'agents_memory_entry_cursors',
  'agents_memory_entry_locks', 'agents_memory_entry_sources', 'agents_messages',
  'agents_observation_cursors', 'agents_observation_locks', 'agents_observations',
  'agents_resources', 'agents_threads', 'ai_builder_temporary_workflow', 'annotation_tag_entity',
  'auth_identity', 'auth_provider_sync_history', 'binary_data', 'chat_hub_tools', 'data_table',
  'data_table_column', 'deployment_key', 'dynamic_credential_resolver', 'evaluation_collection',
  'evaluation_config', 'event_destinations', 'execution_annotation_tags', 'execution_annotations',
  'execution_data', 'execution_metadata', 'folder', 'folder_tag', 'insights_by_period',
  'insights_metadata', 'insights_raw', 'installed_nodes', 'installed_packages', 'instance_ai_checkpoints',
  'instance_ai_iteration_logs', 'instance_ai_messages', 'instance_ai_observation_cursors',
  'instance_ai_observation_locks', 'instance_ai_observational_memory', 'instance_ai_observations',
  'instance_ai_pending_confirmations', 'instance_ai_resources', 'instance_ai_run_snapshots',
  'instance_ai_threads', 'instance_ai_workflow_snapshots', 'instance_version_history',
  'invalid_auth_token', 'mcp_registry_server', 'migrations', 'oauth_access_tokens',
  'oauth_authorization_codes', 'oauth_clients', 'oauth_refresh_tokens', 'oauth_user_consents',
  'processed_data', 'project', 'project_relation', 'project_secrets_provider_access', 'role',
  'role_mapping_rule', 'role_mapping_rule_project', 'role_scope', 'scope', 'secrets_provider_connection',
  'settings', 'shared_workflow', 'tag_entity', 'test_case_execution', 'test_run', 'token_exchange_jti',
  'trusted_key', 'trusted_key_source', 'user', 'user_api_keys', 'user_favorites', 'variables',
  'webhook_entity', 'workflow_builder_session', 'workflow_dependency', 'workflow_entity',
  'workflow_history', 'workflow_publication_outbox', 'workflow_publish_history',
  'workflow_published_version', 'workflow_statistics', 'workflows_tags'
];

// Tables that clone-db.js excludes data for (or truncates)
const excludedTables = [
  'credentials_entity', 'shared_credentials', 'chat_hub_sessions', 'chat_hub_agents',
  'credential_dependency', 'dynamic_credential_entry', 'dynamic_credential_user_entry',
  'instance_ai_mcp_registry_connections', 'chat_hub_agent_tools', 'chat_hub_messages',
  'chat_hub_session_tools', 'execution_entity'
];

const tablesToClone = allTables.filter(t => !excludedTables.includes(t));

console.log(`Starting benchmark for cloning n8n database...`);
console.log(`Production URL: ${PROD_N8N_URL}`);
console.log(`Number of tables to clone in table-by-table approach: ${tablesToClone.length}`);

// Helper to terminate connections & recreate DB
function resetLocalDb(dbName) {
  try {
    execSync(
      `${dockerComposeCmd} exec -T db psql -U jager -d postgres -c ` +
      `"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${dbName}' AND pid <> pg_backend_pid();"`,
      { stdio: 'ignore' }
    );
  } catch (e) {}
  execSync(`${dockerComposeCmd} exec -T db psql -U jager -d postgres -c "DROP DATABASE IF EXISTS ${dbName};"`, { stdio: 'ignore' });
  execSync(`${dockerComposeCmd} exec -T db psql -U jager -d postgres -c "CREATE DATABASE ${dbName};"`, { stdio: 'ignore' });
}

// ----------------------------------------------------
// BENCHMARK 1: Standard Full DB Clone (Directory Format)
// ----------------------------------------------------
function runStandardClone() {
  console.log('\n--- Running Benchmark 1: Standard Full DB Clone (Directory Format) ---');
  resetLocalDb('n8n');
  const tempDir = '/tmp/n8n_full_dump';
  try {
    execSync(`${dockerComposeCmd} exec -T db rm -rf ${tempDir}`, { stdio: 'ignore' });
  } catch (e) {}

  const start = Date.now();

  // Dump
  console.log('Dumping production database...');
  let dumpCmd = `${dockerComposeCmd} exec -T db pg_dump -Fd -j 4 -Z 0 -d "${PROD_N8N_URL}" --no-owner --no-privileges`;
  excludedTables.forEach(t => {
    dumpCmd += ` --exclude-table-data=${t}`;
  });
  dumpCmd += ` -f ${tempDir}`;
  execSync(dumpCmd, { stdio: 'inherit' });

  // Restore
  console.log('Restoring to local database...');
  execSync(`${dockerComposeCmd} exec -T db pg_restore -U jager -d n8n -j 4 --no-owner --no-privileges ${tempDir}`, { stdio: 'inherit' });

  const duration = Date.now() - start;
  console.log(`Standard Full Clone completed in: ${(duration / 1000).toFixed(2)}s`);

  // Cleanup
  try {
    execSync(`${dockerComposeCmd} exec -T db rm -rf ${tempDir}`, { stdio: 'ignore' });
  } catch (e) {}

  return duration;
}

// ----------------------------------------------------
// BENCHMARK 2: Table-by-Table Clone
// ----------------------------------------------------
function runTableByTableClone() {
  console.log('\n--- Running Benchmark 2: Table-by-Table Data Sync ---');
  resetLocalDb('n8n');
  const tempDir = '/tmp/n8n_table_dump';
  try {
    execSync(`${dockerComposeCmd} exec -T db rm -rf ${tempDir}`, { stdio: 'ignore' });
  } catch (e) {}
  execSync(`${dockerComposeCmd} exec -T db mkdir -p ${tempDir}`, { stdio: 'ignore' });

  const start = Date.now();

  // Step 1: Dump and restore schema only (definitions, types, tables)
  console.log('Dumping production schema (definitions only)...');
  execSync(`${dockerComposeCmd} exec -T db pg_dump --schema-only -Fd -d "${PROD_N8N_URL}" --no-owner --no-privileges -f ${tempDir}/schema`, { stdio: 'inherit' });
  
  console.log('Restoring schema to local database...');
  execSync(`${dockerComposeCmd} exec -T db pg_restore -U jager -d n8n --no-owner --no-privileges ${tempDir}/schema`, { stdio: 'inherit' });

  // Step 2: Disable triggers/constraints to avoid foreign key violations during out-of-order table-by-table restore
  console.log('Disabling triggers on local database tables...');
  tablesToClone.forEach(t => {
    try {
      execSync(`${dockerComposeCmd} exec -T db psql -U jager -d n8n -c "ALTER TABLE \\"${t}\\" DISABLE TRIGGER ALL;"`, { stdio: 'ignore' });
    } catch (e) {
      // Ignore if some tables are views or don't support triggers
    }
  });

  // Step 3: Dump and restore table data one-by-one (Benchmark sequential)
  console.log('Syncing data table by table...');
  let idx = 0;
  for (const table of tablesToClone) {
    idx++;
    console.log(`[${idx}/${tablesToClone.length}] Syncing table data: ${table}...`);
    try {
      // Dump data only for this specific table
      execSync(
        `${dockerComposeCmd} exec -T db pg_dump -a -t "\\"${table}\\"" -Fc -d "${PROD_N8N_URL}" --no-owner --no-privileges -f ${tempDir}/${table}.dump`,
        { stdio: 'ignore' }
      );
      // Restore data only for this specific table
      execSync(
        `${dockerComposeCmd} exec -T db pg_restore -a -U jager -d n8n --no-owner --no-privileges ${tempDir}/${table}.dump`,
        { stdio: 'ignore' }
      );
    } catch (err) {
      console.error(`Failed to sync data for table ${table}: ${err.message}`);
    }
  }

  // Step 4: Re-enable triggers/constraints
  console.log('Re-enabling triggers on local database tables...');
  tablesToClone.forEach(t => {
    try {
      execSync(`${dockerComposeCmd} exec -T db psql -U jager -d n8n -c "ALTER TABLE \\"${t}\\" ENABLE TRIGGER ALL;"`, { stdio: 'ignore' });
    } catch (e) {}
  });

  const duration = Date.now() - start;
  console.log(`Table-by-table Clone completed in: ${(duration / 1000).toFixed(2)}s`);

  // Cleanup
  try {
    execSync(`${dockerComposeCmd} exec -T db rm -rf ${tempDir}`, { stdio: 'ignore' });
  } catch (e) {}

  return duration;
}

async function run() {
  const timeFull = runStandardClone();
  const timeTable = runTableByTableClone();

  console.log('\n=========================================');
  console.log('BENCHMARK RESULTS');
  console.log('=========================================');
  console.log(`Standard Full Clone:  ${(timeFull / 1000).toFixed(2)}s`);
  console.log(`Table-by-table Clone: ${(timeTable / 1000).toFixed(2)}s`);
  console.log(`Difference:           ${((timeTable - timeFull) / 1000).toFixed(2)}s (${(timeTable / timeFull).toFixed(1)}x slower)`);
  console.log('=========================================');
}

run().catch(err => {
  console.error('Benchmark failed:', err);
  process.exit(1);
});
