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
        JOIN cdp.leads l ON p.id = l.person_id
    """,
    "hiring_decision_makers": """
        SELECT DISTINCT p.id FROM cdp.persons p
        LEFT JOIN cdp.person_account_relationships r ON p.id = r.person_id
        LEFT JOIN cdp.persons_linkedins pli ON (
            (p.primary_email IS NOT NULL AND p.primary_email = pli.email_address)
            OR (p.linkedin_url IS NOT NULL AND pli.profile_url IS NOT NULL AND p.linkedin_url ILIKE '%' || pli.profile_url || '%')
        )
        WHERE r.id IS NOT NULL
           OR LOWER(COALESCE(pli.position, '')) ~ '(ceo|cto|cfo|coo|vp|vice president|director|head of|founder|owner|chief|hiring manager)'
    """,
    "peer_collaborators": """
        SELECT DISTINCT p.id FROM cdp.persons p
        JOIN cdp.persons_linkedins pli ON (
            (p.primary_email IS NOT NULL AND p.primary_email = pli.email_address)
            OR (p.linkedin_url IS NOT NULL AND pli.profile_url IS NOT NULL AND p.linkedin_url ILIKE '%' || pli.profile_url || '%')
        )
        WHERE LOWER(COALESCE(pli.position, '')) ~ '(agency|freelance|consultant|partner|advisor|contractor)'
           OR LOWER(COALESCE(pli.company, '')) ~ '(agency|consulting|advisory|solutions|studio)'
    """,
    "ecosystem_tooling_partners": """
        SELECT DISTINCT p.id FROM cdp.persons p
        JOIN cdp.persons_linkedins pli ON (
            (p.primary_email IS NOT NULL AND p.primary_email = pli.email_address)
            OR (p.linkedin_url IS NOT NULL AND pli.profile_url IS NOT NULL AND p.linkedin_url ILIKE '%' || pli.profile_url || '%')
        )
        WHERE LOWER(COALESCE(pli.company, '')) ~ '(dlthub|dlt|motherduck|n8n|airbyte|dagster|prefect|duckdb|snowflake|databricks|astronomer)'
           OR LOWER(COALESCE(pli.position, '')) ~ '(devrel|developer advocate|developer relations|maintainer|creator|founding engineer)'
    """,
    "former_colleagues_alumni": """
        SELECT DISTINCT p.id FROM cdp.persons p
        JOIN cdp.persons_linkedins pli ON (
            (p.primary_email IS NOT NULL AND p.primary_email = pli.email_address)
            OR (p.linkedin_url IS NOT NULL AND pli.profile_url IS NOT NULL AND p.linkedin_url ILIKE '%' || pli.profile_url || '%')
        )
        WHERE LOWER(COALESCE(pli.company, '')) ~ '(hellofresh|delivery hero|foodpanda|vestiaire)'
    """
}

LEAD_SEGMENT_RULES = {
    "new_leads_no_followup_7d": """
        SELECT l.id FROM cdp.leads l
        LEFT JOIN cdp.engagements e ON (l.person_id = e.person_id OR l.client_account_id = e.client_account_id)
        WHERE l.status = 'prospect'
          AND l.intake_at <= NOW() - INTERVAL '7 days'
        GROUP BY l.id
        HAVING COUNT(e.id) = 0
    """,
    "stale_in_negotiation": """
        SELECT l.id FROM cdp.leads l
        LEFT JOIN cdp.engagements e ON (l.person_id = e.person_id OR l.client_account_id = e.client_account_id) AND e.occurred_at >= NOW() - INTERVAL '14 days'
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
    """Ensures built-in seed segments exist in person_segments and lead_segments tables."""
    person_seeds = [
        ("clients_and_prospects", "Clients & Prospects", "Active or past consulting clients and warm lead opportunities", "dynamic", {"rule": "clients_and_prospects"}),
        ("hiring_decision_makers", "Hiring Decision-Makers", "Founders, CTOs, VPs of Data/Engineering, and hiring decision makers", "dynamic", {"rule": "hiring_decision_makers"}),
        ("peer_collaborators", "Peer Collaborators & Agencies", "Other consultants, agency owners, or freelancers for project referrals/partnerships", "dynamic", {"rule": "peer_collaborators"}),
        ("ecosystem_tooling_partners", "Ecosystem & Tooling Partners", "Founders, maintainers, DevRel, and creators at data/AI tooling platforms (e.g. dltHub, MotherDuck, n8n)", "dynamic", {"rule": "ecosystem_tooling_partners"}),
        ("former_colleagues_alumni", "Alumni & Former Colleagues", "Alumni network contacts from target companies (HelloFresh, Delivery Hero, Foodpanda, Vestiaire)", "dynamic", {"rule": "former_colleagues_alumni"}),
        ("general_network", "General Network", "General network contacts not belonging to specific opportunity segments", "dynamic", {"rule": "general_network"}),
    ]

    for slug, name, desc, seg_type, criteria in person_seeds:
        conn.execute(
            text("""
                INSERT INTO cdp.person_segments (slug, name, description, segment_type, criteria)
                VALUES (:slug, :name, :desc, :type, :criteria)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, criteria = EXCLUDED.criteria, updated_at = NOW();
            """),
            {"slug": slug, "name": name, "desc": desc, "type": seg_type, "criteria": json.dumps(criteria)}
        )

    # Delete obsolete community_and_audience segment if present
    conn.execute(text("DELETE FROM cdp.person_segments WHERE slug = 'community_and_audience'"))

    lead_seeds = [
        ("new_leads_no_followup_7d", "New Leads No Followup 7d", "Leads in prospect status created 7+ days ago with zero engagement", "dynamic", {"rule": "new_leads_no_followup_7d"}),
        ("stale_in_negotiation", "Stale In Negotiation", "Leads in negotiating status with no touchpoints in last 14 days", "dynamic", {"rule": "stale_in_negotiation"}),
        ("high_intent_inbound", "High Intent Inbound", "Leads flagged with high intent or strong signal strength", "dynamic", {"rule": "high_intent_inbound"}),
        ("contract_pending", "Contract Pending", "Leads in offer_accepted stage awaiting contract execution", "dynamic", {"rule": "contract_pending"}),
        ("re_engagement_prospects", "Re-engagement Prospects", "Leads in nurture status whose contact has recent activity in last 30 days", "dynamic", {"rule": "re_engagement_prospects"}),
    ]

    for slug, name, desc, seg_type, criteria in lead_seeds:
        conn.execute(
            text("""
                INSERT INTO cdp.lead_segments (slug, name, description, segment_type, criteria)
                VALUES (:slug, :name, :desc, :type, :criteria)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, criteria = EXCLUDED.criteria, updated_at = NOW();
            """),
            {"slug": slug, "name": name, "desc": desc, "type": seg_type, "criteria": json.dumps(criteria)}
        )


