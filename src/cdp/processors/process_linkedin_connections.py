import os
from sqlalchemy import text
try:
    from utils import setup_logging, get_db_engine
except ImportError:
    from src.cdp.utils import setup_logging, get_db_engine

logger = setup_logging("cdp-linkedin-processor")


def process_linkedin_connections():
    """
    Reads unprocessed LinkedIn connections from s_linkedin.connections (processed = 0),
    normalizes profiles, and upserts them into cdp.persons cleanly.
    """
    logger.info("Starting processing of unprocessed LinkedIn connections into cdp.persons...")
    engine = get_db_engine()

    processed_count = 0
    with engine.begin() as conn:
        # Fetch unprocessed connection records
        rows = conn.execute(
            text("""
                SELECT id, first_name, last_name, profile_url, email_address, company, position, connected_at
                FROM s_linkedin.connections
                WHERE processed = 0
            """)
        ).mappings().all()

        if not rows:
            logger.info("No unprocessed LinkedIn connections found.")
            return {"status": "success", "processed_count": 0}

        for row in rows:
            conn_id = row.get("id")
            first_name = (row.get("first_name") or "").strip() or None
            last_name = (row.get("last_name") or "").strip() or None
            profile_url = (row.get("profile_url") or "").strip() or None

            raw_email = row.get("email_address")
            email = raw_email.strip() if raw_email else None
            if email and "@linkedin.user" in email:
                email = None

            # Upsert into cdp.persons matching by linkedin_url or primary_email
            conn.execute(
                text("""
                    WITH existing_person AS (
                      SELECT id FROM cdp.persons
                      WHERE (linkedin_url IS NOT NULL AND linkedin_url = :profile_url)
                         OR (primary_email IS NOT NULL AND primary_email = :email)
                      LIMIT 1
                    ),
                    upserted_person AS (
                      INSERT INTO cdp.persons (first_name, last_name, primary_email, linkedin_url, status, created_at, updated_at)
                      SELECT :first_name, :last_name, :email, :profile_url, 'active', NOW(), NOW()
                      WHERE NOT EXISTS (SELECT 1 FROM existing_person)
                      RETURNING id
                    )
                    UPDATE cdp.persons
                    SET
                      first_name = COALESCE(:first_name, cdp.persons.first_name),
                      last_name = COALESCE(:last_name, cdp.persons.last_name),
                      primary_email = COALESCE(:email, cdp.persons.primary_email),
                      linkedin_url = COALESCE(:profile_url, cdp.persons.linkedin_url),
                      updated_at = NOW()
                    WHERE id = (SELECT id FROM existing_person);

                    UPDATE s_linkedin.connections
                    SET processed = 1
                    WHERE id = :conn_id;
                """),
                {
                    "conn_id": conn_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "profile_url": profile_url
                }
            )
            processed_count += 1

    logger.info(f"Successfully processed {processed_count} LinkedIn connections into cdp.persons.")
    return {"status": "success", "processed_count": processed_count}


if __name__ == "__main__":
    process_linkedin_connections()
