import os
import sys
import re
from typing import Dict, Any
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

logger = setup_logging("cdp-linkedin-messages-processor")


def detect_message_metadata(convo_transcript: str) -> Dict[str, Any]:
    """
    Analyzes conversation transcript text to extract opportunity_type, intent, and signal_strength.
    """
    text_lower = convo_transcript.lower() if convo_transcript else ""

    # 1. Opportunity Type Detection
    opp_types = []
    if any(k in text_lower for k in ["consulting", "advisory", "fractional", "audit", "data stack", "snowflake", "data engineering", "pipeline"]):
        opp_types.append("consulting_project")
    if any(k in text_lower for k in ["freelance", "contract", "interim", "subcontract"]):
        opp_types.append("freelance_contract")
    if any(k in text_lower for k in ["full time", "full-time", "permanent", "head of", "director", "lead", "hiring", "recruit", "talent partner"]):
        opp_types.append("full_time_job")

    opportunity_type = "/".join(opp_types) if opp_types else "general_inquiry"

    # 2. Intent Detection
    if any(k in text_lower for k in [
        "access your service", "hire you for", "consulting rate", "hourly rate", "data stack audit", 
        "build our data", "project proposal", "freelance proposal", "advice regarding data", 
        "data and analytics", "engineering firm", "snowflake", "pipeline", "audit", "need some advice",
        "service inquiry", "consulting project", "exploring ai", "databizaitech", "my new business",
        "consultancy page", "your site", "security & compliance", "gdpr"
    ]):
        intent = "inbound_service_request"
    elif any(k in text_lower for k in ["recruiting", "recruiter", "talent acquisition", "talent partner", "open for a role", "job opportunity", "hiring"]):
        intent = "recruitment_inbound"
    elif any(k in text_lower for k in ["consulting", "advisory", "project", "freelance", "contract", "work together", "call", "meeting"]):
        intent = "business_collaboration"
    else:
        intent = "networking_inquiry"

    # 3. Signal Strength Detection
    if any(k in text_lower for k in ["access your service", "pricing", "rate", "quote", "proposal", "call next week", "call this week", "phone number", "calendar invite", "google meet"]):
        signal_strength = "high"
    elif any(k in text_lower for k in ["opportunity", "hiring", "role", "project", "freelance", "contract", "advice"]):
        signal_strength = "medium"
    else:
        signal_strength = "low"

    return {
        "intent": intent,
        "signal_strength": signal_strength,
        "opportunity_type": opportunity_type
    }


