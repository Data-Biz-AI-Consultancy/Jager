import os
import sys
import json
from typing import Dict, Any, List
from sqlalchemy import text

cdp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
for path in (cdp_dir, root_dir):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from shared.db import setup_logging, get_db_engine
except ImportError:
    from utils import setup_logging, get_db_engine

logger = setup_logging("cdp-segment-processor")


PERSON_SEGMENT_RULES = {
    "clients_and_prospects": """
        SELECT DISTINCT p.id FROM cdp.persons p
        WHERE p.id IN (
            -- 1. Persons linked to cdp.activities or cdp.activities_notion_meeting_notes (excluding recruiters/HR contacts)
            SELECT a.person_id FROM cdp.activities a WHERE a.person_id IS NOT NULL
            UNION
            SELECT amn.person_id FROM cdp.activities_notion_meeting_notes amn WHERE amn.person_id IS NOT NULL
            UNION
            SELECT p2.id FROM cdp.persons p2
            JOIN cdp.activities a2 ON (
                (LENGTH(p2.first_name) >= 3 AND LENGTH(p2.last_name) >= 3 
                 AND a2.title ILIKE '%' || p2.first_name || '%' 
                 AND a2.title ILIKE '%' || p2.last_name || '%')
            )
            LEFT JOIN cdp.persons_linkedins pli2 ON (
                (p2.primary_email IS NOT NULL AND p2.primary_email = pli2.email_address)
                OR (p2.linkedin_url IS NOT NULL AND pli2.profile_url IS NOT NULL AND pli2.profile_url ILIKE '%' || p2.linkedin_url || '%')
                OR (LOWER(TRIM(p2.first_name)) = LOWER(TRIM(pli2.first_name)) AND LOWER(TRIM(p2.last_name)) = LOWER(TRIM(pli2.last_name)))
            )
            WHERE LOWER(p2.first_name) != 'jimmy' AND LOWER(p2.last_name) != 'pang'
              AND LOWER(COALESCE(pli2.position, '')) !~ '(recruiter|recruiting|talent acquisition|talent partner|talent manager|talent management|hr manager|headhunter|sourcer)'
            UNION
            SELECT p3.id FROM cdp.persons p3
            JOIN cdp.activities_notion_meeting_notes amn2 ON (
                (LENGTH(p3.first_name) >= 3 AND LENGTH(p3.last_name) >= 3 
                 AND amn2.title ILIKE '%' || p3.first_name || '%' 
                 AND amn2.title ILIKE '%' || p3.last_name || '%')
            )
            LEFT JOIN cdp.persons_linkedins pli3 ON (
                (p3.primary_email IS NOT NULL AND p3.primary_email = pli3.email_address)
                OR (p3.linkedin_url IS NOT NULL AND pli3.profile_url IS NOT NULL AND pli3.profile_url ILIKE '%' || p3.linkedin_url || '%')
                OR (LOWER(TRIM(p3.first_name)) = LOWER(TRIM(pli3.first_name)) AND LOWER(TRIM(p3.last_name)) = LOWER(TRIM(pli3.last_name)))
            )
            WHERE LOWER(p3.first_name) != 'jimmy' AND LOWER(p3.last_name) != 'pang'
              AND LOWER(COALESCE(pli3.position, '')) !~ '(recruiter|recruiting|talent acquisition|talent partner|talent manager|talent management|hr manager|headhunter|sourcer)'
            UNION
            -- 2. Persons with active consulting/service/project/business collaboration leads
            SELECT l.person_id FROM cdp.leads l
            WHERE LOWER(COALESCE(l.intent, '')) IN ('inbound_service_request', 'consulting_inquiry', 'project_inquiry')
               OR LOWER(COALESCE(l.status, '')) IN ('in_discussion', 'proposal_sent', 'negotiating', 'offer_accepted', 'won', 'active_client')
               OR LOWER(COALESCE(l.summary, '')) ~* '\\y(snowflake|migration|freelance|consulting|contract|project|data engineering|calendar invite|client|proposal|quote|project onboarding|exploring ai|databizaitech|new business|consultancy page|your site|gdpr)\\y'
        )
    """,
    "former_colleagues_alumni": """
        SELECT DISTINCT p.id FROM cdp.persons p
        JOIN cdp.persons_linkedins pli ON (
            (p.primary_email IS NOT NULL AND p.primary_email = pli.email_address)
            OR (p.linkedin_url IS NOT NULL AND pli.profile_url IS NOT NULL AND pli.profile_url ILIKE '%' || p.linkedin_url || '%')
            OR (LOWER(TRIM(p.first_name)) = LOWER(TRIM(pli.first_name)) AND LOWER(TRIM(p.last_name)) = LOWER(TRIM(pli.last_name)))
        )
        WHERE LOWER(COALESCE(pli.company, '')) ~ '(hayes|hays|foodpanda|delivery hero|hellofresh|hello fresh|vestiaire)'
    """,
    "recruiters_and_talent": """
        SELECT DISTINCT p.id FROM cdp.persons p
        JOIN cdp.persons_linkedins pli ON (
            (p.primary_email IS NOT NULL AND p.primary_email = pli.email_address)
            OR (p.linkedin_url IS NOT NULL AND pli.profile_url IS NOT NULL AND pli.profile_url ILIKE '%' || p.linkedin_url || '%')
            OR (LOWER(TRIM(p.first_name)) = LOWER(TRIM(pli.first_name)) AND LOWER(TRIM(p.last_name)) = LOWER(TRIM(pli.last_name)))
        )
        WHERE LOWER(COALESCE(pli.position, '')) ~ '(recruiter|recruiting|talent acquisition|talent partner|talent manager|talent management|hr manager|headhunter|sourcer|talent specialist)'
    """,
    "hiring_decision_makers": """
        SELECT DISTINCT p.id FROM cdp.persons p
        JOIN cdp.persons_linkedins pli ON (
            (p.primary_email IS NOT NULL AND p.primary_email = pli.email_address)
            OR (p.linkedin_url IS NOT NULL AND pli.profile_url IS NOT NULL AND pli.profile_url ILIKE '%' || p.linkedin_url || '%')
            OR (LOWER(TRIM(p.first_name)) = LOWER(TRIM(pli.first_name)) AND LOWER(TRIM(p.last_name)) = LOWER(TRIM(pli.last_name)))
        )
        WHERE LOWER(COALESCE(pli.position, '')) ~ '(founder|co-founder|cofounder|owner|partner|chief|ceo|cto|cfo|coo|cmo|cpo|cro|cio|cdo|vp|vice president|head|director|lead|manager|executive|principal)'
    """,
    "peer_collaborators": """
        SELECT DISTINCT p.id FROM cdp.persons p
        JOIN cdp.persons_linkedins pli ON (
            (p.primary_email IS NOT NULL AND p.primary_email = pli.email_address)
            OR (p.linkedin_url IS NOT NULL AND pli.profile_url IS NOT NULL AND pli.profile_url ILIKE '%' || p.linkedin_url || '%')
            OR (LOWER(TRIM(p.first_name)) = LOWER(TRIM(pli.first_name)) AND LOWER(TRIM(p.last_name)) = LOWER(TRIM(pli.last_name)))
        )
        WHERE LOWER(COALESCE(pli.position, '')) ~ '(agency|freelance|consultant|partner|advisor|contractor|devrel|developer advocate|developer relations|maintainer|creator|founding engineer)'
           OR LOWER(COALESCE(pli.company, '')) ~ '(agency|consulting|advisory|solutions|studio|dlthub|dlt|motherduck|n8n|airbyte|dagster|prefect|duckdb|snowflake|databricks|astronomer)'
    """
}

