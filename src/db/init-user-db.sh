#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	SELECT 'CREATE DATABASE n8n'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n')\gexec

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

	CREATE EXTENSION IF NOT EXISTS pgcrypto;

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



	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('smallbusiness', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('saas', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('solopreneur', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('indiebiz', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('entrepreneurship', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('advancedentrepreneur', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('entrepreneurridealong', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('growmybusiness', TRUE) ON CONFLICT (name) DO NOTHING;

	INSERT INTO substack_feeds_monitored (name, feed_url, active) VALUES 
		('SeattleDataGuy', 'https://seattledataguy.substack.com/feed', TRUE),
		('Decision', 'https://decision.substack.com/feed', TRUE),
		('TheGoodBoss', 'https://read.thegoodboss.com/feed', TRUE),
		('EngLeadership', 'https://newsletter.eng-leadership.com/feed', TRUE),
		('ThrivingInEngineering', 'https://thrivinginengineering.substack.com/feed', TRUE),
		('CodeLikeAGirl', 'https://codelikeagirl.substack.com/feed', TRUE),
		('JimmyPang', 'https://jimmypang.substack.com/feed', TRUE)
	ON CONFLICT (name) DO NOTHING;
EOSQL
