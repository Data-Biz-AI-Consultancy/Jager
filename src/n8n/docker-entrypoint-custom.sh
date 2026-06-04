#!/bin/sh

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL database to be ready..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Import credentials if they exist and haven't been imported yet
if [ -f /etc/n8n/credentials.json ]; then
  IMPORT_STATUS=$(node -e "
const pgPath = require.resolve('pg', { paths: ['/usr/local/lib/node_modules/n8n'] });
const { Client } = require(pgPath);
const client = new Client({
  host: process.env.DB_POSTGRESDB_HOST || 'db',
  port: parseInt(process.env.DB_POSTGRESDB_PORT || '5432', 10),
  database: process.env.DB_POSTGRESDB_DATABASE || 'n8n',
  user: process.env.DB_POSTGRESDB_USER || 'jager',
  password: process.env.DB_POSTGRESDB_PASSWORD || 'jager',
});
client.connect()
  .then(() => client.query(\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'credentials_entity')\"))
  .then(res => {
    if (!res.rows[0].exists) {
      console.log('IMPORT');
      process.exit(0);
    }
    return client.query('SELECT count(*) FROM credentials_entity');
  })
  .then(res => {
    if (res) {
      const count = parseInt(res.rows[0].count, 10);
      if (count === 0) {
        console.log('IMPORT');
      } else {
        console.log('SKIP');
      }
    }
    client.end();
    process.exit(0);
  })
  .catch(err => {
    console.log('IMPORT');
    process.exit(0);
  });
  " 2>/dev/null)

  if [ "$IMPORT_STATUS" = "IMPORT" ]; then
    echo "Importing N8N credentials..."
    n8n import:credentials --input /etc/n8n/credentials.json
  else
    echo "N8N credentials already exist in database. Skipping import to prevent overwriting."
  fi
fi

# Import workflows from workflows directory
if [ -d /etc/n8n/workflows ]; then
  for f in /etc/n8n/workflows/*.json; do
    if [ -f "$f" ]; then
      echo "Importing workflow: $f"
      n8n import:workflow --input "$f"
    fi
  done
fi

# Execute the default n8n entrypoint
echo "Starting N8N..."
exec /docker-entrypoint.sh