LEAD_SEGMENT_RULES = {
    "new_leads_no_followup_7d": """
        SELECT l.id FROM cdp.leads l
        LEFT JOIN cdp.engagements e ON (l.person_id = e.person_id OR l.company_id = e.company_id)
        WHERE l.status = 'prospect'
          AND l.intake_at <= NOW() - INTERVAL '7 days'
        GROUP BY l.id
        HAVING COUNT(e.id) = 0
    """,
    "stale_in_negotiation": """
        SELECT l.id FROM cdp.leads l
        LEFT JOIN cdp.engagements e ON (l.person_id = e.person_id OR l.company_id = e.company_id) AND e.occurred_at >= NOW() - INTERVAL '14 days'
        WHERE l.status = 'negotiating'
        GROUP BY l.id
        HAVING COUNT(e.id) = 0
    """,
    "high_intent_inbound": """
        SELECT l.id FROM cdp.leads l
        WHERE LOWER(COALESCE(l.intent, '')) IN ('high', 'high_intent', 'inbound', 'direct_inquiry')
           OR LOWER(COALESCE(l.signal_strength, '')) IN ('high', 'strong')
    """,
    "contract_pending": """
        SELECT l.id FROM cdp.leads l
        WHERE l.status = 'offer_accepted'
    """,
    "re_engagement_prospects": """
        SELECT l.id FROM cdp.leads l
        JOIN cdp.engagements e ON l.person_id = e.person_id
        WHERE l.status = 'nurture'
          AND e.occurred_at >= NOW() - INTERVAL '30 days'
        GROUP BY l.id
    """
}


