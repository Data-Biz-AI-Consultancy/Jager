const fs = require('fs');
const path = require('path');

let Client;
try {
  const pgPath = require.resolve('pg', { paths: ['/usr/local/lib/node_modules/n8n'] });
  Client = require(pgPath).Client;
} catch (e) {
  Client = require('pg').Client;
}

let client;
let configLog = '';

if (process.env.DB_APPLICATION_URL) {
  configLog = `DB_APPLICATION_URL (connection string)`;
  client = new Client({
    connectionString: process.env.DB_APPLICATION_URL,
  });
} else if (process.env.DATABASE_URL && (process.env.DATABASE_URL.includes('/jager') || !process.env.DATABASE_URL.includes('/n8n'))) {
  configLog = `DATABASE_URL (connection string)`;
  client = new Client({
    connectionString: process.env.DATABASE_URL,
  });
} else {
  const host = process.env.DB_APPLICATION_HOST || process.env.DB_POSTGRESDB_HOST || 'db';
  const port = process.env.DB_APPLICATION_PORT || process.env.DB_POSTGRESDB_PORT || '5432';
  const database = 'jager';
  const user = process.env.DB_APPLICATION_USER || process.env.DB_POSTGRESDB_USER || 'jager';
  configLog = `host=${host}, port=${port}, database=${database}, user=${user}`;
  client = new Client({
    host,
    port: parseInt(port, 10),
    database,
    user,
    password: process.env.DB_APPLICATION_PASSWORD || process.env.DB_POSTGRESDB_PASSWORD || 'jager',
  });
}

console.log(`Database migration script connecting via: ${configLog}`);

const sqlDir = path.join(__dirname, 'sql');
const cdpDdl = fs.readFileSync(path.join(sqlDir, 'cdp_schema.sql'), 'utf8');
const cdpSeedDdl = process.env.CI !== 'true' ? fs.readFileSync(path.join(sqlDir, 'cdp_seeds.sql'), 'utf8') : '';
const ddl = fs.readFileSync(path.join(sqlDir, 'oltp_schema.sql'), 'utf8');
const seeds = process.env.CI !== 'true' ? fs.readFileSync(path.join(sqlDir, 'oltp_seeds.sql'), 'utf8') : '';

