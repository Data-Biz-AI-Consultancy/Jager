import os
import sys
import re
from sqlalchemy import text

cdp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
for path in (cdp_dir, root_dir):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from utils import setup_logging, get_db_engine
except ImportError:
    from src.cdp.utils import setup_logging, get_db_engine

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
    Reads unprocessed LinkedIn connections from s_linkedin.connections (processed = 0),
    normalizes profiles into cdp.persons, extracts company accounts into cdp.client_accounts,
    and maps relationships in cdp.person_account_relationships.
    """
    logger.info("Starting processing of LinkedIn connections into cdp.persons and cdp.client_accounts...")
    engine = get_db_engine()

    processed_count = 0
    accounts_processed = 0
    relationships_processed = 0

    with engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT id, first_name, last_name, profile_url, email_address, company, position, connected_at
                FROM s_linkedin.connections
                WHERE processed = 0
            """)
        ).mappings().all()

        if not rows:
            logger.info("No unprocessed LinkedIn connections found.")
            return {
                "status": "success",
                "processed_count": 0,
                "accounts_processed": 0,
                "relationships_processed": 0
            }

        for row in rows:
            conn_id = row.get("id")
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
                conn.execute(
                    text("UPDATE s_linkedin.connections SET processed = 1 WHERE id = :conn_id"),
                    {"conn_id": conn_id}
                )
                continue

            # 1. Upsert person into cdp.persons
            person_res = conn.execute(
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
                    ),
                    updated_person AS (
                      UPDATE cdp.persons
                      SET
                        first_name = COALESCE(:first_name, cdp.persons.first_name),
                        last_name = COALESCE(:last_name, cdp.persons.last_name),
                        primary_email = COALESCE(:email, cdp.persons.primary_email),
                        linkedin_url = COALESCE(:profile_url, cdp.persons.linkedin_url),
                        updated_at = NOW()
                      WHERE id = (SELECT id FROM existing_person)
                      RETURNING id
                    )
                    SELECT id FROM upserted_person UNION ALL SELECT id FROM updated_person;
                """),
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "profile_url": profile_url
                }
            )
            person_id = person_res.scalar()

            # 2. Process company into cdp.client_accounts if present
            client_account_id = None
            if company:
                company_clean = company.strip()
                domain = generate_company_domain(company_clean)
                account_res = conn.execute(
                    text("""
                        WITH existing_account AS (
                          SELECT id FROM cdp.client_accounts
                          WHERE company_name = :company
                          LIMIT 1
                        ),
                        upserted_account AS (
                          INSERT INTO cdp.client_accounts (company_name, domain, status, created_at, updated_at)
                          SELECT
                            :company,
                            CASE WHEN EXISTS (SELECT 1 FROM cdp.client_accounts WHERE domain = :domain) THEN NULL ELSE :domain END,
                            'prospect',
                            NOW(),
                            NOW()
                          WHERE NOT EXISTS (SELECT 1 FROM existing_account)
                          RETURNING id
                        ),
                        updated_account AS (
                          UPDATE cdp.client_accounts
                          SET
                            updated_at = NOW()
                          WHERE id = (SELECT id FROM existing_account)
                          RETURNING id
                        )
                        SELECT id FROM upserted_account UNION ALL SELECT id FROM updated_account;
                    """),
                    {"company": company_clean, "domain": domain}
                )
                client_account_id = account_res.scalar()
                if client_account_id:
                    accounts_processed += 1

                    # Link primary client account to person if not set
                    if person_id:
                        conn.execute(
                            text("""
                                UPDATE cdp.persons
                                SET primary_client_account_id = COALESCE(primary_client_account_id, :account_id),
                                    updated_at = NOW()
                                WHERE id = :person_id;
                            """),
                            {"account_id": client_account_id, "person_id": person_id}
                        )

            # 3. Create person_account_relationship if both person and client_account exist
            if person_id and client_account_id:
                conn.execute(
                    text("""
                        INSERT INTO cdp.person_account_relationships (
                            person_id, client_account_id, job_title, role_type, is_primary, status, created_at, updated_at
                        )
                        VALUES (:person_id, :client_account_id, :job_title, 'decision_maker', TRUE, 'active', NOW(), NOW())
                        ON CONFLICT (person_id, client_account_id, role_type) DO UPDATE SET
                            job_title = COALESCE(EXCLUDED.job_title, cdp.person_account_relationships.job_title),
                            updated_at = NOW();
                    """),
                    {
                        "person_id": person_id,
                        "client_account_id": client_account_id,
                        "job_title": position
                    }
                )
                relationships_processed += 1

            # 4. Mark s_linkedin.connections row as processed
            conn.execute(
                text("UPDATE s_linkedin.connections SET processed = 1 WHERE id = :conn_id"),
                {"conn_id": conn_id}
            )
            processed_count += 1

    logger.info(
        f"CDP processing complete: {processed_count} persons, "
        f"{accounts_processed} accounts, {relationships_processed} relationships processed."
    )
    return {
        "status": "success",
        "processed_count": processed_count,
        "accounts_processed": accounts_processed,
        "relationships_processed": relationships_processed
    }


if __name__ == "__main__":
    process_linkedin_connections()