def evaluate_person_segments(conn) -> Dict[str, int]:
    """Evaluates dynamic person segments and updates person_segment_id, person_segment_name, person_segment_slug on cdp.persons."""
    results = {}
    
    # 1. Reset segment fields
    conn.execute(text("UPDATE cdp.persons SET person_segment_id = NULL, person_segment_name = NULL, person_segment_slug = NULL"))

    segments = conn.execute(text("SELECT id, slug, name, segment_type, criteria FROM cdp.person_segments WHERE slug != 'general_network'")).fetchall()

    for seg in segments:
        seg_id, slug, seg_name, seg_type, criteria = seg[0], seg[1], seg[2], seg[3], seg[4] or {}
        if seg_type != "dynamic":
            continue

        rule_name = criteria.get("rule") if isinstance(criteria, dict) else None
        if not rule_name or rule_name not in PERSON_SEGMENT_RULES:
            continue

        sql_query = PERSON_SEGMENT_RULES[rule_name]
        matching_person_rows = conn.execute(text(sql_query)).fetchall()
        matching_person_ids = [row[0] for row in matching_person_rows]

        if matching_person_ids:
            conn.execute(
                text("""
                    UPDATE cdp.persons 
                    SET person_segment_id = :seg_id,
                        person_segment_name = :seg_name,
                        person_segment_slug = :seg_slug
                    WHERE id IN :person_ids
                """),
                {"seg_id": seg_id, "seg_name": seg_name, "seg_slug": slug, "person_ids": tuple(matching_person_ids)}
            )

        results[slug] = len(matching_person_ids)

    # 2. Fallback unclassified contacts to 'general_network' (No NULLs)
    gen_seg = conn.execute(text("SELECT id, slug, name FROM cdp.person_segments WHERE slug = 'general_network'")).fetchone()
    if gen_seg:
        unassigned = conn.execute(text("""
            UPDATE cdp.persons 
            SET person_segment_id = :seg_id,
                person_segment_name = :seg_name,
                person_segment_slug = :seg_slug
            WHERE person_segment_id IS NULL
        """), {"seg_id": gen_seg[0], "seg_name": gen_seg[2], "seg_slug": gen_seg[1]}).rowcount
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


def evaluate_lead_segments(conn) -> Dict[str, int]:
    """Evaluates dynamic lead segments and updates lead_segment_id, lead_segment_name, lead_segment_slug on cdp.leads."""
    results = {}
    segments = conn.execute(text("SELECT id, slug, name, segment_type, criteria FROM cdp.lead_segments")).fetchall()

    for seg in segments:
        seg_id, slug, seg_name, seg_type, criteria = seg[0], seg[1], seg[2], seg[3], seg[4] or {}
        if seg_type != "dynamic":
            continue

        rule_name = criteria.get("rule") if isinstance(criteria, dict) else None
        if not rule_name or rule_name not in LEAD_SEGMENT_RULES:
            continue

        sql_query = LEAD_SEGMENT_RULES[rule_name]
        matching_lead_rows = conn.execute(text(sql_query)).fetchall()
        matching_lead_ids = [row[0] for row in matching_lead_rows]

        if matching_lead_ids:
            conn.execute(
                text("""
                    UPDATE cdp.leads 
                    SET lead_segment_id = :seg_id,
                        lead_segment_name = :seg_name,
                        lead_segment_slug = :seg_slug
                    WHERE id IN :lead_ids
                """),
                {"seg_id": seg_id, "seg_name": seg_name, "seg_slug": slug, "lead_ids": tuple(matching_lead_ids)}
            )

        results[slug] = len(matching_lead_ids)

    return results


def evaluate_segments() -> Dict[str, Any]:
    """Evaluates all Person and Lead dynamic segments and engagement temperatures in CDP database."""
    logger.info("Starting CDP segment and engagement temperature evaluation for Persons and Leads...")
    cdp_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/cdp", env_var="DATABASE_URL")

    with cdp_engine.begin() as conn:
        ensure_seed_segments(conn)
        person_results = evaluate_person_segments(conn)
        temperature_results = evaluate_engagement_temperature(conn)
        lead_results = evaluate_lead_segments(conn)

    logger.info(f"CDP segment evaluation completed. Persons: {person_results}, Temperature: {temperature_results}, Leads: {lead_results}")
    return {
        "status": "success",
        "person_segments": person_results,
        "engagement_temperatures": temperature_results,
        "lead_segments": lead_results
    }


if __name__ == "__main__":
    summary = evaluate_segments()
    print(json.dumps(summary, indent=2))
