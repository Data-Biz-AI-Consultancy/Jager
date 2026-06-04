const pgPath = require.resolve('pg', { paths: ['/usr/local/lib/node_modules/n8n'] });
const { Client } = require(pgPath);

const client = new Client({
  host: process.env.DB_POSTGRESDB_HOST || 'db',
  port: parseInt(process.env.DB_POSTGRESDB_PORT || '5432', 10),
  database: 'jager',
  user: process.env.DB_POSTGRESDB_USER || 'jager',
  password: process.env.DB_POSTGRESDB_PASSWORD || 'jager',
});

const ddl = `
CREATE TABLE IF NOT EXISTS reddit_subreddits_monitored (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  active BOOLEAN DEFAULT TRUE,
  rules TEXT,
  title VARCHAR(255),
  updated_at TIMESTAMP WITH TIME ZONE,
  icon VARCHAR(1024),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reddit_posts (
  id VARCHAR(255) PRIMARY KEY,
  subreddit_id INTEGER REFERENCES reddit_subreddits_monitored(id) ON DELETE CASCADE,
  author VARCHAR(255),
  title VARCHAR(1024),
  content TEXT NOT NULL,
  url VARCHAR(2048),
  score INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE,
  processed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reddit_comments (
  id VARCHAR(255) PRIMARY KEY,
  post_id VARCHAR(255) NOT NULL,
  author VARCHAR(255),
  content TEXT NOT NULL,
  score INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS slack_workspaces_monitored (
  id SERIAL PRIMARY KEY,
  workspace_id VARCHAR(255) NOT NULL UNIQUE,
  workspace_name VARCHAR(255),
  token BYTEA NOT NULL,
  d_cookie BYTEA,
  d_s_cookie BYTEA,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS slack_channels_monitored (
  id SERIAL PRIMARY KEY,
  workspace_id INTEGER REFERENCES slack_workspaces_monitored(id) ON DELETE CASCADE,
  channel_id VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (workspace_id, channel_id)
);

CREATE TABLE IF NOT EXISTS slack_messages (
  id VARCHAR(255) PRIMARY KEY,
  channel_db_id INTEGER REFERENCES slack_channels_monitored(id) ON DELETE CASCADE,
  author VARCHAR(255),
  content TEXT NOT NULL,
  url VARCHAR(2048),
  created_at TIMESTAMP WITH TIME ZONE,
  processed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS substack_feeds_monitored (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  feed_url VARCHAR(1024) NOT NULL UNIQUE,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS substack_posts (
  id VARCHAR(255) PRIMARY KEY,
  feed_id INTEGER REFERENCES substack_feeds_monitored(id) ON DELETE CASCADE,
  author VARCHAR(255),
  title VARCHAR(1024),
  content TEXT NOT NULL,
  url VARCHAR(2048),
  published_at TIMESTAMP WITH TIME ZONE,
  processed INTEGER DEFAULT 0
);

INSERT INTO reddit_subreddits_monitored (name, active) VALUES 
('smallbusiness', TRUE),
('saas', TRUE),
('solopreneur', TRUE),
('indiebiz', TRUE),
('entrepreneurship', TRUE),
('advancedentrepreneur', TRUE),
('entrepreneurridealong', TRUE),
('growmybusiness', TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO substack_feeds_monitored (name, feed_url, active) 
VALUES 
('SeattleDataGuy', 'https://seattledataguy.substack.com/feed', TRUE),
('Decision', 'https://decision.substack.com/feed', TRUE),
('TheGoodBoss', 'https://read.thegoodboss.com/feed', TRUE),
('EngLeadership', 'https://newsletter.eng-leadership.com/feed', TRUE),
('ThrivingInEngineering', 'https://thrivinginengineering.substack.com/feed', TRUE),
('CodeLikeAGirl', 'https://codelikeagirl.substack.com/feed', TRUE),
('JimmyPang', 'https://jimmypang.substack.com/feed', TRUE)
ON CONFLICT (name) DO NOTHING;
`;

async function run() {
  console.log('Connecting to jager application database for automated migrations...');
  await client.connect();
  console.log('Running application database migrations...');
  await client.query(ddl);
  console.log('Application database migrations completed successfully.');
  await client.end();
}

run().catch(err => {
  console.error('Database migration failed:', err);
  process.exit(1);
});
