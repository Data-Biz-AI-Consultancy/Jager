#!/usr/bin/env node

const { exec, execSync } = require('child_process');
const { promisify } = require('util');
const fs = require('fs');
const os = require('os');

const execAsync = promisify(exec);

// Load .env manually if present
if (fs.existsSync('.env')) {
  const envContent = fs.readFileSync('.env', 'utf8');
  for (const line of envContent.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const match = trimmed.match(/^([^=]+)=(.*)$/);
    if (match) {
      const key = match[1].trim();
      let val = match[2].trim();
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      if (!process.env[key]) {
        process.env[key] = val;
      }
    }
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Run a shell command asynchronously, printing stdout/stderr with an optional
 * [tag] prefix so interleaved parallel output stays readable.
 */
async function run(cmd, tag = '') {
  const prefix = tag ? `[${tag}] ` : '';
  const { stdout, stderr } = await execAsync(cmd, { maxBuffer: 100 * 1024 * 1024 });
  if (stdout) stdout.trim().split('\n').forEach(l => console.log(`${prefix}${l}`));
  if (stderr) stderr.trim().split('\n').forEach(l => console.error(`${prefix}${l}`));
}

/**
 * Poll pg_isready every second until PostgreSQL accepts connections or we time out.
 * Replaces the blind `sleep 5`.
 */
async function waitForPostgres(dockerComposeCmd, timeoutSeconds = 30) {
  console.log('Waiting for PostgreSQL to be ready...');
  for (let i = 0; i < timeoutSeconds; i++) {
    try {
      await execAsync(`${dockerComposeCmd} exec -T db pg_isready -U jager`, {
        maxBuffer: 1 * 1024 * 1024,
      });
      console.log('PostgreSQL is ready!');
      return;
    } catch {
      await new Promise(r => setTimeout(r, 1000));
    }
  }
  throw new Error(`PostgreSQL did not become ready after ${timeoutSeconds}s.`);
}

// ─── Usage ────────────────────────────────────────────────────────────────────

// ─── Usage ────────────────────────────────────────────────────────────────────

function usage() {
  console.log(`
Usage: node scripts/clone-db.js <PROD_DATABASE_URL> [options]

Options:
  --skip-n8n                  Skip cloning 'n8n' database
  --skip-cdp                  Skip cloning 'cdp' database
  --skip-jager                Skip cloning 'jager' database
  --jager-only                Only clone 'jager' database
  --n8n-only                  Only clone 'n8n' database
  --cdp-only                  Only clone 'cdp' database
  --include-history           Include n8n execution log table data (execution_entity,
                              execution_data, execution_metadata). By default these
                              tables are skipped as they can be very large.
  --jobs <N>                  Number of parallel pg_dump/pg_restore jobs per database.
                              Defaults to floor(cpu_count / 2), min 2, max 8.

Examples:
  node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager"
  node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --skip-n8n
  node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --exclude-history --jobs 4
`);
  process.exit(1);
}

// ─── Arg Parsing ──────────────────────────────────────────────────────────────

const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) usage();

const connectionString = args.find(
  a => a.startsWith('postgres://') || a.startsWith('postgresql://') || a.includes('@')
);
const cdpOnly        = args.includes('--cdp-only');
const n8nOnly        = args.includes('--n8n-only');
const jagerOnly      = args.includes('--jager-only');

const skipN8N        = args.includes('--skip-n8n') || jagerOnly || cdpOnly;
const skipCDP        = args.includes('--skip-cdp') || jagerOnly || n8nOnly;
const skipJager      = args.includes('--skip-jager') || n8nOnly || cdpOnly;

const includeHistory = args.includes('--include-history');
const excludeHistory = !includeHistory; // excluded by default; use --include-history to opt in

// --jobs N: auto-detect sensible default from CPU count
const jobsIdx    = args.findIndex(a => a === '--jobs');
const cpuCount   = os.cpus().length;
const autoJobs   = Math.min(8, Math.max(2, Math.floor(cpuCount / 2)));
const numJobs    = (jobsIdx !== -1 && args[jobsIdx + 1])
  ? (parseInt(args[jobsIdx + 1], 10) || autoJobs)
  : autoJobs;

// ─── URLs ─────────────────────────────────────────────────────────────────────

let PROD_JAGER_URL      = connectionString || process.env.PROD_DATABASE_URL || process.env.PROD_JAGER_URL;
let PROD_N8N_URL        = process.env.PROD_N8N_URL;
let PROD_CDP_URL        = process.env.PROD_CDP_URL;

if (PROD_JAGER_URL) {
  try {
    const urlObj = new URL(PROD_JAGER_URL);
    if (!PROD_N8N_URL) {
      urlObj.pathname = '/n8n';
      PROD_N8N_URL = urlObj.toString();
    }
    if (!PROD_CDP_URL) {
      urlObj.pathname = '/cdp';
      PROD_CDP_URL = urlObj.toString();
    }
  } catch {
    if (!PROD_N8N_URL) PROD_N8N_URL = PROD_JAGER_URL.replace(/\/jager(\?|$)/, '/n8n$1');
    if (!PROD_CDP_URL) PROD_CDP_URL = PROD_JAGER_URL.replace(/\/jager(\?|$)/, '/cdp$1');
  }
}

if (!PROD_JAGER_URL) {
  console.error('Error: No production database URL provided.');
  usage();
}

if (!fs.existsSync('docker-compose.yml')) {
  console.error('Error: docker-compose.yml not found. Please run this script from the project root.');
  process.exit(1);
}

// ─── Docker Compose Detection (sync — runs before any async work) ─────────────

let dockerComposeCmd = 'docker compose';
try {
  execSync('docker compose version', { stdio: 'ignore' });
} catch {
  try {
    execSync('docker-compose version', { stdio: 'ignore' });
    dockerComposeCmd = 'docker-compose';
  } catch {
    console.error("Error: Neither 'docker compose' nor 'docker-compose' found.");
    process.exit(1);
  }
}

// ─── Clone Function ───────────────────────────────────────────────────────────

/**
 * Clone a single production PostgreSQL database into the local Docker environment.
 *
 * Uses pg_dump -Fd (directory format) with -j parallel workers for the dump,
 * then pg_restore -Fd -j for the restore. Both phases are tagged in log output
 * so interleaved output from parallel runs stays readable.
 */
async function cloneDatabase(dbName, prodUrl) {
  const tag    = dbName;
  const log    = msg => console.log(`[${tag}] ${msg}`);
  const tempDir = `/tmp/${dbName}_prod_dump`;

  log('=========================================');
  log(`Cloning Database: ${dbName}`);
  log(`Parallelism: -j ${numJobs}  (${cpuCount} CPUs detected)`);
  log('=========================================');


  // credentials_entity is always excluded from n8n dumps — production credentials
  // should never land in the local environment.
  const alwaysExcluded = dbName === 'n8n'
    ? ['--exclude-table-data=credentials_entity']
    : [];

  // Execution log tables are excluded by default (they can be multi-GB).
  // Pass --include-history to include them.
  const historyExcluded = (dbName === 'n8n' && excludeHistory)
    ? [
        '--exclude-table-data=execution_entity',
        '--exclude-table-data=execution_data',
        '--exclude-table-data=execution_metadata',
      ]
    : [];

  const exclusions = [...alwaysExcluded, ...historyExcluded].join(' ');

  if (alwaysExcluded.length) log('Excluding credentials_entity (production credentials are never cloned locally).');
  if (historyExcluded.length) log('Excluding execution log table data: execution_entity, execution_data, execution_metadata.');

  try {
    // ── Pre-clean: remove any stale temp dir from a previous failed run ────
    try {
      await run(`${dockerComposeCmd} exec -T db rm -rf ${tempDir}`, tag);
    } catch {
      // Ignore — dir may not exist yet
    }

    // ── Step 1: Dump into directory format ──────────────────────────────────
    log(`Dumping production → ${tempDir}  (format: directory, -j ${numJobs})...`);
    await run(
      `${dockerComposeCmd} exec -T db pg_dump -Fd -j ${numJobs}` +
        ` -d "${prodUrl}" --no-owner --no-privileges ${exclusions} -f ${tempDir}`,
      tag
    );

    // ── Step 2: Clean existing database schema (without dropping database) ──
    // We only drop 'public' and s_* schemas. The 'cdp' schema is intentionally
    // preserved so that GUI IDE connections (PostgreSQL Explorer) bound to
    // cdp/scratch.pgsql never lose their connection handle.
    log(`Clearing existing schemas in local database ${dbName}...`);
    if (dbName === 'jager') {
      // Enumerate and drop all s_* schemas (ODS layer) plus public; leave cdp alone.
      await run(
        `${dockerComposeCmd} exec -T db psql -U jager -d ${dbName} -tAc ` +
          `"SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 's\\_%' OR schema_name = 'public'"`,
        tag
      ).catch(() => {});
      await run(
        `${dockerComposeCmd} exec -T db psql -U jager -d ${dbName} -c ` +
          `"DO \\$\\$ DECLARE r RECORD; BEGIN FOR r IN SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 's\\_%%' LOOP EXECUTE 'DROP SCHEMA IF EXISTS ' || quote_ident(r.schema_name) || ' CASCADE'; END LOOP; END \\$\\$; DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"`,
        tag
      );
    } else {
      // n8n and cdp databases: drop public + cdp schemas as before
      await run(
        `${dockerComposeCmd} exec -T db psql -U jager -d ${dbName}` +
          ` -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; DROP SCHEMA IF EXISTS cdp CASCADE;"`,
        tag
      );
    }

    // ── Step 4: Restore with pg_restore -Fd -j ───────────────────────────────
    log(`Restoring → local ${dbName}  (-j ${numJobs})...`);
    try {
      await run(
        `${dockerComposeCmd} exec -T db pg_restore -Fd -j ${numJobs}` +
          ` --no-owner --no-privileges -U jager -d ${dbName} ${tempDir}`,
        tag
      );
    } catch (err) {
      // pg_restore exits with code 1 when there are non-fatal warnings, e.g. FK
      // constraint failures caused by intentionally-excluded tables (credentials_entity).
      // The data is still fully restored — only the constraint declarations failed.
      if (err.stderr && err.stderr.includes('errors ignored on restore')) {
        console.error(`[${tag}] pg_restore finished with warnings (see above) — continuing.`);
      } else {
        throw err;
      }
    }

    // ── Step 5: Credential FK cleanup (n8n only) & Schema initialization (cdp only) ─────
    if (dbName === 'n8n') {
      log('Cleaning up credential FK references (credentials intentionally excluded)...');
      try {
        await run(
          `${dockerComposeCmd} exec -T db psql -U jager -d n8n -c ` +
            `'UPDATE public.chat_hub_sessions SET "credentialId" = NULL WHERE "credentialId" IS NOT NULL;` +
            ` DELETE FROM public.shared_credentials;` +
            ` DELETE FROM public.credential_dependency;` +
            ` DELETE FROM public.dynamic_credential_entry;` +
            ` DELETE FROM public.dynamic_credential_user_entry;` +
            ` DELETE FROM public.instance_ai_mcp_registry_connections;'`,
          tag
        );
        log('Credential FK cleanup complete.');
      } catch (err) {
        console.error(`[${tag}] Warning: credential FK cleanup failed:`, err.message);
      }
    }

    if (dbName === 'cdp') {
      log('Ensuring cdp schema and tables exist in local cdp database...');
      try {
        await run(
          `${dockerComposeCmd} exec -T db psql -U jager -d cdp -c "` +
            `CREATE EXTENSION IF NOT EXISTS pgcrypto; ` +
            `CREATE SCHEMA IF NOT EXISTS cdp; ` +
            `CREATE TABLE IF NOT EXISTS cdp.client_accounts (` +
              `id UUID PRIMARY KEY DEFAULT gen_random_uuid(), ` +
              `company_name VARCHAR(255) NOT NULL, ` +
              `domain VARCHAR(255) UNIQUE, ` +
              `status VARCHAR(50) DEFAULT 'prospect', ` +
              `attributes JSONB DEFAULT '{}'::jsonb, ` +
              `created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), ` +
              `updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()` +
            `); ` +
            `CREATE TABLE IF NOT EXISTS cdp.persons (` +
              `id UUID PRIMARY KEY DEFAULT gen_random_uuid(), ` +
              `first_name VARCHAR(255), ` +
              `last_name VARCHAR(255), ` +
              `primary_email VARCHAR(255) UNIQUE, ` +
              `primary_phone VARCHAR(100), ` +
              `linkedin_url VARCHAR(2048), ` +
              `city VARCHAR(100), ` +
              `country VARCHAR(100), ` +
              `primary_client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL, ` +
              `status VARCHAR(50) DEFAULT 'active', ` +
              `attributes JSONB DEFAULT '{}'::jsonb, ` +
              `created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), ` +
              `updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()` +
            `); ` +
            `CREATE TABLE IF NOT EXISTS cdp.leads (` +
              `id UUID PRIMARY KEY DEFAULT gen_random_uuid(), ` +
              `person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL, ` +
              `full_name VARCHAR(255), ` +
              `description TEXT, ` +
              `rate VARCHAR(100), ` +
              `status VARCHAR(50) DEFAULT 'new', ` +
              `source VARCHAR(100) NOT NULL DEFAULT 'manual', ` +
              `raw_payload JSONB DEFAULT '{}'::jsonb, ` +
              `intake_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), ` +
              `updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()` +
            `); ` +
            `CREATE TABLE IF NOT EXISTS cdp.person_account_relationships (` +
              `id UUID PRIMARY KEY DEFAULT gen_random_uuid(), ` +
              `person_id UUID NOT NULL REFERENCES cdp.persons(id) ON DELETE CASCADE, ` +
              `client_account_id UUID NOT NULL REFERENCES cdp.client_accounts(id) ON DELETE CASCADE, ` +
              `job_title VARCHAR(255), ` +
              `department VARCHAR(100), ` +
              `role_type VARCHAR(50) DEFAULT 'decision_maker', ` +
              `is_primary BOOLEAN DEFAULT TRUE, ` +
              `start_date DATE, ` +
              `end_date DATE, ` +
              `status VARCHAR(50) DEFAULT 'active', ` +
              `created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), ` +
              `updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), ` +
              `UNIQUE (person_id, client_account_id, role_type)` +
            `); ` +
            `CREATE TABLE IF NOT EXISTS cdp.engagements (` +
              `id UUID PRIMARY KEY DEFAULT gen_random_uuid(), ` +
              `person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL, ` +
              `client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL, ` +
              `engagement_type VARCHAR(50) NOT NULL, ` +
              `direction VARCHAR(20) DEFAULT 'inbound', ` +
              `subject VARCHAR(1024), ` +
              `summary_or_content TEXT, ` +
              `channel VARCHAR(100), ` +
              `status VARCHAR(50) DEFAULT 'completed', ` +
              `occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), ` +
              `metadata JSONB DEFAULT '{}'::jsonb, ` +
              `created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(), ` +
              `updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()` +
            `); ` +
            `ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS primary_client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL; ` +
            `ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS in_linkedin_connections BOOLEAN DEFAULT FALSE; ` +
            `ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS in_substack_subscriber_export BOOLEAN DEFAULT FALSE; ` +
            `ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL; ` +
            `ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL;"`,
          tag
        );
        log('cdp schema and tables verified/created successfully.');
      } catch (err) {
        console.error(`[${tag}] Warning: cdp schema initialization failed:`, err.message);
      }
    }

    log(`Successfully cloned ${dbName}!`);

  } catch (error) {
    console.error(`[${tag}] Error cloning database ${dbName}:`, error.message);
    throw error;
  } finally {
    // Clean up temp directory inside the container
    try {
      await run(`${dockerComposeCmd} exec -T db rm -rf ${tempDir}`, tag);
    } catch {
      // Ignore cleanup errors
    }
  }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

(async () => {
  // Ensure local DB container is running
  let dbStatus = '';
  try {
    dbStatus = execSync(`${dockerComposeCmd} ps -q db`, { encoding: 'utf8' }).trim();
  } catch {
    // Container not started
  }

  if (!dbStatus) {
    console.log('Local database container (db) is not running. Starting services...');
    execSync(`${dockerComposeCmd} up -d db`, { stdio: 'inherit' });
    await waitForPostgres(dockerComposeCmd);
  }

  // ── Backup dev n8n credentials before clone ───────────────────────────────
  // credentials_entity is excluded from the production dump (security).
  // We snapshot the local dev credentials into a dedicated `n8n_backup` PostgreSQL
  // database (lives in the same pgdata volume — no temp files, survives restarts).
  let credBackupExists = false;
  if (!skipN8N && PROD_N8N_URL) {
    try {
      // Check how many credentials exist locally before bothering with a backup
      const { stdout: countOut } = await execAsync(
        `${dockerComposeCmd} exec -T db psql -U jager -d n8n -tAc "SELECT COUNT(*) FROM credentials_entity;"`,
        { maxBuffer: 1 * 1024 * 1024 }
      );
      const credCount = parseInt(countOut.trim(), 10) || 0;

      if (credCount > 0) {
        console.log(`Backing up ${credCount} dev credential(s) into n8n_backup database...`);
        // 1. Recreate the backup database
        await execAsync(
          `${dockerComposeCmd} exec -T db psql -U jager -d postgres ` +
            `-c "DROP DATABASE IF EXISTS n8n_backup;" ` +
            `-c "CREATE DATABASE n8n_backup;"`,
          { maxBuffer: 1 * 1024 * 1024 }
        );
        // 2. Dump credentials tables (schema + data) to a file inside the container
        await execAsync(
          `${dockerComposeCmd} exec -T db pg_dump -U jager -d n8n ` +
            `--table=credentials_entity --table=shared_credentials ` +
            `-f /tmp/n8n_cred_backup.sql`,
          { maxBuffer: 50 * 1024 * 1024 }
        );
        // 3. Load into n8n_backup
        await execAsync(
          `${dockerComposeCmd} exec -T db psql -U jager -d n8n_backup -f /tmp/n8n_cred_backup.sql`,
          { maxBuffer: 50 * 1024 * 1024 }
        );
        credBackupExists = true;
        console.log('Dev credentials backed up to n8n_backup.');
      } else {
        console.log('No dev credentials to back up. Will seed from credentials.json after clone.');
      }
    } catch (e) {
      console.error('Warning: credential backup failed:', e.stderr?.trim() || e.message);
      console.log('Proceeding without backup — will seed from credentials.json after clone.');
    }
  }

  // ── Build list of clone tasks ─────────────────────────────────────────────
  const tasks = [];

  if (!skipJager) {
    if (PROD_JAGER_URL) {
      tasks.push(cloneDatabase('jager', PROD_JAGER_URL));
    } else {
      console.log("Production URL for 'jager' not available. Skipping.");
    }
  } else {
    console.log("Skipping 'jager' database clone.");
  }

  if (!skipCDP) {
    if (PROD_CDP_URL) {
      tasks.push(cloneDatabase('cdp', PROD_CDP_URL));
    } else {
      console.log("Production URL for 'cdp' not available. Skipping.");
    }
  } else {
    console.log("Skipping 'cdp' database clone.");
  }

  if (!skipN8N) {
    if (PROD_N8N_URL) {
      tasks.push(cloneDatabase('n8n', PROD_N8N_URL));
    } else {
      console.log("Production URL for 'n8n' not available. Skipping.");
    }
  } else {
    console.log("Skipping 'n8n' database clone.");
  }

  // ── Run all clone jobs in parallel ────────────────────────────────────
  // Use allSettled so every clone runs to completion (including finally cleanup)
  // even if one fails — then we collect and report failures at the end.
  console.log(`Starting ${tasks.length} clone job(s) in parallel (-j ${numJobs} each)...`);

  const results = await Promise.allSettled(tasks);
  const failures = results.filter(r => r.status === 'rejected');
  if (failures.length > 0) {
    failures.forEach(f => console.error('Clone failed:', f.reason?.message ?? f.reason));
    process.exit(1);
  }

  // ── Restore dev n8n credentials after clone ───────────────────────────────
  if (!skipN8N && PROD_N8N_URL) {
    if (credBackupExists) {
      console.log('Restoring dev credentials from n8n_backup...');
      try {
        await execAsync(
          `${dockerComposeCmd} exec -T db sh -c "` +
            `pg_dump -U jager -d n8n_backup --data-only | psql -U jager -d n8n"`,
          { maxBuffer: 50 * 1024 * 1024 }
        );
        console.log('Dev credentials restored.');
      } catch (e) {
        console.error('Warning: failed to restore dev credentials:', e.message);
      }
    } else {
      // Fresh environment — seed from credentials.json via n8n's own import
      console.log('Seeding credentials from credentials.json...');
      try {
        await execAsync(
          `${dockerComposeCmd} exec -T n8n n8n import:credentials --input /etc/n8n/credentials.json`,
          { maxBuffer: 10 * 1024 * 1024 }
        );
        console.log('credentials.json imported.');
      } catch (e) {
        console.error('Warning: failed to import credentials.json:', e.message);
      }
    }
    // Deduplicate and ensure constraints on local n8n database tables (due to production database version mismatch/duplicates)
    console.log('Fixing unique constraints and indexes in local n8n database...');
    try {
      await execAsync(
        `${dockerComposeCmd} exec -T db psql -U jager -d n8n -c "` +
          `DELETE FROM workflow_statistics a USING workflow_statistics b WHERE a.id < b.id AND a.name = b.name AND a.\\\"workflowId\\\" = b.\\\"workflowId\\\"; ` +
          `ALTER TABLE workflow_statistics DROP CONSTRAINT IF EXISTS \\\"UQ_workflow_statistics\\\"; ` +
          `CREATE UNIQUE INDEX IF NOT EXISTS \\\"IDX_workflow_statistics_workflow_name\\\" ON public.workflow_statistics USING btree (\\\"workflowId\\\", name); ` +
          `DELETE FROM insights_metadata a USING insights_metadata b WHERE a.\\\"metaId\\\" < b.\\\"metaId\\\" AND a.\\\"workflowId\\\" = b.\\\"workflowId\\\"; ` +
          `CREATE UNIQUE INDEX IF NOT EXISTS \\\"IDX_1d8ab99d5861c9388d2dc1cf73\\\" ON public.insights_metadata USING btree (\\\"workflowId\\\"); ` +
          `DELETE FROM shared_workflow a USING shared_workflow b WHERE a.ctid < b.ctid AND a.\\\"workflowId\\\" = b.\\\"workflowId\\\" AND a.\\\"projectId\\\" = b.\\\"projectId\\\"; ` +
          `ALTER TABLE ONLY public.shared_workflow ADD CONSTRAINT \\\"PK_5ba87620386b847201c9531c58f\\\" PRIMARY KEY (\\\"workflowId\\\", \\\"projectId\\\");"`,
        { maxBuffer: 10 * 1024 * 1024 }
      );
      console.log('Database constraints and indexes ensured successfully.');
    } catch (e) {
      console.error('Warning: failed to ensure database constraints:', e.message);
    }

    console.log('n8n database updated. Refresh the n8n browser tab to see the new data.');
  }

  // ── Seed CDP local data if empty ──────────────────────────────────────────
  if (!skipCDP) {
    try {
      const { stdout: countOut } = await execAsync(
        `${dockerComposeCmd} exec -T db psql -U jager -d cdp -tAc "SELECT COUNT(*) FROM cdp.leads;"`,
        { maxBuffer: 1 * 1024 * 1024 }
      );
      const leadCount = parseInt(countOut.trim(), 10) || 0;
      if (leadCount === 0) {
        console.log('Local CDP database is empty. Ingesting seed data (substack & cdp seeds)...');
        await execAsync(
          `${dockerComposeCmd} exec -T dapp python /app/src/dapp/oltp/ingest_seeds.py`,
          { maxBuffer: 50 * 1024 * 1024 }
        );
        console.log('Local CDP database seeded successfully.');
      } else {
        console.log(`Local CDP database verified (${leadCount} leads existing).`);
      }
    } catch (e) {
      console.warn('Warning: CDP auto-seed check failed:', e.message);
    }

    // Mirror cdp schema into jager database so the 'Jager (Dev)' PostgreSQL Explorer
    // connection (database: jager) can browse cdp.leads, cdp.persons etc without switching connections.
    // --clean --if-exists: drops & recreates objects inside the schema without touching the schema itself,
    // so the IDE's connection handle to the cdp schema folder is never severed.
    console.log('Mirroring cdp schema into jager database for IDE browsing...');
    try {
      await execAsync(
        `${dockerComposeCmd} exec -T db sh -c "pg_dump -U jager -d cdp -n cdp --clean --if-exists | psql -U jager -d jager -q"`,
        { maxBuffer: 50 * 1024 * 1024 }
      );
      console.log('cdp schema mirrored into jager database.');
    } catch (e) {
      console.warn('Warning: cdp schema mirror into jager failed:', e.message);
    }
  }

  console.log('Database clone process completed.');


})().catch(err => {
  console.error('Fatal error:', err.message);
  process.exit(1);
});