def ensure_seed_segments(conn):
    """Ensures built-in seed segments exist in person_segments and lead_statuses tables."""
    person_seeds = [
        ("clients_and_prospects", "Clients & Prospects", "Active or past consulting clients and warm lead opportunities", "dynamic", "Consulting Projects, Advisory, Fractional Data Leadership", {"rule": "clients_and_prospects"}),
        ("recruiters_and_talent", "Recruiters & Talent Acquisition", "Internal/agency recruiters, talent acquisition managers, talent partners, headhunters, and sourcers", "dynamic", "Full-Time Employment, Contract Roles, Fractional Opportunities", {"rule": "recruiters_and_talent"}),
        ("hiring_decision_makers", "Hiring Decision-Makers", "Founders, CTOs, VPs of Data/Engineering, Heads, and hiring decision makers", "dynamic", "Consulting Projects, Full-Time Employment, Fractional Leadership", {"rule": "hiring_decision_makers"}),
        ("peer_collaborators", "Peer Collaborators & Agencies", "Other consultants, agency owners, freelancers, tooling partners, or DevRel for project referrals/partnerships", "dynamic", "Project Subcontracting, Co-bidding, Client Referrals, Tooling Implementations", {"rule": "peer_collaborators"}),
        ("former_colleagues_alumni", "Alumni & Former Colleagues", "Alumni network contacts from target companies (Hays, HelloFresh, Delivery Hero, Foodpanda, Vestiaire)", "dynamic", "Referrals, Re-hiring, Warm Client Introductions, Partnering", {"rule": "former_colleagues_alumni"}),
        ("general_network", "General Network", "General network contacts not belonging to specific opportunity segments", "dynamic", "Brand Awareness, Audience Engagement, Content Reach", {"rule": "general_network"}),
    ]

    for slug, name, desc, seg_type, opp_types, criteria in person_seeds:
        conn.execute(
            text("""
                INSERT INTO cdp.person_segments (slug, name, description, segment_type, potential_opportunity_types, criteria)
                VALUES (:slug, :name, :desc, :type, :opp_types, :criteria)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, potential_opportunity_types = EXCLUDED.potential_opportunity_types, criteria = EXCLUDED.criteria, updated_at = NOW();
            """),
            {"slug": slug, "name": name, "desc": desc, "type": seg_type, "opp_types": opp_types, "criteria": json.dumps(criteria)}
        )

    conn.execute(text("DELETE FROM cdp.person_segments WHERE slug IN ('community_and_audience', 'ecosystem_tooling_partners')"))

    lead_seeds = [
        ("prospect", "Prospect", "awareness", False, "Default state upon lead intake/ingestion. No negotiation initiated yet.", {"rule": "prospect"}),
        ("nurture", "Nurture", "awareness", False, "Long-term follow up or delayed opportunity.", {"rule": "nurture"}),
        ("negotiating", "Negotiating", "consideration", False, "Rates, scope, or ROE discussions underway.", {"rule": "negotiating"}),
        ("offer_accepted", "Offer Accepted", "consideration", False, "Rates and terms agreed; awaiting contract execution.", {"rule": "offer_accepted"}),
        ("contract_signed", "Contract Signed", "conversion", False, "Contract fully executed and signed.", {"rule": "contract_signed"}),
        ("engaging", "Engaging", "conversion", False, "Active project work period.", {"rule": "engaging"}),
        ("completed", "Completed", None, True, "Project or consulting engagement successfully finished.", {"rule": "completed"}),
        ("disqualified", "Disqualified", None, True, "Unresponsive, poor fit, or lost opportunity.", {"rule": "disqualified"}),
    ]

    for slug, name, stage, is_end_state, desc, criteria in lead_seeds:
        conn.execute(
            text("""
                INSERT INTO cdp.lead_statuses (slug, name, stage, is_end_state, description, criteria)
                VALUES (:slug, :name, :stage, :is_end_state, :desc, :criteria)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, stage = EXCLUDED.stage, is_end_state = EXCLUDED.is_end_state, description = EXCLUDED.description, criteria = EXCLUDED.criteria, updated_at = NOW();
            """),
            {"slug": slug, "name": name, "stage": stage, "is_end_state": is_end_state, "desc": desc, "criteria": json.dumps(criteria)}
        )


