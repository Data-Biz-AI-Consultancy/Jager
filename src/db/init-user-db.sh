#!/bin/sh
set -e

# Create databases
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	SELECT 'CREATE DATABASE n8n'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n')\gexec
	SELECT 'CREATE DATABASE cdp'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cdp')\gexec
EOSQL


# Initialize CDP database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "cdp" <<-EOSQL
	CREATE SCHEMA IF NOT EXISTS cdp;

	-- Client Account status lifecycle: 'prospect', 'reached', 'decision_maker_reached', 'contract_signed', 'engaging', 'completed'
	CREATE TABLE IF NOT EXISTS cdp.client_accounts (
		id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		company_name VARCHAR(255) NOT NULL,
		domain VARCHAR(255) UNIQUE,
		status VARCHAR(50) DEFAULT 'prospect',
		attributes JSONB DEFAULT '{}'::jsonb,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);


	CREATE TABLE IF NOT EXISTS cdp.persons (
		id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		first_name VARCHAR(255),
		last_name VARCHAR(255),
		primary_email VARCHAR(255) UNIQUE,
		primary_phone VARCHAR(100),
		linkedin_url VARCHAR(2048),
		city VARCHAR(100),
		country VARCHAR(100),
		primary_client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL,
		status VARCHAR(50) DEFAULT 'active',
		attributes JSONB DEFAULT '{}'::jsonb,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	-- LinkedIn Persons intake (sourced from s_linkedin.connections)
	CREATE TABLE IF NOT EXISTS cdp.persons_linkedins (
		connection_id VARCHAR(255) PRIMARY KEY,
		first_name VARCHAR(255),
		last_name VARCHAR(255),
		profile_url VARCHAR(2048),
		email_address VARCHAR(255),
		company VARCHAR(255),
		position VARCHAR(255),
		connected_at TIMESTAMP WITH TIME ZONE,
		raw_payload JSONB DEFAULT '{}'::jsonb,
		intake_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	-- Manual Substack Persons intake (sourced from s_manual)
	CREATE TABLE IF NOT EXISTS cdp.persons_manual_substack (
		id VARCHAR(255) PRIMARY KEY,
		email VARCHAR(255),
		first_name VARCHAR(255),
		last_name VARCHAR(255),
		full_name VARCHAR(255),
		phone VARCHAR(100),
		linkedin_url VARCHAR(2048),
		country VARCHAR(100),
		subscribed_at TIMESTAMP WITH TIME ZONE,
		source_table VARCHAR(255),
		raw_payload JSONB DEFAULT '{}'::jsonb,
		intake_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);


	-- LinkedIn Leads intake (sourced from s_linkedin.messages)
	CREATE TABLE IF NOT EXISTS cdp.leads_linkedin (
		conversation_id VARCHAR(255) PRIMARY KEY,
		person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL,
		full_name VARCHAR(255),
		description TEXT,
		message_count INTEGER DEFAULT 0,
		summary TEXT,
		convo_history TEXT,
		intent VARCHAR(100),
		signal_strength VARCHAR(50),
		opportunity_type VARCHAR(100),
		status VARCHAR(50) DEFAULT 'prospect',
		raw_payload JSONB DEFAULT '{}'::jsonb,
		intake_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	-- Manual Leads intake (sourced from s_manual)
	CREATE TABLE IF NOT EXISTS cdp.leads_manual (
		id VARCHAR(255) PRIMARY KEY,
		person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL,
		client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL,
		full_name VARCHAR(255),
		description TEXT,
		rate VARCHAR(100),
		status VARCHAR(50) DEFAULT 'prospect',
		source VARCHAR(100) DEFAULT 'manual',
		raw_payload JSONB DEFAULT '{}'::jsonb,
		intake_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	-- Lead status lifecycle: 'prospect', 'negotiating', 'offer_accepted', 'contract_signed', 'engaging', 'completed', 'nurture', 'disqualified'
	CREATE TABLE IF NOT EXISTS cdp.leads (
		id VARCHAR(255) PRIMARY KEY,
		person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL,
		client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL,
		full_name VARCHAR(255),
		description TEXT,
		message_count INTEGER DEFAULT 0,
		summary TEXT,
		convo_history TEXT,
		intent VARCHAR(100),
		signal_strength VARCHAR(50),
		opportunity_type VARCHAR(100),
		rate VARCHAR(100),
		status VARCHAR(50) DEFAULT 'prospect',
		source VARCHAR(100) NOT NULL DEFAULT 'Manual',
		raw_payload JSONB DEFAULT '{}'::jsonb,
		intake_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);
	ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS primary_client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL;
	ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS in_linkedin_connections BOOLEAN DEFAULT FALSE;
	ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS in_substack_subscriber_export BOOLEAN DEFAULT FALSE;
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL;
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL;
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS message_count INTEGER DEFAULT 0;
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS summary TEXT;
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS convo_history TEXT;
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS intent VARCHAR(100);
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS signal_strength VARCHAR(50);
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS opportunity_type VARCHAR(100);
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS rate VARCHAR(100);
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS source VARCHAR(100) NOT NULL DEFAULT 'Manual';

	DO $$
	BEGIN
		IF EXISTS (
			SELECT 1 FROM information_schema.columns 
			WHERE table_schema = 'cdp' AND table_name = 'leads' AND column_name = 'conversation_id'
		) THEN
			ALTER TABLE cdp.leads RENAME COLUMN conversation_id TO id;
		END IF;

		IF EXISTS (
			SELECT 1 FROM information_schema.columns 
			WHERE table_schema = 'cdp' AND table_name = 'leads' AND column_name = 'id' AND data_type = 'uuid'
		) THEN
			ALTER TABLE cdp.leads ALTER COLUMN id TYPE VARCHAR(255);
		END IF;
	END $$;

	CREATE TABLE IF NOT EXISTS cdp.activities_notion_meeting_notes (
		page_id VARCHAR(255) PRIMARY KEY,
		person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL,
		client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL,
		database_name VARCHAR(255),
		title VARCHAR(1024),
		meeting_date TIMESTAMP WITH TIME ZONE,
		attendees TEXT,
		summary_or_content TEXT,
		to_dos JSONB DEFAULT '[]'::jsonb,
		url VARCHAR(2048),
		raw_payload JSONB DEFAULT '{}'::jsonb,
		intake_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS cdp.activities (
		id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		activity_type VARCHAR(50) NOT NULL DEFAULT 'meeting_note',
		source VARCHAR(100) NOT NULL DEFAULT 'notion_meeting_notes',
		source_id VARCHAR(255) UNIQUE,
		person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL,
		client_account_id UUID REFERENCES cdp.client_accounts(id) ON DELETE SET NULL,
		title VARCHAR(1024),
		activity_date TIMESTAMP WITH TIME ZONE,
		summary_or_content TEXT,
		to_dos JSONB DEFAULT '[]'::jsonb,
		participants TEXT,
		url VARCHAR(2048),
		metadata JSONB DEFAULT '{}'::jsonb,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS cdp.person_segments (
		id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		slug VARCHAR(64) UNIQUE NOT NULL,
		name VARCHAR(128) NOT NULL,
		description TEXT,
		segment_type VARCHAR(32) NOT NULL DEFAULT 'dynamic',
		criteria JSONB DEFAULT '{}'::jsonb,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS cdp.lead_segments (
		id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		slug VARCHAR(64) UNIQUE NOT NULL,
		name VARCHAR(128) NOT NULL,
		description TEXT,
		segment_type VARCHAR(32) NOT NULL DEFAULT 'dynamic',
		criteria JSONB DEFAULT '{}'::jsonb,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	DROP TABLE IF EXISTS cdp.person_segment_memberships;
	DROP TABLE IF EXISTS cdp.lead_segment_memberships;

	ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS person_segment_id UUID REFERENCES cdp.person_segments(id) ON DELETE SET NULL;
	ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS person_segment_name VARCHAR(128);
	ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS person_segment_slug VARCHAR(64);
	ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS engagement_temperature VARCHAR(32) DEFAULT 'cold';

	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS lead_segment_id UUID REFERENCES cdp.lead_segments(id) ON DELETE SET NULL;
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS lead_segment_name VARCHAR(128);
	ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS lead_segment_slug VARCHAR(64);

	-- Seed initial person segments (Opportunity-Based Framework)
	INSERT INTO cdp.person_segments (slug, name, description, segment_type, criteria) VALUES
	('clients_and_prospects', 'Clients & Prospects', 'Active or past consulting clients and warm lead opportunities', 'dynamic', '{"rule": "clients_and_prospects"}'::jsonb),
	('recruiters_and_talent', 'Recruiters & Talent Acquisition', 'Internal/agency recruiters, talent acquisition managers, talent partners, headhunters, and sourcers', 'dynamic', '{"rule": "recruiters_and_talent"}'::jsonb),
	('hiring_decision_makers', 'Hiring Decision-Makers', 'Founders, CTOs, VPs of Data/Engineering, Heads, and hiring decision makers', 'dynamic', '{"rule": "hiring_decision_makers"}'::jsonb),
	('peer_collaborators', 'Peer Collaborators & Agencies', 'Other consultants, agency owners, freelancers, tooling partners, or DevRel for project referrals/partnerships', 'dynamic', '{"rule": "peer_collaborators"}'::jsonb),
	('former_colleagues_alumni', 'Alumni & Former Colleagues', 'Alumni network contacts from target companies (HelloFresh, Delivery Hero, Foodpanda, Vestiaire)', 'dynamic', '{"rule": "former_colleagues_alumni"}'::jsonb),
	('general_network', 'General Network', 'General network contacts and audience members not belonging to specific opportunity segments', 'dynamic', '{"rule": "general_network"}'::jsonb)
	ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, criteria = EXCLUDED.criteria, updated_at = NOW();

	-- Seed initial lead segments
	INSERT INTO cdp.lead_segments (slug, name, description, segment_type, criteria) VALUES
	('new_leads_no_followup_7d', 'New Leads No Followup 7d', 'Leads in prospect status created 7+ days ago with zero engagement touchpoints', 'dynamic', '{"rule": "new_leads_no_followup_7d"}'::jsonb),
	('stale_in_negotiation', 'Stale In Negotiation', 'Leads in negotiating status with no touchpoints in the last 14 days', 'dynamic', '{"rule": "stale_in_negotiation"}'::jsonb),
	('high_intent_inbound', 'High Intent Inbound', 'Leads flagged with high intent or strong signal strength', 'dynamic', '{"rule": "high_intent_inbound"}'::jsonb),
	('contract_pending', 'Contract Pending', 'Leads in offer_accepted stage awaiting contract execution', 'dynamic', '{"rule": "contract_pending"}'::jsonb),
	('re_engagement_prospects', 'Re-engagement Prospects', 'Leads in nurture status whose contact has recent activity in last 30 days', 'dynamic', '{"rule": "re_engagement_prospects"}'::jsonb)
	ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, criteria = EXCLUDED.criteria, updated_at = NOW();
EOSQL


# Initialize OLTP database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
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
	CREATE SCHEMA IF NOT EXISTS s_buffer;
	CREATE SCHEMA IF NOT EXISTS s_manual;
	CREATE SCHEMA IF NOT EXISTS s_motherduck;




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

	CREATE TABLE IF NOT EXISTS s_zernio.linkedin_posts (
		id VARCHAR(255) PRIMARY KEY,
		content TEXT,
		url VARCHAR(2048),
		published_at TIMESTAMP WITH TIME ZONE,
		fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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

	CREATE TABLE IF NOT EXISTS s_zernio.linkedin_follower_stats_timeline (
		account_id VARCHAR(255),
		date DATE,
		followers_count INTEGER DEFAULT 0,
		growth INTEGER DEFAULT 0,
		growth_percentage NUMERIC(5,2) DEFAULT 0.00,
		fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
		PRIMARY KEY (account_id, date)
	);

	CREATE TABLE IF NOT EXISTS s_zernio.linkedin_post_timeline (
		post_id VARCHAR(255),
		date DATE,
		impressions INTEGER DEFAULT 0,
		reach INTEGER DEFAULT 0,
		likes INTEGER DEFAULT 0,
		comments INTEGER DEFAULT 0,
		shares INTEGER DEFAULT 0,
		saves INTEGER DEFAULT 0,
		clicks INTEGER DEFAULT 0,
		views INTEGER DEFAULT 0,
		fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
		PRIMARY KEY (post_id, date)
	);

	CREATE TABLE IF NOT EXISTS s_zernio.linkedin_content_decay (
		platform VARCHAR(50),
		bucket_order INTEGER,
		bucket_label VARCHAR(50),
		avg_pct_of_final NUMERIC(5,2),
		post_count INTEGER,
		fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
		PRIMARY KEY (platform, bucket_order)
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
		type VARCHAR(50) DEFAULT 'database',
		active BOOLEAN DEFAULT TRUE,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);
	ALTER TABLE s_notion.databases_monitored ADD COLUMN IF NOT EXISTS type VARCHAR(50) DEFAULT 'database';

	CREATE TABLE IF NOT EXISTS s_notion.pages (
		id VARCHAR(255) PRIMARY KEY,
		database_id VARCHAR(255) REFERENCES s_notion.databases_monitored(database_id) ON DELETE CASCADE,
		title VARCHAR(1024),
		content TEXT,
		properties JSONB DEFAULT '{}'::jsonb,
		cover_url VARCHAR(2048),
		icon VARCHAR(1024),
		url VARCHAR(2048),
		created_time TIMESTAMP WITH TIME ZONE,
		last_edited_time TIMESTAMP WITH TIME ZONE,
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed INTEGER DEFAULT 0
	);

	ALTER TABLE s_notion.pages ADD COLUMN IF NOT EXISTS properties JSONB DEFAULT '{}'::jsonb;
	ALTER TABLE s_notion.pages ADD COLUMN IF NOT EXISTS cover_url VARCHAR(2048);
	ALTER TABLE s_notion.pages ADD COLUMN IF NOT EXISTS icon VARCHAR(1024);
	ALTER TABLE s_notion.pages ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
	ALTER TABLE s_notion.pages ADD COLUMN IF NOT EXISTS _dlt_load_id VARCHAR DEFAULT 'legacy';
	ALTER TABLE s_notion.pages ADD COLUMN IF NOT EXISTS _dlt_id VARCHAR DEFAULT 'legacy';

	CREATE TABLE IF NOT EXISTS s_notion.meeting_notes (
		id VARCHAR(255) PRIMARY KEY,
		database_id VARCHAR(255) REFERENCES s_notion.databases_monitored(database_id) ON DELETE CASCADE,
		title VARCHAR(1024),
		meeting_date TIMESTAMP WITH TIME ZONE,
		attendees TEXT,
		summary TEXT,
		transcription TEXT,
		action_items TEXT,
		recording_url VARCHAR(2048),
		properties JSONB DEFAULT '{}'::jsonb,
		url VARCHAR(2048),
		created_time TIMESTAMP WITH TIME ZONE,
		last_edited_time TIMESTAMP WITH TIME ZONE,
		processed INTEGER DEFAULT 0
	);

	ALTER TABLE s_notion.meeting_notes ADD COLUMN IF NOT EXISTS _dlt_load_id VARCHAR DEFAULT 'legacy';
	ALTER TABLE s_notion.meeting_notes ADD COLUMN IF NOT EXISTS _dlt_id VARCHAR DEFAULT 'legacy';

	CREATE TABLE IF NOT EXISTS s_buffer.channels (
		id VARCHAR(255) PRIMARY KEY,
		name VARCHAR(255),
		service VARCHAR(100),
		organization_id VARCHAR(255),
		active BOOLEAN DEFAULT TRUE,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
	);

	CREATE TABLE IF NOT EXISTS s_buffer.posts (
		id VARCHAR(255) PRIMARY KEY,
		text TEXT,
		channel_id VARCHAR(255) REFERENCES s_buffer.channels(id) ON DELETE CASCADE,
		due_at TIMESTAMP WITH TIME ZONE,
		status VARCHAR(50),
		assets JSONB DEFAULT '[]'::jsonb,
		metrics JSONB DEFAULT '[]'::jsonb,
		reactions INTEGER DEFAULT 0,
		comments INTEGER DEFAULT 0,
		shares INTEGER DEFAULT 0,
		reposts INTEGER DEFAULT 0,
		clicks INTEGER DEFAULT 0,
		reach INTEGER DEFAULT 0,
		impressions INTEGER DEFAULT 0,
		views INTEGER DEFAULT 0,
		engagement_rate NUMERIC DEFAULT 0.00,
		created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
		processed INTEGER DEFAULT 0
	);

	ALTER TABLE s_buffer.posts ADD COLUMN IF NOT EXISTS metrics JSONB DEFAULT '[]'::jsonb;
	ALTER TABLE s_buffer.posts ADD COLUMN IF NOT EXISTS reactions INTEGER DEFAULT 0;
	ALTER TABLE s_buffer.posts ADD COLUMN IF NOT EXISTS comments INTEGER DEFAULT 0;
	ALTER TABLE s_buffer.posts ADD COLUMN IF NOT EXISTS shares INTEGER DEFAULT 0;
	ALTER TABLE s_buffer.posts ADD COLUMN IF NOT EXISTS reposts INTEGER DEFAULT 0;
	ALTER TABLE s_buffer.posts ADD COLUMN IF NOT EXISTS clicks INTEGER DEFAULT 0;
	ALTER TABLE s_buffer.posts ADD COLUMN IF NOT EXISTS reach INTEGER DEFAULT 0;
	ALTER TABLE s_buffer.posts ADD COLUMN IF NOT EXISTS impressions INTEGER DEFAULT 0;
	ALTER TABLE s_buffer.posts ADD COLUMN IF NOT EXISTS views INTEGER DEFAULT 0;
	ALTER TABLE s_buffer.posts ADD COLUMN IF NOT EXISTS engagement_rate NUMERIC DEFAULT 0.00;





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

	INSERT INTO s_notion.databases_monitored (database_id, name, type, active) VALUES 
		('b5ad53f72b0e45e3b481e25da2703fd8', 'Leadership & Management', 'database', TRUE),
		('1686e98d4ef8806da4e1c28268b7365e', 'Data Science - AIs', 'database', TRUE),
		('4cd9498f5b5c48c6864d57bd36f7f82d', 'Data Science', 'database', TRUE),
		('32fcdb5f301b4a9c94329dcadeffca15', 'data engineering', 'database', TRUE),
		('f0501c9ac3bf4f0ea8d06b7ed6e40a31', 'Data Governance', 'database', TRUE),
		('8fc4f5d17d6644eaa6b199f11cb3bf2b', 'Data Visualization & Reporting', 'database', TRUE),
		('40906fc76abd4951bd4b283c9717d320', 'Product Management', 'database', TRUE),
		('2bdfbb81d5c043d0a5fdd3028ad2504f', 'Product Analytics', 'database', TRUE),
		('1d362ecd225241c0ab3c0fe4d0ed3cda', 'Software Engineering', 'database', TRUE),
		('2d56e98d4ef8806ba96cca38539b67e1', 'Business', 'database', TRUE),
		('f34619396f3c4be8b96fa64211eb18d7', 'Career', 'database', TRUE),
		('3876e98d4ef8807eab9be1b0b029246c', 'Interview Meeting notes', 'meeting_notes', TRUE),
		('3876e98d4ef880a6a61ae99d8912694f', 'Meetups & Seminars', 'meeting_notes', TRUE),
		('3a36e98d4ef88084a1aec60052a3cb80', 'FaDi meeting notes', 'meeting_notes', TRUE)
	ON CONFLICT (database_id) DO UPDATE SET name = EXCLUDED.name, type = EXCLUDED.type, active = TRUE;

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

