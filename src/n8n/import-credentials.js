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

async function run() {
  await client.connect();

  const tableCheck = await client.query(`
    SELECT EXISTS (
      SELECT FROM information_schema.tables 
      WHERE table_schema = 'public' 
      AND table_name = 'credentials_entity'
    )
  `);

  const tableExists = tableCheck.rows[0].exists;

  const credentialsFile = '/etc/n8n/credentials.json';
  if (!fs.existsSync(credentialsFile)) {
    console.log('Credentials file not found, skipping credential import.');
    await client.end();
    return;
  }

  let localCredentials;
  try {
    localCredentials = JSON.parse(fs.readFileSync(credentialsFile, 'utf8'));
  } catch (err) {
    console.error(`Error parsing credentials JSON file:`, err.message);
    await client.end();
    return;
  }

  if (!Array.isArray(localCredentials)) {
    console.error('Credentials JSON format error: expected an array.');
    await client.end();
    return;
  }

  let newCredentials = [];

  if (tableExists) {
    try {
      const res = await client.query('SELECT id FROM credentials_entity');
      const existingIds = new Set(res.rows.map(row => row.id));

      for (const cred of localCredentials) {
        if (!cred.id) {
          console.warn('Skipping credential entry with missing ID:', cred);
          continue;
        }
        if (existingIds.has(cred.id)) {
          console.log(`Credential with ID "${cred.id}" already exists. Skipping.`);
        } else {
          console.log(`Credential with ID "${cred.id}" is new. Adding to import list.`);
          newCredentials.push(cred);
        }
      }
    } catch (err) {
      console.error('Error querying credentials from database:', err.message);
      newCredentials = localCredentials; // fallback to importing all on query failure
    }
  } else {
    console.log('credentials_entity table does not exist yet. Importing all credentials.');
    newCredentials = localCredentials;
  }

  if (newCredentials.length > 0) {
    const tempFile = '/tmp/new_credentials.json';
    try {
      fs.writeFileSync(tempFile, JSON.stringify(newCredentials, null, 2), 'utf8');
      console.log(`Importing ${newCredentials.length} new credential(s)...`);
      execSync(`n8n import:credentials --input "${tempFile}"`, { stdio: 'inherit' });
    } catch (err) {
      console.error('Failed to import new credentials:', err.message);
    } finally {
      if (fs.existsSync(tempFile)) {
        try {
          fs.unlinkSync(tempFile);
        } catch (e) {
          // ignore cleanup errors
        }
      }
    }
  } else {
    console.log('No new credentials to import.');
  }

  await client.end();
}

run().catch(err => {
  console.error('Fatal error in import-credentials script:', err);
  process.exit(1);
});
