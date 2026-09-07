-- s_analytics
CREATE TABLE IF NOT EXISTS s_analytics.directives (
	id SERIAL PRIMARY KEY,
	directive TEXT NOT NULL UNIQUE,
	active BOOLEAN DEFAULT TRUE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- s_reddit
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

-- s_slack
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

-- s_substack
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
ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS reaction_count INTEGER DEFAULT 0;
ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS reactions JSONB DEFAULT '{}'::jsonb;
ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS comment_count INTEGER DEFAULT 0;
ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS child_comment_count INTEGER DEFAULT 0;
ALTER TABLE s_substack.posts ADD COLUMN IF NOT EXISTS restacks INTEGER DEFAULT 0;
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

-- s_wordpress
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

-- s_meetup
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