async function run() {
  console.log('Connecting to jager application database for automated migrations...');
  await client.connect();

  console.log('Running application database migrations...');
  try {
    await client.query(`
      ALTER TABLE t_content_generation.linkedin_posts DROP COLUMN IF EXISTS publish_at;
      ALTER TABLE t_content_generation.linkedin_posts DROP COLUMN IF EXISTS scheduled_to_publish_at;
    `);
  } catch (err) {
    console.warn('Warning: Failed to drop duplicate scheduling columns:', err.message);
  }
  await client.query(ddl);

  // Deduplicate and ensure primary key constraints for s_linkedin tables
  const tablesToFix = [
    'ugc_posts',
    'social_action_likes',
    'social_action_comments',
    'all_comments',
    'all_likes',
    'invitations',
    'all_invitations',
    'messages',
    'all_messages',
    'connections',
    'following',
    'searches',
    'job_applications',
    'job_seeker_preferences',
    'instant_reposts'
  ];
  for (const table of tablesToFix) {
    console.log(`Ensuring primary key on s_linkedin.${table}...`);
    await client.query(`
      DELETE FROM s_linkedin.${table} a
      USING s_linkedin.${table} b
      WHERE a.ctid < b.ctid AND a.id = b.id;
    `);
    await client.query(`
      DO $$
      BEGIN
          IF NOT EXISTS (
              SELECT 1 FROM information_schema.table_constraints 
              WHERE table_schema = 's_linkedin' 
              AND table_name = '${table}' 
              AND constraint_type = 'PRIMARY KEY'
          ) THEN
              ALTER TABLE s_linkedin.${table} ADD PRIMARY KEY (id);
          END IF;
      END $$;
    `);
  }

  const migrations = [
    // Parent Tables (Migrated first to resolve FK dependencies)
    { oldTable: 'reddit_subreddits_monitored', newTable: 's_reddit.subreddits_monitored', hasSerial: true },
    { oldTable: 'slack_workspaces_monitored', newTable: 's_slack.workspaces_monitored', hasSerial: true },
    { oldTable: 'substack_feeds_monitored', newTable: 's_substack.feeds_monitored', hasSerial: true },
    { oldTable: 'wordpress_feeds_monitored', newTable: 's_wordpress.feeds_monitored', hasSerial: true },

    // Child/Dependent Tables
    { oldTable: 'reddit_posts', newTable: 's_reddit.posts', hasSerial: false },
    { oldTable: 'reddit_comments', newTable: 's_reddit.comments', hasSerial: false },
    { oldTable: 'slack_channels_monitored', newTable: 's_slack.channels_monitored', hasSerial: true },
    { oldTable: 'slack_messages', newTable: 's_slack.messages', hasSerial: false },
    { oldTable: 'substack_posts', newTable: 's_substack.posts', hasSerial: false },
    { oldTable: 'wordpress_posts', newTable: 's_wordpress.posts', hasSerial: false },

    // Eurostat & Yahoo
    { oldTable: 'eurostat_regional_gdp', newTable: 's_euro_stat.regional_gdp', hasSerial: true },
    { oldTable: 'eurostat_regional_crime_rates', newTable: 's_euro_stat.regional_crime_rates', hasSerial: true },
    { oldTable: 'eurostat_inflation', newTable: 's_euro_stat.inflation', hasSerial: true },
    { oldTable: 'eurostat_quarterly_gdp', newTable: 's_euro_stat.quarterly_gdp', hasSerial: true },
    { oldTable: 'eurostat_unemployment', newTable: 's_euro_stat.unemployment', hasSerial: true },
    { oldTable: 'eurostat_house_price_index', newTable: 's_euro_stat.house_price_index', hasSerial: true },
    { oldTable: 'eurostat_fx_rates', newTable: 's_euro_stat.fx_rates', hasSerial: true },
    { oldTable: 'yahoo_finance_stock_prices', newTable: 's_yahoo_finance.stock_prices', hasSerial: true },
  ];

  console.log('Checking for legacy data to migrate from public schema...');
  for (const m of migrations) {
    const checkRes = await client.query(
      `SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1)`,
      [m.oldTable]
    );
    if (checkRes.rows[0].exists) {
      // Find common columns
      const [newSchema, newTableName] = m.newTable.split('.');
      const colsRes = await client.query(
        `SELECT column_name FROM information_schema.columns 
         WHERE table_schema = 'public' AND table_name = $1
         INTERSECT
         SELECT column_name FROM information_schema.columns 
         WHERE table_schema = $2 AND table_name = $3`,
        [m.oldTable, newSchema, newTableName]
      );
      const commonCols = colsRes.rows.map(r => `"${r.column_name}"`).join(', ');

      console.log(`Migrating data from public.${m.oldTable} to ${m.newTable} using columns: ${commonCols}...`);
      
      // Copy data
      await client.query(`INSERT INTO ${m.newTable} (${commonCols}) SELECT ${commonCols} FROM public.${m.oldTable} ON CONFLICT DO NOTHING`);
      
      // Update serial sequence if needed
      if (m.hasSerial) {
        await client.query(
          `SELECT setval(pg_get_serial_sequence($1, 'id'), coalesce(max(id), 1)) FROM ${m.newTable}`,
          [m.newTable]
        );
      }
      
      // Drop old table
      console.log(`Dropping legacy table public.${m.oldTable}...`);
      await client.query(`DROP TABLE public.${m.oldTable} CASCADE`);
    }
  }

  if (seeds) {
    console.log('Seeding default feeds and subreddits...');
    await client.query(seeds);
  }

  console.log('Application database migrations and data transfers completed successfully.');
  await client.end();

  let cdpConfig;
  if (process.env.CDP_DATABASE_URL) {
    cdpConfig = { connectionString: process.env.CDP_DATABASE_URL };
  } else if (process.env.DATABASE_URL && process.env.DATABASE_URL.includes('/jager')) {
    cdpConfig = { connectionString: process.env.DATABASE_URL.replace('/jager', '/cdp') };
  } else {
    const host = process.env.DB_APPLICATION_HOST || process.env.DB_POSTGRESDB_HOST || 'db';
    const port = parseInt(process.env.DB_APPLICATION_PORT || process.env.DB_POSTGRESDB_PORT || '5432', 10);
    const user = process.env.DB_APPLICATION_USER || process.env.DB_POSTGRESDB_USER || 'jager';
    const password = process.env.DB_APPLICATION_PASSWORD || process.env.DB_POSTGRESDB_PASSWORD || 'jager';
    cdpConfig = { host, port, database: 'cdp', user, password };
  }
  const cdpClient = new Client(cdpConfig);
  try {
    console.log('Connecting to cdp database for migrations...');
    await cdpClient.connect();
  } catch (err) {
    if (err.code === '3D000') {
      const adminClient = new Client(
        process.env.DATABASE_URL
          ? { connectionString: process.env.DATABASE_URL }
          : {
              host: process.env.DB_APPLICATION_HOST || process.env.DB_POSTGRESDB_HOST || 'db',
              port: parseInt(process.env.DB_APPLICATION_PORT || process.env.DB_POSTGRESDB_PORT || '5432', 10),
              database: 'jager',
              user: process.env.DB_APPLICATION_USER || process.env.DB_POSTGRESDB_USER || 'jager',
              password: process.env.DB_APPLICATION_PASSWORD || process.env.DB_POSTGRESDB_PASSWORD || 'jager',
            }
      );
      await adminClient.connect();
      await adminClient.query('CREATE DATABASE cdp');
      await adminClient.end();
      await cdpClient.connect();
    } else {
      throw err;
    }
  }

  console.log('Applying cdp database schema DDL...');
  await cdpClient.query(cdpDdl);
  if (cdpSeedDdl) {
    console.log('Applying cdp seed data (skipped in CI)...');
    await cdpClient.query(cdpSeedDdl);
  }
  console.log('CDP database migrations completed successfully.');
  await cdpClient.end();
}

run().catch(err => {
  console.error('Database migration failed:', err);
  process.exit(1);
});
