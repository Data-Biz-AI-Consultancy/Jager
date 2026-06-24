#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');

function usage() {
  console.log(`
Usage: node scripts/clone-db.js <PROD_DATABASE_URL> [options]

Options:
  --skip-n8n, --jager-only    Only clone the 'jager' database, skip 'n8n' database
  --skip-jager, --n8n-only    Only clone the 'n8n' database, skip 'jager' database
  -j, --jobs <number>         Number of parallel dump/restore jobs (default: 4)
  --exclude-history           Exclude large history/execution log tables (e.g. execution_entity in n8n)

Example:
  node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --skip-n8n --jobs 4 --exclude-history
`);
  process.exit(1);
}

// Parse args
const args = process.argv.slice(2);
const connectionString = args.find(a => a.startsWith('postgres://') || a.startsWith('postgresql://') || a.includes('@'));

const skipN8N = args.includes('--skip-n8n') || args.includes('--jager-only');
const skipJager = args.includes('--skip-jager') || args.includes('--n8n-only');

let jobs = 4;
const jobsIdx = args.findIndex(a => a === '-j' || a === '--jobs');
if (jobsIdx !== -1 && jobsIdx + 1 < args.length) {
  const val = parseInt(args[jobsIdx + 1], 10);
  if (!isNaN(val)) {
    jobs = val;
  }
}
const excludeHistory = args.includes('--exclude-history');

if ((!connectionString && args.includes('-h')) || args.includes('--help') || (!connectionString && args.length === 0)) {
  usage();
}

// Environment fallback variables or derived URLs
let PROD_JAGER_URL = connectionString || process.env.PROD_DATABASE_URL || process.env.PROD_JAGER_URL;
let PROD_N8N_URL = process.env.PROD_N8N_URL;

if (PROD_JAGER_URL) {
  try {
    const urlObj = new URL(PROD_JAGER_URL);
    // If the database name in the URL is 'jager' (or anything else), derive n8n URL
    if (urlObj.pathname !== '/n8n') {
      urlObj.pathname = '/n8n';
      PROD_N8N_URL = urlObj.toString();
    }
  } catch (e) {
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

// Detect docker compose command
let dockerComposeCmd = 'docker compose';
try {
  execSync('docker compose version', { stdio: 'ignore' });
} catch (e) {
  try {
    execSync('docker-compose version', { stdio: 'ignore' });
    dockerComposeCmd = 'docker-compose';
  } catch (err) {
    console.error("Error: Neither 'docker compose' nor 'docker-compose' found.");
    process.exit(1);
  }
}

// Ensure local db service is running
let dbStatus = '';
try {
  dbStatus = execSync(`${dockerComposeCmd} ps -q db`, { encoding: 'utf8' }).trim();
} catch (e) {
  // Container not started
}

if (!dbStatus) {
  console.log('Local database container (db) is not running. Starting services...');
  execSync(`${dockerComposeCmd} up -d db`, { stdio: 'inherit' });
  console.log('Waiting for PostgreSQL to start...');
  execSync('sleep 5');
}

function cloneDatabase(dbName, prodUrl) {
  console.log('=========================================');
  console.log(`Cloning Database: ${dbName}`);
  console.log('=========================================');

  const tempDir = `/tmp/${dbName}_prod_dump`;
  try {
    // Ensure temp directory does not exist or is clean
    try {
      execSync(`${dockerComposeCmd} exec -T db rm -rf ${tempDir}`, { stdio: 'ignore' });
    } catch (e) {}

    // Run pg_dump first to ensure it succeeds before we drop/touch local databases
    console.log(`Dumping from production URL to temporary directory...`);
    let dumpCmd = `${dockerComposeCmd} exec -T db pg_dump -Fd -j ${jobs} -d "${prodUrl}" --no-owner --no-privileges`;
    if (excludeHistory && dbName === 'n8n') {
      dumpCmd += ' --exclude-table-data=execution_entity';
    }
    dumpCmd += ` -f ${tempDir}`;
    execSync(dumpCmd, { stdio: 'inherit' });

    // Terminate existing connections
    console.log(`Terminating existing connections to local database: ${dbName}...`);
    try {
      execSync(
        `${dockerComposeCmd} exec -T db psql -U jager -d postgres -c ` +
        `"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${dbName}' AND pid <> pg_backend_pid();"`,
        { stdio: 'ignore' }
      );
    } catch (e) {
      // Ignore error if database has no connections or doesn't exist yet
    }

    // Drop and recreate local database
    console.log(`Recreating local database: ${dbName}...`);
    execSync(`${dockerComposeCmd} exec -T db psql -U jager -d postgres -c "DROP DATABASE IF EXISTS ${dbName};"`, { stdio: 'inherit' });
    execSync(`${dockerComposeCmd} exec -T db psql -U jager -d postgres -c "CREATE DATABASE ${dbName};"`, { stdio: 'inherit' });
    
    // Restore from the temp directory
    console.log(`Restoring dump to local ${dbName}...`);
    execSync(`${dockerComposeCmd} exec -T db pg_restore -U jager -d "${dbName}" -j ${jobs} --no-owner --no-privileges ${tempDir}`, { stdio: 'inherit' });
    
    if (dbName === 'n8n') {
      console.log(`Sanitizing cloned n8n database: deactivating workflows and removing production credentials...`);
      try {
        execSync(`${dockerComposeCmd} exec -T db psql -U jager -d n8n -c "UPDATE workflow_entity SET active = false;"`, { stdio: 'inherit' });
        execSync(`${dockerComposeCmd} exec -T db psql -U jager -d n8n -c "TRUNCATE credentials_entity CASCADE;"`, { stdio: 'inherit' });
        console.log(`Successfully sanitized n8n database!`);
      } catch (err) {
        console.error(`Warning: Failed to sanitize n8n database:`, err.message);
      }
    }

    console.log(`Successfully cloned ${dbName}!`);
  } catch (error) {
    console.error(`Error cloning database ${dbName}:`, error.message);
    throw error;
  } finally {
    // Clean up temp directory
    try {
      execSync(`${dockerComposeCmd} exec -T db rm -rf ${tempDir}`, { stdio: 'ignore' });
    } catch (e) {
      // Ignore cleanup errors
    }
  }
}

// Clone jager
if (!skipJager) {
  if (PROD_JAGER_URL) {
    cloneDatabase('jager', PROD_JAGER_URL);
  } else {
    console.log("Production URL for 'jager' database not provided.");
  }
} else {
  console.log("Skipping 'jager' database clone.");
}

// Clone n8n
if (!skipN8N) {
  if (PROD_N8N_URL) {
    cloneDatabase('n8n', PROD_N8N_URL);
  } else {
    console.log("Production URL for 'n8n' database not provided. Skipping 'n8n' cloning.");
  }
} else {
  console.log("Skipping 'n8n' database clone.");
}

// Restart n8n container if we cloned n8n database, or if we want to ensure fresh connections
if (!skipN8N) {
  console.log('Restarting n8n container to apply changes and re-import credentials...');
  try {
    execSync(`${dockerComposeCmd} restart n8n`, { stdio: 'inherit' });
    console.log('n8n container restarted successfully.');
  } catch (e) {
    console.error('Failed to restart n8n container:', e.message);
  }
}

console.log('Database clone process completed.');
