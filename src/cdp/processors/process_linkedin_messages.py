import os
import sys
import json
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
                ) as latest_snippet
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
                "counterparty_url": profile_url
            })

            description_text = f"LinkedIn conversation ({msg_count} msgs). Latest: {snippet}" if snippet else f"LinkedIn conversation ({msg_count} msgs)."

            cdp_conn.execute(
                text("""
                    INSERT INTO cdp.leads (
                        person_id, full_name, description, status, source, raw_payload, intake_at, updated_at
                    )
                    VALUES (
                        :person_id, :full_name, :description, 'prospect', 'linkedin:message', CAST(:raw_payload AS jsonb), :intake_at, NOW()
                    );
                """),
                {
                    "person_id": person_id,
                    "full_name": full_name,
                    "description": description_text,
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
