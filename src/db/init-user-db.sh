#!/bin/sh
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	SELECT 'CREATE DATABASE n8n'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n')\gexec

	CREATE SCHEMA IF NOT EXISTS s_reddit;
	CREATE SCHEMA IF NOT EXISTS s_slack;
	CREATE SCHEMA IF NOT EXISTS s_substack;
	CREATE SCHEMA IF NOT EXISTS s_meetup;
	CREATE SCHEMA IF NOT EXISTS s_euro_stat;
	CREATE SCHEMA IF NOT EXISTS s_yahoo_finance;
	CREATE SCHEMA IF NOT EXISTS s_wordpress;
	CREATE SCHEMA IF NOT EXISTS s_linkedin;

	CREATE TABLE IF NOT EXISTS s_reddit.subreddits_monitored (
		id SERIAL PRIMARY KEY,
		name VARCHAR(255) NOT NULL UNIQUE,
		active BOOLEAN DEFAULT TRUE,
		rules TEXT,
		title VARCHAR(255),
		updated_at TIMESTAMP WITH TIME ZONE,
		icon VARCHAR(1024),
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS s_reddit.posts (
		id VARCHAR(255) PRIMARY KEY,
		subreddit_id INTEGER REFERENCES s_reddit.subreddits_monitored(id) ON DELETE CASCADE,
		author VARCHAR(255),
		title VARCHAR(1024),
		content TEXT NOT NULL,
		url VARCHAR(2048),
		score INTEGER DEFAULT 0,
		created_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_reddit.comments (
		id VARCHAR(255) PRIMARY KEY,
		post_id VARCHAR(255) NOT NULL,
		author VARCHAR(255),
		content TEXT NOT NULL,
		score INTEGER DEFAULT 0,
		created_at TIMESTAMP WITH TIME ZONE
	);

	CREATE EXTENSION IF NOT EXISTS pgcrypto;

	CREATE TABLE IF NOT EXISTS s_slack.workspaces_monitored (
		id SERIAL PRIMARY KEY,
		workspace_id VARCHAR(255) NOT NULL UNIQUE,
		workspace_name VARCHAR(255),
		token BYTEA NOT NULL,
		d_cookie BYTEA,
		d_s_cookie BYTEA,
		active BOOLEAN DEFAULT TRUE,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS s_slack.channels_monitored (
		id SERIAL PRIMARY KEY,
		workspace_id INTEGER REFERENCES s_slack.workspaces_monitored(id) ON DELETE CASCADE,
		channel_id VARCHAR(255) NOT NULL,
		name VARCHAR(255),
		active BOOLEAN DEFAULT TRUE,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		UNIQUE (workspace_id, channel_id)
	);

	CREATE TABLE IF NOT EXISTS s_slack.messages (
		id VARCHAR(255) PRIMARY KEY,
		channel_db_id INTEGER REFERENCES s_slack.channels_monitored(id) ON DELETE CASCADE,
		author VARCHAR(255),
		content TEXT NOT NULL,
		url VARCHAR(2048),
		created_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_substack.feeds_monitored (
		id SERIAL PRIMARY KEY,
		name VARCHAR(255) NOT NULL UNIQUE,
		feed_url VARCHAR(1024) NOT NULL UNIQUE,
		active BOOLEAN DEFAULT TRUE,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS s_substack.posts (
		id VARCHAR(255) PRIMARY KEY,
		feed_id INTEGER REFERENCES s_substack.feeds_monitored(id) ON DELETE CASCADE,
		feed_name VARCHAR(255),
		author VARCHAR(255),
		title VARCHAR(1024),
		content TEXT NOT NULL,
		url VARCHAR(2048),
		published_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);

	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS feed_name VARCHAR(255);

	CREATE TABLE IF NOT EXISTS s_wordpress.feeds_monitored (
		id SERIAL PRIMARY KEY,
		name VARCHAR(255) NOT NULL UNIQUE,
		feed_url VARCHAR(1024) NOT NULL UNIQUE,
		active BOOLEAN DEFAULT TRUE,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS s_wordpress.posts (
		id VARCHAR(255) PRIMARY KEY,
		feed_id INTEGER REFERENCES s_wordpress.feeds_monitored(id) ON DELETE CASCADE,
		feed_name VARCHAR(255),
		author VARCHAR(255),
		title VARCHAR(1024),
		content TEXT NOT NULL,
		url VARCHAR(2048),
		published_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.ugc_posts (
		id VARCHAR(255) PRIMARY KEY,
		author VARCHAR(255),
		content TEXT,
		url VARCHAR(2048),
		published_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);

	DROP TABLE IF EXISTS s_linkedin.social_actions CASCADE;

	CREATE TABLE IF NOT EXISTS s_linkedin.social_action_likes (
		id VARCHAR(255) PRIMARY KEY,
		post_id VARCHAR(255) NOT NULL,
		author VARCHAR(255),
		published_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.social_action_comments (
		id VARCHAR(255) PRIMARY KEY,
		post_id VARCHAR(255) NOT NULL,
		author VARCHAR(255),
		content TEXT,
		published_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_meetup.searches_monitored (
		id SERIAL PRIMARY KEY,
		name VARCHAR(255) NOT NULL UNIQUE,
		search_url VARCHAR(1024) NOT NULL UNIQUE,
		active BOOLEAN DEFAULT TRUE,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS s_meetup.search_results (
		id VARCHAR(255) PRIMARY KEY,
		search_id INTEGER REFERENCES s_meetup.searches_monitored(id) ON DELETE CASCADE,
		search_name VARCHAR(255),
		title VARCHAR(1024),
		description TEXT NOT NULL,
		url VARCHAR(2048),
		published_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);



	CREATE TABLE IF NOT EXISTS s_euro_stat.regional_gdp (
		id SERIAL PRIMARY KEY,
		geo_code VARCHAR(50) NOT NULL,
		geo_name VARCHAR(255),
		year INTEGER NOT NULL,
		gdp_value NUMERIC,
		unit VARCHAR(50),
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		UNIQUE (geo_code, year, unit)
	);

	CREATE TABLE IF NOT EXISTS s_euro_stat.regional_crime_rates (
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

	CREATE TABLE IF NOT EXISTS s_euro_stat.inflation (
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

	CREATE TABLE IF NOT EXISTS s_euro_stat.quarterly_gdp (
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

	CREATE TABLE IF NOT EXISTS s_euro_stat.unemployment (
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

	CREATE TABLE IF NOT EXISTS s_euro_stat.house_price_index (
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

	CREATE TABLE IF NOT EXISTS s_euro_stat.fx_rates (
		id SERIAL PRIMARY KEY,
		base_currency VARCHAR(3) NOT NULL,
		target_currency VARCHAR(3) NOT NULL,
		rate NUMERIC NOT NULL,
		rate_date DATE NOT NULL,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		UNIQUE (base_currency, target_currency, rate_date)
	);

	CREATE TABLE IF NOT EXISTS s_yahoo_finance.stock_prices (
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



	INSERT INTO s_reddit.subreddits_monitored (name, active) VALUES ('smallbusiness', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO s_reddit.subreddits_monitored (name, active) VALUES ('saas', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO s_reddit.subreddits_monitored (name, active) VALUES ('solopreneur', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO s_reddit.subreddits_monitored (name, active) VALUES ('indiebiz', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO s_reddit.subreddits_monitored (name, active) VALUES ('entrepreneurship', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO s_reddit.subreddits_monitored (name, active) VALUES ('advancedentrepreneur', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO s_reddit.subreddits_monitored (name, active) VALUES ('entrepreneurridealong', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO s_reddit.subreddits_monitored (name, active) VALUES ('growmybusiness', TRUE) ON CONFLICT (name) DO NOTHING;

	INSERT INTO s_substack.feeds_monitored (name, feed_url, active) VALUES 
		('SeattleDataGuy', 'https://seattledataguy.substack.com/feed', TRUE),
		('Decision', 'https://decision.substack.com/feed', TRUE),
		('EngLeadership', 'https://newsletter.eng-leadership.com/feed', TRUE),
		('ThrivingInEngineering', 'https://thrivinginengineering.substack.com/feed', TRUE),
		('CodeLikeAGirl', 'https://codelikeagirl.substack.com/feed', TRUE),
		('Data Biz', 'https://jimmypang.substack.com/feed', TRUE),
		('Benn', 'https://benn.substack.com/feed', TRUE),
		('nilukakavanagh', 'https://nilukakavanagh.substack.com/feed', TRUE),
		('Datapreneur', 'https://nickvaliotti.substack.com/feed', TRUE)
	ON CONFLICT (name) DO NOTHING;

	INSERT INTO s_wordpress.feeds_monitored (name, feed_url, active) VALUES 
		('Towards Data Science', 'https://towardsdatascience.com/feed', TRUE)
	ON CONFLICT (name) DO NOTHING;
EOSQL