def evaluate_person_segments(conn) -> Dict[str, int]:
    """Evaluates dynamic person segments in priority order and updates cdp.persons (mutually exclusive)."""
    results = {}
    
    # 1. Reset segment fields
    conn.execute(text("UPDATE cdp.persons SET person_segment_id = NULL, person_segment_name = NULL, person_segment_slug = NULL, potential_opportunity_types = NULL"))

    segment_priority = [
        "clients_and_prospects",
        "former_colleagues_alumni",
        "recruiters_and_talent",
        "hiring_decision_makers",
        "peer_collaborators",
    ]

    segments_by_slug = {}
    rows = conn.execute(text("SELECT id, slug, name, segment_type, potential_opportunity_types, criteria FROM cdp.person_segments")).fetchall()
    for row in rows:
        segments_by_slug[row[1]] = row

    for slug in segment_priority:
        if slug not in segments_by_slug or slug not in PERSON_SEGMENT_RULES:
            continue
        seg = segments_by_slug[slug]
        seg_id, seg_name, opp_types = seg[0], seg[2], seg[4]

        sql_query = PERSON_SEGMENT_RULES[slug]
        matching_person_rows = conn.execute(text(sql_query)).fetchall()
        matching_person_ids = [row[0] for row in matching_person_rows]

        if matching_person_ids:
            conn.execute(
                text("""
                    UPDATE cdp.persons 
                    SET person_segment_id = :seg_id,
                        person_segment_name = :seg_name,
                        person_segment_slug = :seg_slug,
                        potential_opportunity_types = :opp_types
                    WHERE id IN :person_ids
                      AND person_segment_id IS NULL
                """),
                {"seg_id": seg_id, "seg_name": seg_name, "seg_slug": slug, "opp_types": opp_types, "person_ids": tuple(matching_person_ids)}
            )

        assigned_count = conn.execute(text("SELECT COUNT(*) FROM cdp.persons WHERE person_segment_slug = :slug"), {"slug": slug}).scalar()
        results[slug] = assigned_count

    # 2. Fallback unclassified contacts to 'general_network' (No NULLs)
    gen_seg = segments_by_slug.get("general_network")
    if gen_seg:
        unassigned = conn.execute(text("""
            UPDATE cdp.persons 
            SET person_segment_id = :seg_id,
                person_segment_name = :seg_name,
                person_segment_slug = :seg_slug,
                potential_opportunity_types = :opp_types
            WHERE person_segment_id IS NULL
        """), {"seg_id": gen_seg[0], "seg_name": gen_seg[2], "seg_slug": gen_seg[1], "opp_types": gen_seg[4]}).rowcount
        results["general_network"] = unassigned

    return results


