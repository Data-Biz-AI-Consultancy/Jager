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
    from processors.process_linkedin_connections import generate_company_domain
except ImportError:
    from src.cdp.utils import setup_logging, get_db_engine
    from src.cdp.processors.process_linkedin_connections import generate_company_domain

logger = setup_logging("cdp-manual-data-processor")


def process_manual_data():
    """
    Scans tables in the s_manual schema (e.g., notion__* tables created by manual ingestion),
    extracts lead/contact/company entities, and normalizes them into cdp.leads, cdp.persons, and cdp.client_accounts.
    """
    logger.info("Starting processing of s_manual tables into cdp schema...")
    engine = get_db_engine()

    leads_processed = 0
    persons_processed = 0
    accounts_processed = 0

    with engine.begin() as conn:
        # 1. Discover all user tables in s_manual schema
        tables_res = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 's_manual'
                  AND table_type = 'BASE TABLE'
            """)
        ).fetchall()

        table_names = [r[0] for r in tables_res]
        logger.info(f"Found {len(table_names)} tables in s_manual: {table_names}")

        for table in table_names:
            # Check table column names dynamically
            cols_res = conn.execute(
                text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 's_manual'
                      AND table_name = :table_name
                """),
                {"table_name": table}
            ).fetchall()
            col_set = {r[0].lower() for r in cols_res}

            # Build query to fetch rows from the manual table
            # If the table has a 'processed' column, filter by processed = 0
            has_processed = "processed" in col_set
            where_clause = "WHERE processed = 0" if has_processed else ""

            select_query = f"SELECT * FROM s_manual.{table} {where_clause}"
            rows = conn.execute(text(select_query)).mappings().all()

            if not rows:
                logger.info(f"No unprocessed rows found in s_manual.{table}.")
                continue

            for row in rows:
                row_dict = dict(row)

                # Identify potential contact/lead fields dynamically from common Notion/manual column names
                first_name = (
                    row_dict.get("first_name") or
                    row_dict.get("firstname") or
                    row_dict.get("name") or
                    row_dict.get("full_name") or
                    row_dict.get("title") or
                    ""
                )
                if isinstance(first_name, str):
                    first_name = first_name.strip()
                else:
                    first_name = ""

                last_name = (
                    row_dict.get("last_name") or
                    row_dict.get("lastname") or
                    ""
                )
                if isinstance(last_name, str):
                    last_name = last_name.strip()
                else:
                    last_name = ""

                email = (
                    row_dict.get("email") or
                    row_dict.get("primary_email") or
                    row_dict.get("email_address") or
                    ""
                )
                if isinstance(email, str):
                    email = email.strip()
                else:
                    email = ""

                phone = (
                    row_dict.get("phone") or
                    row_dict.get("primary_phone") or
                    row_dict.get("phone_number") or
                    ""
                )
                if isinstance(phone, str):
                    phone = phone.strip()
                else:
                    phone = ""

                linkedin_url = (
                    row_dict.get("linkedin") or
                    row_dict.get("linkedin_url") or
                    row_dict.get("profile_url") or
                    row_dict.get("notion_url") or
                    ""
                )
                if isinstance(linkedin_url, str):
                    linkedin_url = linkedin_url.strip()
                else:
                    linkedin_url = ""

                company = (
                    row_dict.get("company") or
                    row_dict.get("company_name") or
                    row_dict.get("organization") or
                    ""
                )
                if isinstance(company, str):
                    company = company.strip()
                else:
                    company = ""

                # Skip if no meaningful person or company details found
                if not first_name and not last_name and not email and not linkedin_url and not company:
                    if has_processed and "id" in row_dict:
                        conn.execute(
                            text(f"UPDATE s_manual.{table} SET processed = 1 WHERE id = :row_id"),
                            {"row_id": row_dict["id"]}
                        )
                    elif has_processed and "notion_id" in row_dict:
                        conn.execute(
                            text(f"UPDATE s_manual.{table} SET processed = 1 WHERE notion_id = :row_id"),
                            {"row_id": row_dict["notion_id"]}
                        )
                    continue

                # 1. Upsert person into cdp.persons if contact info exists
                person_id = None
                if first_name or last_name or email or linkedin_url:
                    person_res = conn.execute(
                        text("""
                            WITH existing_person AS (
                              SELECT id FROM cdp.persons
                              WHERE (primary_email IS NOT NULL AND primary_email = :email AND :email != '')
                                 OR (linkedin_url IS NOT NULL AND linkedin_url = :linkedin_url AND :linkedin_url != '')
                              LIMIT 1
                            ),
                            upserted_person AS (
                              INSERT INTO cdp.persons (first_name, last_name, primary_email, primary_phone, linkedin_url, status, created_at, updated_at)
                              SELECT :first_name, :last_name, NULLIF(:email, ''), NULLIF(:phone, ''), NULLIF(:linkedin_url, ''), 'active', NOW(), NOW()
                              WHERE NOT EXISTS (SELECT 1 FROM existing_person)
                              RETURNING id
                            ),
                            updated_person AS (
                              UPDATE cdp.persons
                              SET
                                first_name = COALESCE(NULLIF(:first_name, ''), cdp.persons.first_name),
                                last_name = COALESCE(NULLIF(:last_name, ''), cdp.persons.last_name),
                                primary_email = COALESCE(NULLIF(:email, ''), cdp.persons.primary_email),
                                primary_phone = COALESCE(NULLIF(:phone, ''), cdp.persons.primary_phone),
                                linkedin_url = COALESCE(NULLIF(:linkedin_url, ''), cdp.persons.linkedin_url),
                                updated_at = NOW()
                              WHERE id = (SELECT id FROM existing_person)
                              RETURNING id
                            )
                            SELECT id FROM upserted_person UNION ALL SELECT id FROM updated_person;
                        """),
                        {
                            "first_name": first_name or None,
                            "last_name": last_name or None,
                            "email": email or "",
                            "phone": phone or "",
                            "linkedin_url": linkedin_url or ""
                        }
                    )
                    person_id = person_res.scalar()
                    if person_id:
                        persons_processed += 1

                # 2. Process company into cdp.client_accounts if present
                client_account_id = None
                if company:
                    domain = generate_company_domain(company)
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
                              SET updated_at = NOW()
                              WHERE id = (SELECT id FROM existing_account)
                              RETURNING id
                            )
                            SELECT id FROM upserted_account UNION ALL SELECT id FROM updated_account;
                        """),
                        {"company": company, "domain": domain}
                    )
                    client_account_id = account_res.scalar()
                    if client_account_id:
                        accounts_processed += 1

                # 3. Create lead record in cdp.leads
                full_lead_name = f"{first_name} {last_name}".strip() or company or "Manual Lead"
                conn.execute(
                    text("""
                        INSERT INTO cdp.leads (
                            person_id, client_account_id, full_name, description, status, source, raw_payload, intake_at, updated_at
                        )
                        VALUES (
                            :person_id, :client_account_id, :full_name, :description, 'prospect', :source, :raw_payload, NOW(), NOW()
                        );
                    """),
                    {
                        "person_id": person_id,
                        "client_account_id": client_account_id,
                        "full_name": full_lead_name,
                        "description": f"Manual lead ingested from s_manual.{table}",
                        "source": f"manual:{table}",
                        "raw_payload": str(row_dict)
                    }
                )
                leads_processed += 1

                # 4. Mark row as processed if column exists
                if has_processed:
                    if "id" in row_dict:
                        conn.execute(
                            text(f"UPDATE s_manual.{table} SET processed = 1 WHERE id = :row_id"),
                            {"row_id": row_dict["id"]}
                        )
                    elif "notion_id" in row_dict:
                        conn.execute(
                            text(f"UPDATE s_manual.{table} SET processed = 1 WHERE notion_id = :row_id"),
                            {"row_id": row_dict["notion_id"]}
                        )

    logger.info(
        f"s_manual data processing complete: {leads_processed} leads, "
        f"{persons_processed} persons, {accounts_processed} client accounts processed."
    )
    return {
        "status": "success",
        "leads_processed": leads_processed,
        "persons_processed": persons_processed,
        "accounts_processed": accounts_processed
    }


if __name__ == "__main__":
    process_manual_data()