def process_linkedin_messages():
    """
    Groups s_linkedin.messages from jager DB by conversation_id, matches counterpart contacts
    to cdp.persons (or creates them), and inserts grouped lead records into cdp.leads (cdp DB).
    """
    logger.info("Starting processing of s_linkedin.messages into cdp.leads...")
    jager_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/jager", env_var="JAGER_DATABASE_URL")
    cdp_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/cdp", env_var="DATABASE_URL")

    leads_processed = 0
    persons_created = 0

    with jager_engine.begin() as jager_conn, cdp_engine.begin() as cdp_conn:
        # Group s_linkedin.messages by conversation_id
        conversations_query = text("""
            SELECT 
                conversation_id,
                COUNT(*) as msg_count,
                MIN(sent_at) as first_sent_at,
                MAX(sent_at) as last_sent_at,
                -- Identify the counterparty name (prefer names that are not Jimmy Pang)
                MODE() WITHIN GROUP (
                    ORDER BY CASE 
                        WHEN sender_name IS NOT NULL AND sender_name != 'Jimmy Pang' THEN sender_name
                        WHEN recipient_name IS NOT NULL AND recipient_name != 'Jimmy Pang' THEN recipient_name
                        ELSE COALESCE(sender_name, recipient_name)
                    END
                ) as counterparty_name,
                -- Identify counterparty profile URL
                MODE() WITHIN GROUP (
                    ORDER BY CASE 
                        WHEN sender_name != 'Jimmy Pang' AND sender_profile_url IS NOT NULL THEN sender_profile_url
                        WHEN recipient_name != 'Jimmy Pang' AND recipient_profile_urls IS NOT NULL THEN recipient_profile_urls
                        ELSE COALESCE(sender_profile_url, recipient_profile_urls)
                    END
                ) as counterparty_url,
                -- Collect last message subject/content snippet
                (
                    SELECT COALESCE(NULLIF(subject, ''), LEFT(content, 200))
                    FROM s_linkedin.messages m2 
                    WHERE m2.conversation_id = m.conversation_id 
                    ORDER BY sent_at DESC LIMIT 1
                ) as latest_snippet,
                -- Concatenate full conversation transcript for downstream NLP scanning
                string_agg(
                    COALESCE(sender_name, 'Unknown') || ': ' || COALESCE(content, ''), 
                    E'\n' 
                    ORDER BY sent_at ASC
                ) as convo_transcript
            FROM s_linkedin.messages m
            GROUP BY conversation_id
        """)

        conv_rows = jager_conn.execute(conversations_query).mappings().all()
        logger.info(f"Found {len(conv_rows)} distinct conversations in s_linkedin.messages.")

        for conv in conv_rows:
            conv_id = conv["conversation_id"]
            raw_name = conv["counterparty_name"] or "Unknown Contact"
            full_name = " ".join(raw_name.split())
            profile_url = conv["counterparty_url"]
            transcript = conv["convo_transcript"] or ""
            latest_snippet = conv["latest_snippet"] or ""
            msg_count = conv["msg_count"]

            parts = full_name.split(maxsplit=1)
            fname = parts[0] if parts else ""
            lname = parts[1] if len(parts) > 1 else ""

            # 1. Match or Create Person in cdp.persons
            person_id = None
            if full_name and full_name != "Unknown Contact":
                # Normalize handle for profile URL matching
                clean_url = profile_url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/") if profile_url else ""

                person_res = cdp_conn.execute(
                    text("""
                        SELECT id FROM cdp.persons 
                        WHERE (linkedin_url IS NOT NULL AND (linkedin_url = :profile_url OR linkedin_url ILIKE '%' || :clean_url || '%'))
                           OR (LOWER(TRIM(first_name)) = LOWER(TRIM(:fname)) AND LOWER(TRIM(last_name)) = LOWER(TRIM(:lname)))
                        LIMIT 1
                    """),
                    {"profile_url": profile_url, "clean_url": clean_url, "fname": fname, "lname": lname}
                ).scalar()

                if person_res:
                    person_id = person_res
                else:
                    ins_person = cdp_conn.execute(
                        text("""
                            INSERT INTO cdp.persons (first_name, last_name, linkedin_url, created_at, updated_at)
                            VALUES (:fname, :lname, :profile_url, NOW(), NOW())
                            RETURNING id;
                        """),
                        {
                            "fname": fname,
                            "lname": lname,
                            "profile_url": profile_url
                        }
                    )
                    person_id = ins_person.scalar()
                    persons_created += 1

            # 2. Detect Metadata & Signals
            meta = detect_message_metadata(transcript)
            intent = meta["intent"]
            signal_strength = meta["signal_strength"]
            opportunity_type = meta["opportunity_type"]
            summary_text = f"LinkedIn Conversation Summary ({msg_count} messages, {conv['first_sent_at'].strftime('%Y-%m-%d') if conv['first_sent_at'] else ''} to {conv['last_sent_at'].strftime('%Y-%m-%d') if conv['last_sent_at'] else ''}):\n{transcript[:400]}"

            # 3. Upsert into cdp.leads_linkedin
            cdp_conn.execute(
                text("""
                    INSERT INTO cdp.leads_linkedin (
                        conversation_id, person_id, full_name, description, message_count,
                        summary, convo_history, intent, signal_strength, opportunity_type, status,
                        intake_at, updated_at
                    ) VALUES (
                        :conv_id, :person_id, :full_name, :description, :msg_count,
                        :summary, :transcript, :intent, :signal_strength, :opportunity_type, 'prospect',
                        NOW(), NOW()
                    )
                    ON CONFLICT (conversation_id) DO UPDATE SET
                        person_id = EXCLUDED.person_id,
                        full_name = EXCLUDED.full_name,
                        message_count = EXCLUDED.message_count,
                        summary = EXCLUDED.summary,
                        convo_history = EXCLUDED.convo_history,
                        intent = EXCLUDED.intent,
                        signal_strength = EXCLUDED.signal_strength,
                        opportunity_type = EXCLUDED.opportunity_type,
                        updated_at = NOW();
                """),
                {
                    "conv_id": conv_id,
                    "person_id": person_id,
                    "full_name": full_name,
                    "description": f"LinkedIn conversation with {full_name} ({msg_count} messages)",
                    "msg_count": msg_count,
                    "summary": summary_text,
                    "transcript": transcript,
                    "intent": intent,
                    "signal_strength": signal_strength,
                    "opportunity_type": opportunity_type
                }
            )

            # 4. Upsert into Consolidated cdp.leads Table
            cdp_conn.execute(
                text("""
                    INSERT INTO cdp.leads (
                        id, person_id, source, summary, intent, status, signal_strength, intake_at, updated_at
                    ) VALUES (
                        :lead_id, :person_id, 'Linkedin', :summary, :intent, 'prospect', :signal_strength, NOW(), NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        person_id = EXCLUDED.person_id,
                        summary = EXCLUDED.summary,
                        intent = EXCLUDED.intent,
                        signal_strength = EXCLUDED.signal_strength,
                        updated_at = NOW();
                """),
                {
                    "lead_id": f"2-{conv_id}_100",
                    "person_id": person_id,
                    "summary": summary_text,
                    "intent": intent,
                    "signal_strength": signal_strength
                }
            )

            leads_processed += 1

    logger.info(f"LinkedIn messages processing complete: {leads_processed} leads created across {len(conv_rows)} conversations ({persons_created} new persons created).")
    return {
        "status": "success",
        "conversations_found": len(conv_rows),
        "leads_processed": leads_processed,
        "persons_created": persons_created
    }


if __name__ == "__main__":
    res = process_linkedin_messages()
    print(res)
