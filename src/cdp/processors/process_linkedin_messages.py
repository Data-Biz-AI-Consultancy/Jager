import os
import sys
import json
import uuid
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


def analyze_convo_nlp(convo_text: str):
    """
    Simple heuristic NLP rule engine to detect intent, signal strength, and opportunity type from conversation history.
    """
    if not convo_text:
        return {
            "intent": "general_inquiry",
            "signal_strength": "low",
            "opportunity_type": "unknown"
        }

    text_lower = convo_text.lower()

    # 1. Opportunity Type Detection
    opp_types = []
    if any(k in text_lower for k in ["freelance", "freelancer", "contract", "contractor", "interim", "project-based"]):
        opp_types.append("freelance_contract")
    if any(k in text_lower for k in ["consulting", "advisory", "adviser", "consultant", "services", "access your service"]):
        opp_types.append("consulting_advisory")
    if any(k in text_lower for k in ["full time", "full-time", "permanent", "head of", "director", "lead", "hiring", "recruit", "talent partner"]):
        opp_types.append("full_time_job")

    opportunity_type = "/".join(opp_types) if opp_types else "general_inquiry"

    # 2. Intent Detection
    if any(k in text_lower for k in ["access your service", "hire you for", "consulting rate", "hourly rate for consulting", "data stack audit", "build our data", "project proposal", "freelance proposal"]):
        intent = "inbound_service_request"
    elif any(k in text_lower for k in ["recruiting", "recruiter", "talent acquisition", "talent partner", "open for a role", "job opportunity", "hiring"]):
        intent = "recruitment_inbound"
    elif any(k in text_lower for k in ["consulting", "advisory", "project", "freelance", "contract"]):
        intent = "business_collaboration"
    else:
        intent = "networking_inquiry"

    # 3. Signal Strength Detection
    if any(k in text_lower for k in ["access your service", "pricing", "rate", "quote", "proposal", "call next week", "call this week", "phone number"]):
        signal_strength = "high"
    elif any(k in text_lower for k in ["opportunity", "hiring", "role", "project", "freelance", "contract"]):
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
        # Group s_linkedin.messages by conversation_id, filtering for business opportunity signals
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
            HAVING BOOL_OR(
                content ILIKE '%access%service%'
                OR content ILIKE '%how%access%'
                OR content ILIKE '%your service%'
                OR content ILIKE '%consulting%'
                OR content ILIKE '%advisory%'
                OR content ILIKE '%pricing%'
                OR content ILIKE '%rate%'
                OR content ILIKE '%quote%'
                OR content ILIKE '%proposal%'
                OR content ILIKE '%freelance%'
                OR content ILIKE '%contractor%'
                OR content ILIKE '%opportunity%'
                OR content ILIKE '%hire%you%'
                OR content ILIKE '%work together%'
            )
        """)

        conv_rows = jager_conn.execute(conversations_query).mappings().all()
        logger.info(f"Found {len(conv_rows)} distinct conversations in s_linkedin.messages.")

        for conv in conv_rows:
            conv_id = conv["conversation_id"]
            full_name = (conv["counterparty_name"] or "Unknown Contact").strip()
            profile_url = conv["counterparty_url"]
            first_sent = conv["first_sent_at"]
            last_sent = conv["last_sent_at"]
            snippet = conv["latest_snippet"] or ""
            convo_transcript = conv["convo_transcript"] or ""
            msg_count = conv["msg_count"]

            parts = full_name.split(maxsplit=1)
            fname = parts[0]
            lname = parts[1] if len(parts) > 1 else ""

            # 1. Match or Create Person in cdp.persons
            person_id = None
            if full_name and full_name != "Unknown Contact":
                person_res = cdp_conn.execute(
                    text("""
                        SELECT id FROM cdp.persons 
                        WHERE (linkedin_url IS NOT NULL AND linkedin_url = :profile_url)
                           OR (first_name = :fname AND last_name = :lname)
                        LIMIT 1
                    """),
                    {"profile_url": profile_url, "fname": fname, "lname": lname}
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

            # 2. Insert Lead grouped by conversation_id into cdp.leads
            raw_payload = json.dumps({
                "conversation_id": conv_id,
                "msg_count": msg_count,
                "first_sent_at": str(first_sent),
                "last_sent_at": str(last_sent),
                "latest_snippet": snippet,
                "convo_transcript": convo_transcript,
                "counterparty_url": profile_url
            })

            # Build a structured summary of the conversation history for description column
            if convo_transcript:
                first_date_str = str(first_sent.date()) if first_sent else "N/A"
                last_date_str = str(last_sent.date()) if last_sent else "N/A"
                
                # Take up to the 3 most key messages (first message & recent messages)
                lines = [line.strip() for line in convo_transcript.split('\n') if line.strip()]
                if len(lines) <= 4:
                    summary_excerpt = "\n".join(lines)
                else:
                    summary_excerpt = f"{lines[0]}\n...\n" + "\n".join(lines[-3:])

                description_text = (
                    f"LinkedIn Conversation Summary ({msg_count} messages, {first_date_str} to {last_date_str}):\n"
                    f"{summary_excerpt}"
                )
            else:
                description_text = f"LinkedIn Conversation with {full_name} ({msg_count} messages)."

            summary_text = description_text
            nlp_result = analyze_convo_nlp(convo_transcript)

            # Insert/Update Lead in cdp.leads_linkedin
            cdp_conn.execute(
                text("""
                    INSERT INTO cdp.leads_linkedin (
                        conversation_id, person_id, full_name, description, message_count, summary, convo_history, intent, signal_strength, opportunity_type, status, raw_payload, intake_at, updated_at
                    )
                    VALUES (
                        :conv_id, :person_id, :full_name, :description, :message_count, :summary, :convo_history, :intent, :signal_strength, :opportunity_type, 'prospect', CAST(:raw_payload AS jsonb), :intake_at, NOW()
                    )
                    ON CONFLICT (conversation_id) DO UPDATE SET
                        description = EXCLUDED.description,
                        message_count = EXCLUDED.message_count,
                        summary = EXCLUDED.summary,
                        convo_history = EXCLUDED.convo_history,
                        intent = EXCLUDED.intent,
                        signal_strength = EXCLUDED.signal_strength,
                        opportunity_type = EXCLUDED.opportunity_type,
                        raw_payload = EXCLUDED.raw_payload,
                        updated_at = NOW();
                """),
                {
                    "conv_id": conv_id,
                    "person_id": person_id,
                    "full_name": full_name,
                    "description": description_text,
                    "message_count": msg_count,
                    "summary": summary_text,
                    "convo_history": convo_transcript,
                    "intent": nlp_result["intent"],
                    "signal_strength": nlp_result["signal_strength"],
                    "opportunity_type": nlp_result["opportunity_type"],
                    "intake_at": last_sent or first_sent,
                    "raw_payload": raw_payload
                }
            )

            # Insert/Update Lead in aggregated cdp.leads table
            cdp_conn.execute(
                text("""
                    INSERT INTO cdp.leads (
                        id, person_id, full_name, description, message_count, summary, convo_history, intent, signal_strength, opportunity_type, status, source, raw_payload, intake_at, updated_at
                    )
                    VALUES (
                        :conv_id, :person_id, :full_name, :description, :message_count, :summary, :convo_history, :intent, :signal_strength, :opportunity_type, 'prospect', 'Linkedin', CAST(:raw_payload AS jsonb), :intake_at, NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        description = EXCLUDED.description,
                        message_count = EXCLUDED.message_count,
                        summary = EXCLUDED.summary,
                        convo_history = EXCLUDED.convo_history,
                        intent = EXCLUDED.intent,
                        signal_strength = EXCLUDED.signal_strength,
                        opportunity_type = EXCLUDED.opportunity_type,
                        source = EXCLUDED.source,
                        raw_payload = EXCLUDED.raw_payload,
                        updated_at = NOW();
                """),
                {
                    "conv_id": conv_id,
                    "person_id": person_id,
                    "full_name": full_name,
                    "description": description_text,
                    "message_count": msg_count,
                    "summary": summary_text,
                    "convo_history": convo_transcript,
                    "intent": nlp_result["intent"],
                    "signal_strength": nlp_result["signal_strength"],
                    "opportunity_type": nlp_result["opportunity_type"],
                    "intake_at": last_sent or first_sent,
                    "raw_payload": raw_payload
                }
            )
            leads_processed += 1

    logger.info(
        f"LinkedIn messages processing complete: {leads_processed} leads created across "
        f"{len(conv_rows)} conversations ({persons_created} new persons created)."
    )

    return {
        "status": "success",
        "leads_processed": leads_processed,
        "persons_created": persons_created
    }


if __name__ == "__main__":
    process_linkedin_messages()
