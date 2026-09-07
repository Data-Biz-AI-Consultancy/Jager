-- m_staging: cleaned/processed content ready for embedding
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

-- m_embeddings: vector embeddings for RAG
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

-- m_fact: extracted facts about entities
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

-- m_episodic: event log
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
