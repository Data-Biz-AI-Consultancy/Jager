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
    "high_engagement_unconverted": """
        SELECT p.id FROM cdp.persons p
        LEFT JOIN cdp.leads l ON p.id = l.person_id AND l.status IN ('negotiating', 'offer_accepted', 'contract_signed', 'engaging', 'completed')
        WHERE (p.in_substack_subscriber_export = TRUE OR p.in_linkedin_connections = TRUE OR EXISTS (SELECT 1 FROM cdp.engagements e WHERE e.person_id = p.id))
          AND l.id IS NULL
    """,
    "cross_channel_contacts": """
        SELECT p.id FROM cdp.persons p
        WHERE p.in_linkedin_connections = TRUE AND p.in_substack_subscriber_export = TRUE
    """,
    "decision_makers": """
        SELECT DISTINCT p.id FROM cdp.persons p
        LEFT JOIN cdp.person_account_relationships r ON p.id = r.person_id
        WHERE r.id IS NOT NULL
           OR p.id IN (
               SELECT person_id FROM cdp.persons_linkedins 
               WHERE LOWER(COALESCE(position, '')) ~ '(ceo|cto|cfo|coo|vp|vice president|director|head|founder|owner|partner|chief)'
           )
    """,
    "inactive_contacts": """
        SELECT p.id FROM cdp.persons p
        LEFT JOIN cdp.engagements e ON p.id = e.person_id AND e.occurred_at >= NOW() - INTERVAL '90 days'
        LEFT JOIN cdp.activities a ON p.id = a.person_id AND a.activity_date >= NOW() - INTERVAL '90 days'
        GROUP BY p.id
        HAVING COUNT(e.id) = 0 AND COUNT(a.id) = 0
    """,
    "former_clients_nurture": """
        SELECT DISTINCT p.id FROM cdp.persons p
        JOIN cdp.leads l ON p.id = l.person_id
        WHERE l.status = 'completed'
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
        ("high_engagement_unconverted", "High Engagement Unconverted", "Active contacts across channels with no active lead", "dynamic", {"rule": "high_engagement_unconverted"}),
        ("cross_channel_contacts", "Cross-Channel Contacts", "Contacts present in both LinkedIn connections and Substack subscribers", "dynamic", {"rule": "cross_channel_contacts"}),
        ("decision_makers", "Decision Makers", "Contacts mapped to accounts or holding executive titles", "dynamic", {"rule": "decision_makers"}),
        ("inactive_contacts", "Inactive Contacts", "Contacts with zero activity or engagement in last 90 days", "dynamic", {"rule": "inactive_contacts"}),
        ("former_clients_nurture", "Former Clients Nurture", "Contacts associated with past completed engagements", "dynamic", {"rule": "former_clients_nurture"}),
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
    """Evaluates dynamic person segments and updates person_segment_id on cdp.persons."""
    results = {}
    segments = conn.execute(text("SELECT id, slug, segment_type, criteria FROM cdp.person_segments")).fetchall()

    for seg in segments:
        seg_id, slug, seg_type, criteria = seg[0], seg[1], seg[2], seg[3] or {}
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
                text("UPDATE cdp.persons SET person_segment_id = :seg_id WHERE id IN :person_ids"),
                {"seg_id": seg_id, "person_ids": tuple(matching_person_ids)}
            )

        results[slug] = len(matching_person_ids)

    return results


def evaluate_lead_segments(conn) -> Dict[str, int]:
    """Evaluates dynamic lead segments and updates lead_segment_id on cdp.leads."""
    results = {}
    segments = conn.execute(text("SELECT id, slug, segment_type, criteria FROM cdp.lead_segments")).fetchall()

    for seg in segments:
        seg_id, slug, seg_type, criteria = seg[0], seg[1], seg[2], seg[3] or {}
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
                text("UPDATE cdp.leads SET lead_segment_id = :seg_id WHERE id IN :lead_ids"),
                {"seg_id": seg_id, "lead_ids": tuple(matching_lead_ids)}
            )

        results[slug] = len(matching_lead_ids)

    return results


def evaluate_segments() -> Dict[str, Any]:
    """Evaluates all Person and Lead dynamic segments in CDP database."""
    logger.info("Starting CDP segment evaluation for Persons and Leads...")
    cdp_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/cdp", env_var="DATABASE_URL")

    with cdp_engine.begin() as conn:
        ensure_seed_segments(conn)
        person_results = evaluate_person_segments(conn)
        lead_results = evaluate_lead_segments(conn)

    logger.info(f"CDP segment evaluation completed. Persons: {person_results}, Leads: {lead_results}")
    return {
        "status": "success",
        "person_segments": person_results,
        "lead_segments": lead_results
    }


if __name__ == "__main__":
    summary = evaluate_segments()
    print(json.dumps(summary, indent=2))