def evaluate_engagement_temperature(conn) -> Dict[str, int]:
    """Evaluates engagement temperature for all Persons: hot (30d), warm (90d), dormant (>90d), cold (0 interaction)."""
    # 1. Reset default to cold
    conn.execute(text("UPDATE cdp.persons SET engagement_temperature = 'cold'"))

    # 2. Dormant: past touchpoints/activities but none in 90d
    conn.execute(text("""
        UPDATE cdp.persons SET engagement_temperature = 'dormant'
        WHERE (EXISTS (SELECT 1 FROM cdp.engagements e WHERE e.person_id = cdp.persons.id)
               OR EXISTS (SELECT 1 FROM cdp.activities a WHERE a.person_id = cdp.persons.id))
          AND NOT EXISTS (SELECT 1 FROM cdp.engagements e WHERE e.person_id = cdp.persons.id AND e.occurred_at >= NOW() - INTERVAL '90 days')
          AND NOT EXISTS (SELECT 1 FROM cdp.activities a WHERE a.person_id = cdp.persons.id AND a.activity_date >= NOW() - INTERVAL '90 days')
    """))

    # 3. Warm: touchpoints/activities in 90d OR active in Substack/LinkedIn
    conn.execute(text("""
        UPDATE cdp.persons SET engagement_temperature = 'warm'
        WHERE (EXISTS (SELECT 1 FROM cdp.engagements e WHERE e.person_id = cdp.persons.id AND e.occurred_at >= NOW() - INTERVAL '90 days')
               OR EXISTS (SELECT 1 FROM cdp.activities a WHERE a.person_id = cdp.persons.id AND a.activity_date >= NOW() - INTERVAL '90 days')
               OR in_substack_subscriber_export = TRUE OR in_linkedin_connections = TRUE)
    """))

    # 4. Hot: touchpoints/activities in 30d
    conn.execute(text("""
        UPDATE cdp.persons SET engagement_temperature = 'hot'
        WHERE (EXISTS (SELECT 1 FROM cdp.engagements e WHERE e.person_id = cdp.persons.id AND e.occurred_at >= NOW() - INTERVAL '30 days')
               OR EXISTS (SELECT 1 FROM cdp.activities a WHERE a.person_id = cdp.persons.id AND a.activity_date >= NOW() - INTERVAL '30 days'))
    """))

    # Return counts breakdown
    counts = conn.execute(text("""
        SELECT engagement_temperature, COUNT(*) FROM cdp.persons GROUP BY engagement_temperature
    """)).fetchall()

    return {row[0]: row[1] for row in counts}


def evaluate_lead_statuses(conn) -> Dict[str, int]:
    """Evaluates lead statuses matching cdp.leads.status and updates lead_status_id, lead_status_name, lead_status_slug, lead_stage_slug, lead_stage_name on cdp.leads."""
    results = {}
    statuses = conn.execute(text("SELECT id, slug, name, stage FROM cdp.lead_statuses")).fetchall()
    status_map = {row[1]: (row[0], row[2], row[3]) for row in statuses}

    stage_display_names = {
        "awareness": "1. Awareness",
        "consideration": "2. Consideration",
        "conversion": "3. Conversion",
    }

    # Reset all lead status references
    conn.execute(text("UPDATE cdp.leads SET lead_status_id = NULL, lead_status_name = NULL, lead_status_slug = NULL, lead_stage_slug = NULL, lead_stage_name = NULL"))

    for slug, (status_id, status_name, stage_slug) in status_map.items():
        stage_name = stage_display_names.get(stage_slug, stage_slug.title()) if stage_slug else None
        count = conn.execute(
            text("""
                UPDATE cdp.leads 
                SET lead_status_id = :status_id,
                    lead_status_name = :status_name,
                    lead_status_slug = :slug,
                    lead_stage_slug = :stage_slug,
                    lead_stage_name = :stage_name
                WHERE LOWER(COALESCE(status, 'prospect')) = :slug
            """),
            {
                "status_id": status_id,
                "status_name": status_name,
                "slug": slug,
                "stage_slug": stage_slug,
                "stage_name": stage_name,
            }
        ).rowcount

        results[slug] = count

    return results


def evaluate_segments() -> Dict[str, Any]:
    """Evaluates all Person dynamic segments, Lead statuses, and engagement temperatures in CDP database."""
    logger.info("Starting CDP segment, status, and engagement temperature evaluation for Persons and Leads...")
    cdp_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/cdp", env_var="DATABASE_URL")

    with cdp_engine.begin() as conn:
        ensure_seed_segments(conn)
        person_results = evaluate_person_segments(conn)
        temperature_results = evaluate_engagement_temperature(conn)
        lead_results = evaluate_lead_statuses(conn)

    logger.info(f"CDP evaluation completed. Persons: {person_results}, Temperature: {temperature_results}, Lead Statuses: {lead_results}")
    return {
        "status": "success",
        "person_segments": person_results,
        "engagement_temperatures": temperature_results,
        "lead_statuses": lead_results
    }


if __name__ == "__main__":
    summary = evaluate_segments()
    print(json.dumps(summary, indent=2))
