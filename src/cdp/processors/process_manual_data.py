import os
import sys
import re
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
    from processors.process_linkedin_connections import generate_company_domain
except ImportError:
    from utils import setup_logging, get_db_engine
    from processors.process_linkedin_connections import generate_company_domain

logger = setup_logging("cdp-manual-data-processor")


def process_manual_data():
    """
    Cross-checks Substack Subscriber data from s_manual schema in jager DB against LinkedIn connections
    in cdp.persons (in cdp DB) to maintain a complete, unified view of contacts.
    """
    logger.info("Starting processing of s_manual tables into cdp schema...")
    jager_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/jager", env_var="JAGER_DATABASE_URL")
    cdp_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/cdp", env_var="DATABASE_URL")

    leads_processed = 0
    persons_processed = 0
    accounts_processed = 0

    with jager_engine.begin() as jager_conn, cdp_engine.begin() as cdp_conn:
        # 1. Discover user data tables in s_manual schema in jager DB
        tables_res = jager_conn.execute(
            text(r"""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 's_manual'
                  AND table_type = 'BASE TABLE'
                  AND table_name NOT LIKE '\_dlt%'
            """)
        ).fetchall()

        table_names = [r[0] for r in tables_res]
        logger.info(f"Found {len(table_names)} user data tables in s_manual: {table_names}")

        for table in table_names:
            cols_res = jager_conn.execute(
                text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 's_manual'
                      AND table_name = :table_name
                """),
                {"table_name": table}
            ).fetchall()
            col_set = {r[0].lower() for r in cols_res}

            has_processed = "processed" in col_set
            where_clause = "WHERE processed = 0" if has_processed else ""

            select_query = f"SELECT * FROM s_manual.{table} {where_clause}"
            rows = jager_conn.execute(text(select_query)).mappings().all()

            if not rows:
                logger.info(f"No unprocessed rows found in s_manual.{table}.")
                continue

            for row in rows:
                row_dict = dict(row)

                # Extract contact fields (e.g. Substack subscriber export or Notion pages)
                raw_name = (
                    row_dict.get("name") or
                    row_dict.get("full_name") or
                    row_dict.get("title") or
                    ""
                )
                if isinstance(raw_name, str):
                    raw_name = raw_name.strip()
                else:
                    raw_name = ""

                first_name = row_dict.get("first_name") or row_dict.get("firstname") or ""
                last_name = row_dict.get("last_name") or row_dict.get("lastname") or ""

                if not first_name and not last_name and raw_name:
                    parts = raw_name.split(maxsplit=1)
                    first_name = parts[0]
                    last_name = parts[1] if len(parts) > 1 else ""

                if isinstance(first_name, str):
                    first_name = first_name.strip()
                else:
                    first_name = ""

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

                country = (
                    row_dict.get("country") or
                    row_dict.get("state_province") or
                    ""
                )
                if isinstance(country, str):
                    country = country.strip()
                else:
                    country = ""

                # Skip blank records with no identifying fields
                if not first_name and not last_name and not email and not linkedin_url and not company and not raw_name:
                    if has_processed and "id" in row_dict:
                        jager_conn.execute(
                            text(f"UPDATE s_manual.{table} SET processed = 1 WHERE id = :row_id"),
                            {"row_id": row_dict["id"]}
                        )
                    elif has_processed and "notion_id" in row_dict:
                        jager_conn.execute(
                            text(f"UPDATE s_manual.{table} SET processed = 1 WHERE notion_id = :row_id"),
                            {"row_id": row_dict["notion_id"]}
                        )
                    continue

                # Determine source flags based on manual table name
                is_substack = "substack" in table.lower()
                is_linkedin = "linkedin" in table.lower()

                person_id = None
                # 1. Upsert person intake record into cdp.persons_manual_substack if substack table
                if is_substack and (first_name or last_name or email or linkedin_url):
                    row_id = str(row_dict.get("id") or row_dict.get("notion_id") or uuid.uuid4())
                    cdp_conn.execute(
                        text("""
                            INSERT INTO cdp.persons_manual_substack (
                                id, email, first_name, last_name, full_name, phone, linkedin_url, country,
                                source_table, raw_payload, intake_at, updated_at
                            ) VALUES (
                                :id, :email, :first_name, :last_name, :full_name, :phone, :linkedin_url, :country,
                                :source_table, CAST(:raw_payload AS jsonb), NOW(), NOW()
                            )
                            ON CONFLICT (id) DO UPDATE SET
                                email = EXCLUDED.email,
                                first_name = EXCLUDED.first_name,
                                last_name = EXCLUDED.last_name,
                                full_name = EXCLUDED.full_name,
                                phone = EXCLUDED.phone,
                                linkedin_url = EXCLUDED.linkedin_url,
                                country = EXCLUDED.country,
                                source_table = EXCLUDED.source_table,
                                raw_payload = EXCLUDED.raw_payload,
                                updated_at = NOW();
                        """),
                        {
                            "id": row_id,
                            "email": email or None,
                            "first_name": first_name or None,
                            "last_name": last_name or None,
                            "full_name": raw_name or None,
                            "phone": phone or None,
                            "linkedin_url": linkedin_url or None,
                            "country": country or None,
                            "source_table": table,
                            "raw_payload": json.dumps(row_dict, default=str)
                        }
                    )
                    persons_processed += 1

                # 2. Process company into cdp.companies if present
                company_id = None
                if company:
                    domain = generate_company_domain(company)
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
                              SET updated_at = NOW()
                              WHERE id = (SELECT id FROM existing_account)
                              RETURNING id
                            )
                            SELECT id FROM upserted_account UNION ALL SELECT id FROM updated_account;
                        """),
                        {"company": company, "domain": domain}
                    )
                    company_id = account_res.scalar()
                    if company_id:
                        accounts_processed += 1

                # 3. Create lead record in cdp.leads_manual and cdp.leads
                full_lead_name = f"{first_name} {last_name}".strip() or raw_name or company or "Manual Lead"
                serialized_json = json.dumps(row_dict, default=str)
                lead_id = str(row_dict.get("notion_id") or row_dict.get("id") or uuid.uuid4())

                cdp_conn.execute(
                    text("""
                        INSERT INTO cdp.leads_manual (
                            id, person_id, company_id, full_name, description, status, source, raw_payload, intake_at, updated_at
                        )
                        VALUES (
                            :id, :person_id, :company_id, :full_name, :description, 'prospect', :source, CAST(:raw_payload AS jsonb), NOW(), NOW()
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            person_id = COALESCE(EXCLUDED.person_id, cdp.leads_manual.person_id),
                            company_id = COALESCE(EXCLUDED.company_id, cdp.leads_manual.company_id),
                            full_name = EXCLUDED.full_name,
                            description = EXCLUDED.description,
                            source = EXCLUDED.source,
                            raw_payload = EXCLUDED.raw_payload,
                            updated_at = NOW();
                    """),
                    {
                        "id": lead_id,
                        "person_id": person_id,
                        "company_id": company_id,
                        "full_name": full_lead_name,
                        "description": f"Manual lead ingested from s_manual.{table}",
                        "source": f"manual:{table}",
                        "raw_payload": serialized_json
                    }
                )

                cdp_conn.execute(
                    text("""
                        INSERT INTO cdp.leads (
                            id, person_id, company_id, full_name, description, status, source, raw_payload, intake_at, updated_at
                        )
                        VALUES (
                            :id, :person_id, :company_id, :full_name, :description, 'prospect', 'Manual', CAST(:raw_payload AS jsonb), NOW(), NOW()
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            person_id = COALESCE(EXCLUDED.person_id, cdp.leads.person_id),
                            company_id = COALESCE(EXCLUDED.company_id, cdp.leads.company_id),
                            full_name = EXCLUDED.full_name,
                            description = EXCLUDED.description,
                            source = EXCLUDED.source,
                            raw_payload = EXCLUDED.raw_payload,
                            updated_at = NOW();
                    """),
                    {
                        "id": lead_id,
                        "person_id": person_id,
                        "company_id": company_id,
                        "full_name": full_lead_name,
                        "description": f"Manual lead ingested from s_manual.{table}",
                        "raw_payload": serialized_json
                    }
                )
                leads_processed += 1

                # 4. Mark row as processed if column exists
                if has_processed:
                    if "id" in row_dict:
                        jager_conn.execute(
                            text(f"UPDATE s_manual.{table} SET processed = 1 WHERE id = :row_id"),
                            {"row_id": row_dict["id"]}
                        )
                    elif "notion_id" in row_dict:
                        jager_conn.execute(
                            text(f"UPDATE s_manual.{table} SET processed = 1 WHERE notion_id = :row_id"),
                            {"row_id": row_dict["notion_id"]}
                        )

        # Trigger unified entity resolution into cdp.persons
        from processors.entity_resolution import resolve_persons
        with cdp_engine.begin() as cdp_conn:
            persons_resolved = resolve_persons(cdp_conn)

    logger.info(
        f"s_manual data processing complete: {leads_processed} leads, "
        f"{persons_processed} manual persons ingested, {accounts_processed} client accounts processed, "
        f"{persons_resolved} master persons resolved."
    )
    return {
        "status": "success",
        "leads_processed": leads_processed,
        "persons_processed": persons_processed,
        "accounts_processed": accounts_processed,
        "persons_resolved": persons_resolved
    }


if __name__ == "__main__":
    process_manual_data()

