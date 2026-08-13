CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS cdp;

-- Company status lifecycle: 'prospect', 'reached', 'decision_maker_reached', 'contract_signed', 'engaging', 'completed'
CREATE TABLE IF NOT EXISTS cdp.companies (
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
	primary_company_id UUID REFERENCES cdp.companies(id) ON DELETE SET NULL,
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
	company_id UUID REFERENCES cdp.companies(id) ON DELETE SET NULL,
	full_name VARCHAR(255),
	description TEXT,
	rate VARCHAR(100),
	status VARCHAR(50) DEFAULT 'prospect',
	source VARCHAR(100) DEFAULT 'manual',
	raw_payload JSONB DEFAULT '{}'::jsonb,
	intake_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Aggregated Lead status lifecycle
CREATE TABLE IF NOT EXISTS cdp.leads (
	id VARCHAR(255) PRIMARY KEY,
	person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL,
	company_id UUID REFERENCES cdp.companies(id) ON DELETE SET NULL,
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

CREATE TABLE IF NOT EXISTS cdp.person_company_relationships (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	person_id UUID NOT NULL REFERENCES cdp.persons(id) ON DELETE CASCADE,
	company_id UUID NOT NULL REFERENCES cdp.companies(id) ON DELETE CASCADE,
	job_title VARCHAR(255),
	department VARCHAR(100),
	role_type VARCHAR(50) DEFAULT 'decision_maker',
	is_primary BOOLEAN DEFAULT TRUE,
	start_date DATE,
	end_date DATE,
	status VARCHAR(50) DEFAULT 'active',
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (person_id, company_id, role_type)
);

CREATE TABLE IF NOT EXISTS cdp.engagements (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL,
	company_id UUID REFERENCES cdp.companies(id) ON DELETE SET NULL,
	engagement_type VARCHAR(50) NOT NULL,
	direction VARCHAR(20) DEFAULT 'inbound',
	subject VARCHAR(1024),
	summary_or_content TEXT,
	channel VARCHAR(100),
	status VARCHAR(50) DEFAULT 'completed',
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	metadata JSONB DEFAULT '{}'::jsonb,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cdp.activities_notion_meeting_notes (
	page_id VARCHAR(255) PRIMARY KEY,
	person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL,
	company_id UUID REFERENCES cdp.companies(id) ON DELETE SET NULL,
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
	company_id UUID REFERENCES cdp.companies(id) ON DELETE SET NULL,
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

ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS primary_company_id UUID REFERENCES cdp.companies(id) ON DELETE SET NULL;
ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS in_linkedin_connections BOOLEAN DEFAULT FALSE;
ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS in_substack_subscriber_export BOOLEAN DEFAULT FALSE;
ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS person_id UUID REFERENCES cdp.persons(id) ON DELETE SET NULL;
ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES cdp.companies(id) ON DELETE SET NULL;
ALTER TABLE IF EXISTS cdp.person_company_relationships ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES cdp.companies(id) ON DELETE CASCADE;
ALTER TABLE IF EXISTS cdp.activities ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES cdp.companies(id) ON DELETE SET NULL;
ALTER TABLE IF EXISTS cdp.engagements ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES cdp.companies(id) ON DELETE SET NULL;

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
		SELECT 1 FROM information_schema.tables 
		WHERE table_schema = 'cdp' AND table_name = 'client_accounts'
	) AND NOT EXISTS (
		SELECT 1 FROM information_schema.tables 
		WHERE table_schema = 'cdp' AND table_name = 'companies'
	) THEN
		ALTER TABLE cdp.client_accounts RENAME TO companies;
	END IF;

	IF EXISTS (
		SELECT 1 FROM information_schema.tables 
		WHERE table_schema = 'cdp' AND table_name = 'person_account_relationships'
	) AND NOT EXISTS (
		SELECT 1 FROM information_schema.tables 
		WHERE table_schema = 'cdp' AND table_name = 'person_company_relationships'
	) THEN
		ALTER TABLE cdp.person_account_relationships RENAME TO person_company_relationships;
	END IF;

	IF EXISTS (
		SELECT 1 FROM information_schema.columns 
		WHERE table_schema = 'cdp' AND table_name = 'person_company_relationships' AND column_name = 'client_account_id'
	) THEN
		ALTER TABLE cdp.person_company_relationships RENAME COLUMN client_account_id TO company_id;
	END IF;

	IF EXISTS (
		SELECT 1 FROM information_schema.columns 
		WHERE table_schema = 'cdp' AND table_name = 'persons' AND column_name = 'primary_client_account_id'
	) THEN
		ALTER TABLE cdp.persons RENAME COLUMN primary_client_account_id TO primary_company_id;
	END IF;

	IF EXISTS (
		SELECT 1 FROM information_schema.columns 
		WHERE table_schema = 'cdp' AND table_name = 'leads' AND column_name = 'client_account_id'
	) THEN
		ALTER TABLE cdp.leads RENAME COLUMN client_account_id TO company_id;
	END IF;

	IF EXISTS (
		SELECT 1 FROM information_schema.columns 
		WHERE table_schema = 'cdp' AND table_name = 'leads_manual' AND column_name = 'client_account_id'
	) THEN
		ALTER TABLE cdp.leads_manual RENAME COLUMN client_account_id TO company_id;
	END IF;

	IF EXISTS (
		SELECT 1 FROM information_schema.columns 
		WHERE table_schema = 'cdp' AND table_name = 'activities_notion_meeting_notes' AND column_name = 'client_account_id'
	) THEN
		ALTER TABLE cdp.activities_notion_meeting_notes RENAME COLUMN client_account_id TO company_id;
	END IF;

	IF EXISTS (
		SELECT 1 FROM information_schema.columns 
		WHERE table_schema = 'cdp' AND table_name = 'activities' AND column_name = 'client_account_id'
	) THEN
		ALTER TABLE cdp.activities RENAME COLUMN client_account_id TO company_id;
	END IF;

	IF EXISTS (
		SELECT 1 FROM information_schema.columns 
		WHERE table_schema = 'cdp' AND table_name = 'leads' AND column_name = 'conversation_id'
	) AND NOT EXISTS (
		SELECT 1 FROM information_schema.columns 
		WHERE table_schema = 'cdp' AND table_name = 'leads' AND column_name = 'id'
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

CREATE TABLE IF NOT EXISTS cdp.lead_statuses (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	slug VARCHAR(64) UNIQUE NOT NULL,
	name VARCHAR(128) NOT NULL,
	stage VARCHAR(32),
	is_end_state BOOLEAN NOT NULL DEFAULT FALSE,
	description TEXT,
	criteria JSONB DEFAULT '{}'::jsonb,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DROP TABLE IF EXISTS cdp.person_segment_memberships;
DROP TABLE IF EXISTS cdp.lead_status_memberships;

ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS person_segment_id UUID REFERENCES cdp.person_segments(id) ON DELETE SET NULL;
ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS person_segment_name VARCHAR(128);
ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS person_segment_slug VARCHAR(64);
ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS potential_opportunity_types TEXT;
ALTER TABLE cdp.persons ADD COLUMN IF NOT EXISTS engagement_temperature VARCHAR(32) DEFAULT 'cold';

ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS lead_status_id UUID REFERENCES cdp.lead_statuses(id) ON DELETE SET NULL;
ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS lead_status_name VARCHAR(128);
ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS lead_status_slug VARCHAR(64);
ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS lead_stage_slug VARCHAR(64);
ALTER TABLE cdp.leads ADD COLUMN IF NOT EXISTS lead_stage_name VARCHAR(128);

ALTER TABLE cdp.person_segments ADD COLUMN IF NOT EXISTS potential_opportunity_types TEXT;
