#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');

function usage() {
  console.log(`
Usage: node scripts/clone-db.js <PROD_DATABASE_URL>

Example:
  node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager"
`);
  process.exit(1);
}

// Parse args
const args = process.argv.slice(2);
const connectionString = args.find(a => a.startsWith('postgres://') || a.startsWith('postgresql://') || a.includes('@'));

if (!connectionString && args.includes('-h') || args.includes('--help')) {
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

  const tempFile = `/tmp/${dbName}_prod_dump.sql`;
  try {
    // Run pg_dump first to ensure it succeeds before we drop/touch local databases
    console.log(`Dumping from production URL to temporary file...`);
    execSync(`${dockerComposeCmd} exec -T db pg_dump -d "${prodUrl}" --no-owner --no-privileges -f ${tempFile}`, { stdio: 'inherit' });

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
    
    // Restore from the temp file
    console.log(`Restoring dump to local ${dbName}...`);
    execSync(`${dockerComposeCmd} exec -T db psql -U jager -d "${dbName}" -f ${tempFile}`, { stdio: 'inherit' });
    
    console.log(`Successfully cloned ${dbName}!`);
  } catch (error) {
    console.error(`Error cloning database ${dbName}:`, error.message);
    throw error;
  } finally {
    // Clean up temp file
    try {
      execSync(`${dockerComposeCmd} exec -T db rm -f ${tempFile}`, { stdio: 'ignore' });
    } catch (e) {
      // Ignore cleanup errors
    }
  }
}

// Clone jager
if (PROD_JAGER_URL) {
  cloneDatabase('jager', PROD_JAGER_URL);
} else {
  console.log("Production URL for 'jager' database not provided.");
}

// Clone n8n
if (PROD_N8N_URL) {
  cloneDatabase('n8n', PROD_N8N_URL);
} else {
  console.log("Production URL for 'n8n' database not provided. Skipping 'n8n' cloning.");
}

console.log('Database clone process completed.');
