-- s_linkedin
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

CREATE TABLE IF NOT EXISTS s_linkedin.all_messages (
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
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
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

CREATE TABLE IF NOT EXISTS s_linkedin.instant_reposts (
	id VARCHAR(255) PRIMARY KEY,
	original_post_id VARCHAR(255),
	original_author VARCHAR(255),
	repost_commentary TEXT,
	reposted_at TIMESTAMP WITH TIME ZONE,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	processed INTEGER DEFAULT 0
);

-- s_zernio
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

-- s_notion
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

-- s_buffer
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
