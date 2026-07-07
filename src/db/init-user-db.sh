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
	CREATE SCHEMA IF NOT EXISTS s_notion;
	CREATE SCHEMA IF NOT EXISTS s_zernio;


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
	CREATE EXTENSION IF NOT EXISTS vector;

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
		processed INTEGER DEFAULT 0,
		subtitle TEXT,
		slug VARCHAR(512),
		canonical_url VARCHAR(2048),
		audience VARCHAR(100),
		is_published BOOLEAN,
		type VARCHAR(100),
		meter_type VARCHAR(100),
		teaser_post_eligible BOOLEAN,
		wordcount INTEGER,
		language VARCHAR(50),
		post_date TIMESTAMP WITH TIME ZONE,
		updated_at TIMESTAMP WITH TIME ZONE,
		reaction_count INTEGER DEFAULT 0,
		reactions JSONB DEFAULT '{}'::jsonb,
		comment_count INTEGER DEFAULT 0,
		child_comment_count INTEGER DEFAULT 0,
		restacks INTEGER DEFAULT 0,
		cover_image VARCHAR(2048),
		cover_image_is_square BOOLEAN DEFAULT FALSE,
		cover_image_is_explicit BOOLEAN DEFAULT FALSE,
		body_html TEXT,
		truncated_body_text TEXT,
		section_id INTEGER,
		audio_items JSONB DEFAULT '[]'::jsonb,
		podcast_fields JSONB DEFAULT '{}'::jsonb,
		theme_variables JSONB DEFAULT '{}'::jsonb,
		comments JSONB DEFAULT '[]'::jsonb,
		inbox_item JSONB DEFAULT '{}'::jsonb
	);

	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS feed_name VARCHAR(255);
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS subtitle TEXT;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS slug VARCHAR(512);
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS canonical_url VARCHAR(2048);
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS audience VARCHAR(100);
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS is_published BOOLEAN;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS type VARCHAR(100);
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS meter_type VARCHAR(100);
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS teaser_post_eligible BOOLEAN;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS wordcount INTEGER;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS language VARCHAR(50);
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS post_date TIMESTAMP WITH TIME ZONE;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS comment_count INTEGER DEFAULT 0;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS child_comment_count INTEGER DEFAULT 0;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS restacks INTEGER DEFAULT 0;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS reactions JSONB DEFAULT '{}'::jsonb;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS reaction_count INTEGER DEFAULT 0;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS cover_image VARCHAR(2048);
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS cover_image_is_square BOOLEAN DEFAULT FALSE;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS cover_image_is_explicit BOOLEAN DEFAULT FALSE;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS body_html TEXT;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS truncated_body_text TEXT;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS section_id INTEGER;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS audio_items JSONB DEFAULT '[]'::jsonb;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS podcast_fields JSONB DEFAULT '{}'::jsonb;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS theme_variables JSONB DEFAULT '{}'::jsonb;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS comments JSONB DEFAULT '[]'::jsonb;
	ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS inbox_item JSONB DEFAULT '{}'::jsonb;

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

	CREATE TABLE IF NOT EXISTS s_linkedin.all_comments (
		id VARCHAR(255) PRIMARY KEY,
		post_id VARCHAR(255) NOT NULL,
		author VARCHAR(255),
		content TEXT,
		published_at TIMESTAMP WITH TIME ZONE,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.all_likes (
		id VARCHAR(255) PRIMARY KEY,
		post_id VARCHAR(255) NOT NULL,
		author VARCHAR(255),
		published_at TIMESTAMP WITH TIME ZONE,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.invitations (
		id VARCHAR(255) PRIMARY KEY,
		to_name VARCHAR(255),
		from_name VARCHAR(255),
		direction VARCHAR(50),
		inviter_profile_url VARCHAR(2048),
		invitee_profile_url VARCHAR(2048),
		message TEXT,
		sent_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.all_invitations (
		id VARCHAR(255) PRIMARY KEY,
		to_name VARCHAR(255),
		from_name VARCHAR(255),
		direction VARCHAR(50),
		inviter_profile_url VARCHAR(2048),
		invitee_profile_url VARCHAR(2048),
		message TEXT,
		sent_at TIMESTAMP WITH TIME ZONE,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.messages (
		id VARCHAR(255) PRIMARY KEY,
		conversation_id VARCHAR(255) NOT NULL,
		sender_name VARCHAR(255),
		recipient_name VARCHAR(255),
		sender_profile_url VARCHAR(2048),
		recipient_profile_urls VARCHAR(2048),
		subject VARCHAR(1024),
		content TEXT,
		folder VARCHAR(50),
		sent_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.connections (
		id VARCHAR(255) PRIMARY KEY,
		first_name VARCHAR(255),
		last_name VARCHAR(255),
		profile_url VARCHAR(2048),
		email_address VARCHAR(255),
		company VARCHAR(255),
		position VARCHAR(255),
		connected_at TIMESTAMP WITH TIME ZONE,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.following (
		id VARCHAR(255) PRIMARY KEY,
		entity_name VARCHAR(255),
		profile_url VARCHAR(2048),
		type VARCHAR(100),
		followed_at TIMESTAMP WITH TIME ZONE,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.searches (
		id VARCHAR(255) PRIMARY KEY,
		query_text TEXT,
		searched_at TIMESTAMP WITH TIME ZONE,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.job_applications (
		id VARCHAR(255) PRIMARY KEY,
		company_name VARCHAR(255),
		job_title VARCHAR(255),
		application_date TIMESTAMP WITH TIME ZONE,
		status VARCHAR(100),
		job_url VARCHAR(2048),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_linkedin.job_seeker_preferences (
		id VARCHAR(255) PRIMARY KEY,
		dream_companies TEXT,
		job_titles TEXT,
		locations TEXT,
		job_types TEXT,
		industries TEXT,
		company_sizes TEXT,
		activity_level VARCHAR(255),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed INTEGER DEFAULT 0
	);

	CREATE TABLE IF NOT EXISTS s_zernio.linkedin_post_analytics (
		post_id VARCHAR(255) PRIMARY KEY,
		impressions INTEGER DEFAULT 0,
		likes INTEGER DEFAULT 0,
		comments INTEGER DEFAULT 0,
		shares INTEGER DEFAULT 0,
		clicks INTEGER DEFAULT 0,
		saves INTEGER DEFAULT 0,
		sends INTEGER DEFAULT 0,
		fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
	);

	CREATE TABLE IF NOT EXISTS s_zernio.linkedin_account_analytics (
		account_id VARCHAR(255) PRIMARY KEY,
		platform VARCHAR(50) DEFAULT 'linkedin',
		username VARCHAR(255),
		impressions INTEGER DEFAULT 0,
		members_reached INTEGER DEFAULT 0,
		reactions INTEGER DEFAULT 0,
		comments INTEGER DEFAULT 0,
		reshares INTEGER DEFAULT 0,
		post_saves INTEGER DEFAULT 0,
		post_sends INTEGER DEFAULT 0,
		fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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

	CREATE TABLE IF NOT EXISTS s_notion.databases_monitored (
		database_id VARCHAR(255) PRIMARY KEY,
		name VARCHAR(255) NOT NULL,
		active BOOLEAN DEFAULT TRUE,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS s_notion.pages (
		id VARCHAR(255) PRIMARY KEY,
		database_id VARCHAR(255) REFERENCES s_notion.databases_monitored(database_id) ON DELETE CASCADE,
		title VARCHAR(1024),
		content TEXT,
		url VARCHAR(2048),
		created_time TIMESTAMP WITH TIME ZONE,
		last_edited_time TIMESTAMP WITH TIME ZONE,
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

	CREATE SCHEMA IF NOT EXISTS t_content_generation;

	CREATE TABLE IF NOT EXISTS t_content_generation.linkedin_posts (
		id SERIAL PRIMARY KEY,
		channel VARCHAR(50) NOT NULL,
		content TEXT NOT NULL,
		original_prompt_or_source TEXT,
		status VARCHAR(50) DEFAULT 'draft',
		is_approved BOOLEAN DEFAULT FALSE,
		slack_ts VARCHAR(100),
		scheduled_at TIMESTAMP WITH TIME ZONE,
		published_at TIMESTAMP WITH TIME ZONE,
		external_post_id VARCHAR(255),
		used_resources JSONB,
		is_scheduled BOOLEAN DEFAULT FALSE,
		is_published BOOLEAN DEFAULT FALSE,
		timezone VARCHAR(50) DEFAULT 'Europe/Berlin',
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	ALTER TABLE t_content_generation.linkedin_posts ADD COLUMN IF NOT EXISTS used_resources jsonb;
	ALTER TABLE t_content_generation.linkedin_posts ADD COLUMN IF NOT EXISTS is_scheduled BOOLEAN DEFAULT FALSE;
	ALTER TABLE t_content_generation.linkedin_posts ADD COLUMN IF NOT EXISTS is_published BOOLEAN DEFAULT FALSE;
	ALTER TABLE t_content_generation.linkedin_posts ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'Europe/Berlin';
	ALTER TABLE t_content_generation.linkedin_posts ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;

	CREATE TABLE IF NOT EXISTS t_content_generation.substack_articles (
		id SERIAL PRIMARY KEY,
		title VARCHAR(1024) NOT NULL,
		content TEXT NOT NULL,
		status VARCHAR(50) DEFAULT 'draft',
		is_approved BOOLEAN DEFAULT FALSE,
		slack_ts VARCHAR(100),
		original_prompt_or_source TEXT,
		used_resources JSONB,
		is_published BOOLEAN DEFAULT FALSE,
		published_at TIMESTAMP WITH TIME ZONE,
		external_post_id VARCHAR(255),
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	ALTER TABLE t_content_generation.substack_articles ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE;
	ALTER TABLE t_content_generation.substack_articles ADD COLUMN IF NOT EXISTS slack_ts VARCHAR(100);
	ALTER TABLE t_content_generation.substack_articles ADD COLUMN IF NOT EXISTS original_prompt_or_source TEXT;
	ALTER TABLE t_content_generation.substack_articles ADD COLUMN IF NOT EXISTS used_resources JSONB;
	ALTER TABLE t_content_generation.substack_articles ADD COLUMN IF NOT EXISTS is_published BOOLEAN DEFAULT FALSE;


	CREATE SCHEMA IF NOT EXISTS m_staging;
	CREATE SCHEMA IF NOT EXISTS m_fact;
	CREATE SCHEMA IF NOT EXISTS m_episodic;

	CREATE TABLE IF NOT EXISTS m_staging.notion_pages (
		id VARCHAR(255),
		database_id VARCHAR(255),
		title VARCHAR(1024),
		content TEXT,
		cleaned_content TEXT,
		category VARCHAR(255),
		executive_summary JSONB,
		content_hash VARCHAR(64) PRIMARY KEY,
		created_time TIMESTAMP WITH TIME ZONE,
		last_edited_time TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS m_staging.substack_posts (
		id VARCHAR(255),
		feed_id INTEGER,
		feed_name VARCHAR(255),
		author VARCHAR(255),
		title VARCHAR(1024),
		content TEXT,
		cleaned_content TEXT,
		category VARCHAR(255),
		executive_summary JSONB,
		content_hash VARCHAR(64) PRIMARY KEY,
		published_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS m_staging.linkedin_posts (
		id VARCHAR(255),
		author VARCHAR(255),
		content TEXT,
		cleaned_content TEXT,
		category VARCHAR(255),
		executive_summary JSONB,
		content_hash VARCHAR(64) PRIMARY KEY,
		published_at TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE SCHEMA IF NOT EXISTS m_embeddings;

 	CREATE TABLE IF NOT EXISTS m_embeddings.notion_pages (
		id VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
		content TEXT,
		metadata JSONB,
		embedding vector(768),
		source_id VARCHAR(255) GENERATED ALWAYS AS (metadata->>'id') STORED
	);

	CREATE TABLE IF NOT EXISTS m_embeddings.substack_posts (
		id VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
		content TEXT,
		metadata JSONB,
		embedding vector(768),
		source_id VARCHAR(255) GENERATED ALWAYS AS (metadata->>'id') STORED
	);

	CREATE TABLE IF NOT EXISTS m_embeddings.linkedin_posts (
		id VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
		content TEXT,
		metadata JSONB,
		embedding vector(768),
		source_id VARCHAR(255) GENERATED ALWAYS AS (metadata->>'id') STORED
	);

	ALTER TABLE m_embeddings.notion_pages ADD COLUMN IF NOT EXISTS source_id VARCHAR(255) GENERATED ALWAYS AS (metadata->>'id') STORED;
	ALTER TABLE m_embeddings.substack_posts ADD COLUMN IF NOT EXISTS source_id VARCHAR(255) GENERATED ALWAYS AS (metadata->>'id') STORED;
	ALTER TABLE m_embeddings.linkedin_posts ADD COLUMN IF NOT EXISTS source_id VARCHAR(255) GENERATED ALWAYS AS (metadata->>'id') STORED;

	CREATE OR REPLACE FUNCTION m_staging.delete_old_notion_embeddings()
	RETURNS TRIGGER AS $$
	BEGIN
		DELETE FROM m_embeddings.notion_pages WHERE source_id = OLD.id;
		RETURN NEW;
	END;
	$$ LANGUAGE plpgsql;

	DROP TRIGGER IF EXISTS trg_delete_old_notion_embeddings ON m_staging.notion_pages;
	CREATE TRIGGER trg_delete_old_notion_embeddings
	BEFORE UPDATE ON m_staging.notion_pages
	FOR EACH ROW
	WHEN (OLD.cleaned_content IS DISTINCT FROM NEW.cleaned_content)
	EXECUTE FUNCTION m_staging.delete_old_notion_embeddings();

	CREATE OR REPLACE FUNCTION m_staging.delete_old_substack_embeddings()
	RETURNS TRIGGER AS $$
	BEGIN
		DELETE FROM m_embeddings.substack_posts WHERE source_id = OLD.id;
		RETURN NEW;
	END;
	$$ LANGUAGE plpgsql;

	DROP TRIGGER IF EXISTS trg_delete_old_substack_embeddings ON m_staging.substack_posts;
	CREATE TRIGGER trg_delete_old_substack_embeddings
	BEFORE UPDATE ON m_staging.substack_posts
	FOR EACH ROW
	WHEN (OLD.cleaned_content IS DISTINCT FROM NEW.cleaned_content)
	EXECUTE FUNCTION m_staging.delete_old_substack_embeddings();

	CREATE OR REPLACE FUNCTION m_staging.delete_old_linkedin_embeddings()
	RETURNS TRIGGER AS $$
	BEGIN
		DELETE FROM m_embeddings.linkedin_posts WHERE source_id = OLD.id;
		RETURN NEW;
	END;
	$$ LANGUAGE plpgsql;

	DROP TRIGGER IF EXISTS trg_delete_old_linkedin_embeddings ON m_staging.linkedin_posts;
	CREATE TRIGGER trg_delete_old_linkedin_embeddings
	BEFORE UPDATE ON m_staging.linkedin_posts
	FOR EACH ROW
	WHEN (OLD.cleaned_content IS DISTINCT FROM NEW.cleaned_content)
	EXECUTE FUNCTION m_staging.delete_old_linkedin_embeddings();

	CREATE TABLE IF NOT EXISTS m_fact.memory_facts (
		id SERIAL PRIMARY KEY,
		entity_name VARCHAR(255) NOT NULL,
		entity_type VARCHAR(100) NOT NULL,
		fact_details TEXT NOT NULL,
		source_table VARCHAR(100) NOT NULL,
		source_id VARCHAR(255) NOT NULL,
		confidence NUMERIC,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS m_episodic.memory_events (
		id SERIAL PRIMARY KEY,
		event_name VARCHAR(255) NOT NULL,
		event_description TEXT NOT NULL,
		event_timestamp TIMESTAMP WITH TIME ZONE,
		actors JSONB,
		source_table VARCHAR(100) NOT NULL,
		source_id VARCHAR(255) NOT NULL,
		outcome TEXT,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);
EOSQL

