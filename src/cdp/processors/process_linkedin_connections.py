import os
import sys
import re
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

logger = setup_logging("cdp-linkedin-processor")


LEGAL_SUFFIX_REGEX = re.compile(
    r'\b(gmbh\s*&\s*co\.?\s*kg|gmbh|co\.?\s*kg|se|inc\.?|corp\.?|corporation|llc|ltd\.?|limited|ag|pty\s*ltd\.?|s\.?a\.?|plc|b\.?v\.?)\b',
    re.IGNORECASE
)


def clean_company_name(raw_name: str) -> str:
    if not raw_name:
        return ""
    name = raw_name.strip()
    # Strip legal entity suffixes
    name = LEGAL_SUFFIX_REGEX.sub('', name)
    # Strip trailing punctuation, spaces, dashes
    name = re.sub(r'[\s,\.-]+$', '', name).strip()
    return name or raw_name.strip()


def generate_company_domain(company_name: str) -> str:
    cleaned_name = clean_company_name(company_name)
    if not cleaned_name:
        return ""
    cleaned = re.sub(r'[^a-zA-Z0-9]+', '', cleaned_name).lower()
    return f"{cleaned}.com" if cleaned else ""


def process_linkedin_connections():
    """
    Reads unprocessed LinkedIn connections from s_linkedin.connections (processed = 0) in jager DB,
    normalizes profiles into cdp.persons, extracts company accounts into cdp.companies,
    and maps relationships in cdp.person_company_relationships in cdp DB.
    """
    logger.info("Starting processing of LinkedIn connections into cdp.persons and cdp.companies...")
    jager_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/jager", env_var="JAGER_DATABASE_URL")
    cdp_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/cdp", env_var="DATABASE_URL")

    processed_count = 0
    accounts_processed = 0
    relationships_processed = 0

    with jager_engine.begin() as jager_conn:
        rows = jager_conn.execute(
            text("""
                SELECT id, first_name, last_name, profile_url, email_address, company, position, connected_at
                FROM s_linkedin.connections
                WHERE processed = 0 OR processed IS NULL
            """)
        ).mappings().all()

        if not rows:
            logger.info("No unprocessed LinkedIn connections found.")
            return {"status": "success", "processed_count": 0, "accounts_processed": 0, "persons_resolved": 0}

        logger.info(f"Fetched {len(rows)} unprocessed LinkedIn connections.")

        with cdp_engine.begin() as cdp_conn:
            for row in rows:
                conn_id = str(row["id"])
                first_name = (row.get("first_name") or "").strip() or None
                last_name = (row.get("last_name") or "").strip() or None
                profile_url = (row.get("profile_url") or "").strip() or None
                company = (row.get("company") or "").strip() or None
                position = (row.get("position") or "").strip() or None

                raw_email = row.get("email_address")
                email = raw_email.strip() if raw_email else None
                if email and "@linkedin.user" in email:
                    email = None

                # Skip blank records with no identifying person fields
                if not first_name and not last_name and not email and not profile_url:
                    jager_conn.execute(
                        text("UPDATE s_linkedin.connections SET processed = 1 WHERE id = :conn_id"),
                        {"conn_id": conn_id}
                    )
                    continue

                # 1. Upsert into cdp.persons_linkedins intake table
                cdp_conn.execute(
                    text("""
                        INSERT INTO cdp.persons_linkedins (
                            connection_id, first_name, last_name, profile_url, email_address,
                            company, position, connected_at, raw_payload, intake_at, updated_at
                        )
                        VALUES (
                            :connection_id, :first_name, :last_name, :profile_url, :email,
                            :company, :position, :connected_at, :raw_payload, NOW(), NOW()
                        )
                        ON CONFLICT (connection_id) DO UPDATE SET
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            profile_url = EXCLUDED.profile_url,
                            email_address = EXCLUDED.email_address,
                            company = EXCLUDED.company,
                            position = EXCLUDED.position,
                            connected_at = EXCLUDED.connected_at,
                            raw_payload = EXCLUDED.raw_payload,
                            updated_at = NOW()
                    """),
                    {
                        "connection_id": conn_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "profile_url": profile_url,
                        "email": email,
                        "company": company,
                        "position": position,
                        "connected_at": row.get("connected_at"),
                        "raw_payload": json.dumps(dict(row), default=str)
                    }
                )

                # 2. Process company into cdp.companies if present
                company_id = None
                if company:
                    company_clean = company.strip()
                    domain = generate_company_domain(company_clean)
                    account_res = cdp_conn.execute(
                        text("""
                            WITH existing_account AS (
                              SELECT id FROM cdp.companies
                              WHERE company_name = :company
                              LIMIT 1
                            ),
                            upserted_account AS (
                              INSERT INTO cdp.companies (company_name, domain, status, created_at, updated_at)
                              SELECT
                                :company,
                                CASE WHEN EXISTS (SELECT 1 FROM cdp.companies WHERE domain = :domain) THEN NULL ELSE :domain END,
                                'prospect',
                                NOW(),
                                NOW()
                              WHERE NOT EXISTS (SELECT 1 FROM existing_account)
                              RETURNING id
                            ),
                            updated_account AS (
                              UPDATE cdp.companies
                              SET
                                updated_at = NOW()
                              WHERE id = (SELECT id FROM existing_account)
                              RETURNING id
                            )
                            SELECT id FROM upserted_account UNION ALL SELECT id FROM updated_account;
                        """),
                        {"company": company_clean, "domain": domain}
                    )
                    company_id = account_res.scalar()
                    if company_id:
                        accounts_processed += 1

                # 3. Mark s_linkedin.connections row as processed in jager DB
                jager_conn.execute(
                    text("UPDATE s_linkedin.connections SET processed = 1 WHERE id = :conn_id"),
                    {"conn_id": conn_id}
                )
                processed_count += 1

        # 4. Trigger unified entity resolution into cdp.persons
        from processors.entity_resolution import resolve_persons
        with cdp_engine.begin() as cdp_conn:
            persons_resolved = resolve_persons(cdp_conn)

    logger.info(
        f"CDP processing complete: {processed_count} connections ingested into cdp.persons_linkedins, "
        f"{accounts_processed} accounts processed, {persons_resolved} master persons resolved."
    )
    return {
        "status": "success",
        "processed_count": processed_count,
        "accounts_processed": accounts_processed,
        "persons_resolved": persons_resolved
    }


if __name__ == "__main__":
    process_linkedin_connections()

