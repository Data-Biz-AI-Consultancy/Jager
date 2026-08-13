-- Seed initial person segments (Opportunity-Based Framework)
INSERT INTO cdp.person_segments (slug, name, description, segment_type, potential_opportunity_types, criteria) VALUES
('clients_and_prospects', 'Clients & Prospects', 'Active or past consulting clients and warm lead opportunities', 'dynamic', 'Consulting Projects, Advisory, Fractional Data Leadership', '{"rule": "clients_and_prospects"}'::jsonb),
('recruiters_and_talent', 'Recruiters & Talent Acquisition', 'Internal/agency recruiters, talent acquisition managers, talent partners, headhunters, and sourcers', 'dynamic', 'Full-Time Employment, Contract Roles, Fractional Opportunities', '{"rule": "recruiters_and_talent"}'::jsonb),
('hiring_decision_makers', 'Hiring Decision-Makers', 'Founders, CTOs, VPs of Data/Engineering, Heads, and hiring decision makers', 'dynamic', 'Consulting Projects, Full-Time Employment, Fractional Leadership', '{"rule": "hiring_decision_makers"}'::jsonb),
('peer_collaborators', 'Peer Collaborators & Agencies', 'Other consultants, agency owners, freelancers, tooling partners, or DevRel for project referrals/partnerships', 'dynamic', 'Project Subcontracting, Co-bidding, Client Referrals, Tooling Implementations', '{"rule": "peer_collaborators"}'::jsonb),
('former_colleagues_alumni', 'Alumni & Former Colleagues', 'Alumni network contacts from target companies (HelloFresh, Delivery Hero, Foodpanda, Vestiaire)', 'dynamic', 'Referrals, Re-hiring, Warm Client Introductions, Partnering', '{"rule": "former_colleagues_alumni"}'::jsonb),
('general_network', 'General Network', 'General network contacts and audience members not belonging to specific opportunity segments', 'dynamic', 'Brand Awareness, Audience Engagement, Content Reach', '{"rule": "general_network"}'::jsonb)
ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, potential_opportunity_types = EXCLUDED.potential_opportunity_types, criteria = EXCLUDED.criteria, updated_at = NOW();

-- Seed initial lead statuses (Canonical Lifecycle Stages, Funnel Mapping & End State Flag)
INSERT INTO cdp.lead_statuses (slug, name, stage, is_end_state, description, criteria) VALUES
('prospect', 'Prospect', 'awareness', FALSE, 'Default state upon lead intake/ingestion. No negotiation initiated yet.', '{"rule": "prospect"}'::jsonb),
('nurture', 'Nurture', 'awareness', FALSE, 'Long-term follow up or delayed opportunity.', '{"rule": "nurture"}'::jsonb),
('negotiating', 'Negotiating', 'consideration', FALSE, 'Rates, scope, or ROE discussions underway.', '{"rule": "negotiating"}'::jsonb),
('offer_accepted', 'Offer Accepted', 'consideration', FALSE, 'Rates and terms agreed; awaiting contract execution.', '{"rule": "offer_accepted"}'::jsonb),
('contract_signed', 'Contract Signed', 'conversion', FALSE, 'Contract fully executed and signed.', '{"rule": "contract_signed"}'::jsonb),
('engaging', 'Engaging', 'conversion', FALSE, 'Active project work period.', '{"rule": "engaging"}'::jsonb),
('completed', 'Completed', NULL, TRUE, 'Project or consulting engagement successfully finished.', '{"rule": "completed"}'::jsonb),
('disqualified', 'Disqualified', NULL, TRUE, 'Unresponsive, poor fit, or lost opportunity.', '{"rule": "disqualified"}'::jsonb)
ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, stage = EXCLUDED.stage, is_end_state = EXCLUDED.is_end_state, description = EXCLUDED.description, criteria = EXCLUDED.criteria, updated_at = NOW();
