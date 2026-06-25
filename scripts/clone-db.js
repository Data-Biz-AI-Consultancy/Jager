#!/usr/bin/env node

const { exec, execSync } = require('child_process');
const { promisify } = require('util');
const fs = require('fs');
const os = require('os');

const execAsync = promisify(exec);

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

function usage() {
  console.log(`
Usage: node scripts/clone-db.js <PROD_DATABASE_URL> [options]

Options:
  --skip-n8n, --jager-only    Only clone the 'jager' database, skip 'n8n' database
  --skip-jager, --n8n-only    Only clone the 'n8n' database, skip 'jager' database
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
const skipN8N        = args.includes('--skip-n8n')    || args.includes('--jager-only');
const skipJager      = args.includes('--skip-jager')   || args.includes('--n8n-only');
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

let PROD_JAGER_URL = connectionString || process.env.PROD_DATABASE_URL || process.env.PROD_JAGER_URL;
let PROD_N8N_URL   = process.env.PROD_N8N_URL;

if (PROD_JAGER_URL) {
  try {
    const urlObj = new URL(PROD_JAGER_URL);
    if (urlObj.pathname !== '/n8n') {
      urlObj.pathname = '/n8n';
      PROD_N8N_URL = urlObj.toString();
    }
  } catch {
    // Simple fallback string replacement if URL parsing fails
    PROD_N8N_URL = PROD_JAGER_URL.replace(/\/jager(\?|$)/, '/n8n$1');
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

    // ── Step 2: Drop local database (WITH FORCE eliminates separate termination step) ──
    log(`Dropping local database ${dbName}...`);
    try {
      // PostgreSQL 13+ — immediately terminates all connections and drops
      await run(
        `${dockerComposeCmd} exec -T db psql -U jager -d postgres` +
          ` -c "DROP DATABASE IF EXISTS ${dbName} WITH (FORCE);"`,
        tag
      );
    } catch {
      // Fallback for PostgreSQL < 13
      await run(
        `${dockerComposeCmd} exec -T db psql -U jager -d postgres` +
          ` -c "DROP DATABASE IF EXISTS ${dbName};"`,
        tag
      );
    }

    // ── Step 3: Recreate ─────────────────────────────────────────────────────
    log(`Creating local database ${dbName}...`);
    await run(
      `${dockerComposeCmd} exec -T db psql -U jager -d postgres -c "CREATE DATABASE ${dbName};"`,
      tag
    );

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

    // ── Step 5: Credential FK cleanup (n8n only) ─────────────────────────────
    // credentials_entity is intentionally empty. Simulate what the database's own
    // ON DELETE rules would have done, so the schema is left consistent:
    //   - ON DELETE SET NULL → NULL out the credentialId column
    //   - ON DELETE CASCADE  → delete rows that reference missing credentials
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

  // ── Restart n8n container after clone ─────────────────────────────────────
  if (!skipN8N && PROD_N8N_URL) {
    console.log('Restarting n8n container to apply changes and re-import credentials...');
    try {
      execSync(`${dockerComposeCmd} restart n8n`, { stdio: 'inherit' });
      console.log('n8n container restarted successfully.');
    } catch (e) {
      console.error('Failed to restart n8n container:', e.message);
    }
  }

  console.log('Database clone process completed.');
})().catch(err => {
  console.error('Fatal error:', err.message);
  process.exit(1);
});
