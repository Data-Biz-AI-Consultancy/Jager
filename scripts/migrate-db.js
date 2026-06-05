const pgPath = require.resolve('pg', { paths: ['/usr/local/lib/node_modules/n8n'] });
const { Client } = require(pgPath);

let client;
if (process.env.DATABASE_URL) {
  client = new Client({
    connectionString: process.env.DATABASE_URL,
  });
} else if (process.env.DB_APPLICATION_URL) {
  client = new Client({
    connectionString: process.env.DB_APPLICATION_URL,
  });
} else {
  client = new Client({
    host: process.env.DB_APPLICATION_HOST || process.env.DB_POSTGRESDB_HOST || 'db',
    port: parseInt(process.env.DB_APPLICATION_PORT || process.env.DB_POSTGRESDB_PORT || '5432', 10),
    database: 'jager',
    user: process.env.DB_APPLICATION_USER || process.env.DB_POSTGRESDB_USER || 'jager',
    password: process.env.DB_APPLICATION_PASSWORD || process.env.DB_POSTGRESDB_PASSWORD || 'jager',
  });
}

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
  feed_name VARCHAR(255),
  author VARCHAR(255),
  title VARCHAR(1024),
  content TEXT NOT NULL,
  url VARCHAR(2048),
  published_at TIMESTAMP WITH TIME ZONE,
  processed INTEGER DEFAULT 0
);

ALTER TABLE substack_posts ADD COLUMN IF NOT EXISTS feed_name VARCHAR(255);


CREATE TABLE IF NOT EXISTS eurostat_regional_gdp (
  id SERIAL PRIMARY KEY,
  geo_code VARCHAR(50) NOT NULL,
  geo_name VARCHAR(255),
  year INTEGER NOT NULL,
  gdp_value NUMERIC,
  unit VARCHAR(50),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (geo_code, year, unit)
);

CREATE TABLE IF NOT EXISTS eurostat_regional_crime_rates (
  id SERIAL PRIMARY KEY,
  geo_code VARCHAR(50) NOT NULL,
  geo_name VARCHAR(255),
  year INTEGER NOT NULL,
  offence_category VARCHAR(255),
  crime_count NUMERIC,
  unit VARCHAR(50),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (geo_code, year, offence_category, unit)
);

CREATE TABLE IF NOT EXISTS eurostat_inflation (
  id SERIAL PRIMARY KEY,
  geo_code VARCHAR(50) NOT NULL,
  geo_name VARCHAR(255),
  time VARCHAR(50) NOT NULL,
  coicop_code VARCHAR(50) NOT NULL,
  coicop_name VARCHAR(255),
  unit VARCHAR(50),
  value NUMERIC,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (geo_code, time, coicop_code, unit)
);

CREATE TABLE IF NOT EXISTS eurostat_quarterly_gdp (
  id SERIAL PRIMARY KEY,
  geo_code VARCHAR(50) NOT NULL,
  geo_name VARCHAR(255),
  time VARCHAR(50) NOT NULL,
  na_item VARCHAR(50) NOT NULL,
  unit VARCHAR(50),
  s_adj VARCHAR(50),
  value NUMERIC,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (geo_code, time, na_item, unit, s_adj)
);

CREATE TABLE IF NOT EXISTS eurostat_unemployment (
  id SERIAL PRIMARY KEY,
  geo_code VARCHAR(50) NOT NULL,
  geo_name VARCHAR(255),
  time VARCHAR(50) NOT NULL,
  age VARCHAR(50),
  sex VARCHAR(10),
  unit VARCHAR(50),
  s_adj VARCHAR(50),
  value NUMERIC,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (geo_code, time, age, sex, unit, s_adj)
);

CREATE TABLE IF NOT EXISTS eurostat_house_price_index (
  id SERIAL PRIMARY KEY,
  geo_code VARCHAR(50) NOT NULL,
  geo_name VARCHAR(255),
  time VARCHAR(50) NOT NULL,
  purchase VARCHAR(50),
  unit VARCHAR(50),
  value NUMERIC,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (geo_code, time, purchase, unit)
);

CREATE TABLE IF NOT EXISTS eurostat_fx_rates (
  id SERIAL PRIMARY KEY,
  base_currency VARCHAR(3) NOT NULL,
  target_currency VARCHAR(3) NOT NULL,
  rate NUMERIC NOT NULL,
  rate_date DATE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (base_currency, target_currency, rate_date)
);

CREATE TABLE IF NOT EXISTS yahoo_finance_stock_prices (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(50) NOT NULL,
  price_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  open_price NUMERIC,
  high_price NUMERIC,
  low_price NUMERIC,
  close_price NUMERIC,
  volume NUMERIC,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (symbol, price_timestamp)
);

CREATE SCHEMA IF NOT EXISTS prediction;

CREATE TABLE IF NOT EXISTS prediction.stock_predictions (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(50) NOT NULL,
  prediction_date DATE NOT NULL,
  predicted_close_price NUMERIC NOT NULL,
  actual_close_price NUMERIC,
  trend VARCHAR(10),
  confidence NUMERIC,
  reasoning TEXT,
  model_name VARCHAR(100) NOT NULL,
  features JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (symbol, prediction_date, model_name)
);

CREATE SCHEMA IF NOT EXISTS training;

CREATE TABLE IF NOT EXISTS training.trained_models (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(50) NOT NULL,
  model_name VARCHAR(100) NOT NULL,
  model_data BYTEA NOT NULL,
  r2_score NUMERIC,
  trained_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (symbol, model_name)
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
