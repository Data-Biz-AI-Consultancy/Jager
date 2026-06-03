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

	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('smallbusiness', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('saas', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('solopreneur', TRUE) ON CONFLICT (name) DO NOTHING;
	INSERT INTO reddit_subreddits_monitored (name, active) VALUES ('indiebiz', TRUE) ON CONFLICT (name) DO NOTHING;
EOSQL

