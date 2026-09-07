const fs = require('fs');
const path = require('path');

let Client;
try {
  const pgPath = require.resolve('pg', { paths: ['/usr/local/lib/node_modules/n8n'] });
  Client = require(pgPath).Client;
} catch (e) {
  Client = require('pg').Client;
}

function getJagerConfig() {
  if (process.env.JAGER_DATABASE_URL) {
    return { connectionString: process.env.JAGER_DATABASE_URL };
  }
  if (process.env.DB_APPLICATION_URL) {
    return { connectionString: process.env.DB_APPLICATION_URL };
  }
  if (process.env.DATABASE_URL) {
    let url = process.env.DATABASE_URL;
    url = url.replace(/\/cdp(\?|$)/, '/jager$1').replace(/\/n8n(\?|$)/, '/jager$1');
    return { connectionString: url };
  }
  const host = process.env.DB_APPLICATION_HOST || process.env.DB_POSTGRESDB_HOST || 'db';
  const port = parseInt(process.env.DB_APPLICATION_PORT || process.env.DB_POSTGRESDB_PORT || '5432', 10);
  const user = process.env.DB_APPLICATION_USER || process.env.DB_POSTGRESDB_USER || 'jager';
  const password = process.env.DB_APPLICATION_PASSWORD || process.env.DB_POSTGRESDB_PASSWORD || 'jager';
  return { host, port, database: 'jager', user, password };
}

const sqlDir = path.join(__dirname, 'sql');
const schemaDir = path.join(sqlDir, 'schema');
const seeds = process.env.CI !== 'true' ? fs.readFileSync(path.join(sqlDir, 'oltp_seeds.sql'), 'utf8') : '';

// Schema files are executed in alphabetical order (01_, 02_, ... prefix ensures correct order).
const schemaFiles = fs.readdirSync(schemaDir)
  .filter(f => f.endsWith('.sql'))
  .sort();

async function run() {
  const jagerConfig = getJagerConfig();
  console.log('Connecting to jager application database for automated migrations...');
  const jagerClient = new Client(jagerConfig);
  await jagerClient.connect();

  // Ensure n8n database exists
  const requiredDbs = ['n8n'];
  for (const dbName of requiredDbs) {
    try {
      const checkRes = await jagerClient.query('SELECT 1 FROM pg_database WHERE datname = $1', [dbName]);
      if (checkRes.rowCount === 0) {
        console.log(`Creating database '${dbName}'...`);
        await jagerClient.query(`CREATE DATABASE ${dbName}`);
        console.log(`Database '${dbName}' created.`);
      }
    } catch (e) {
      console.warn(`Warning: Could not check/create database '${dbName}':`, e.message);
    }
  }

  console.log('Running application database migrations...');

  // Guard: drop legacy scheduling columns if still present
  try {
    await jagerClient.query(`
      ALTER TABLE t_content_generation.linkedin_posts DROP COLUMN IF EXISTS publish_at;
      ALTER TABLE t_content_generation.linkedin_posts DROP COLUMN IF EXISTS scheduled_to_publish_at;
    `);
  } catch (err) {
    console.warn('Warning: Failed to drop legacy scheduling columns:', err.message);
  }

  // Execute each schema file in order
  for (const file of schemaFiles) {
    const filePath = path.join(schemaDir, file);
    const sql = fs.readFileSync(filePath, 'utf8');
    console.log(`  Applying ${file}...`);
    await jagerClient.query(sql);
  }

  if (seeds) {
    console.log('Seeding default feeds and subreddits...');
    await jagerClient.query(seeds);
  }

  console.log('Application database migrations completed successfully.');
  await jagerClient.end();
}

run().catch(err => {
  console.error('Database migration failed:', err);
  process.exit(1);
});
