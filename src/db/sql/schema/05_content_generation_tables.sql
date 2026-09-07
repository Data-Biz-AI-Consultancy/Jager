-- t_content_generation
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
