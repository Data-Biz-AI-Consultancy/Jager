import os
import sys
import csv
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import text

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import setup_logging, get_db_engine

logger = setup_logging("ingest-seeds")

def get_workspace_root():
    # Path to repo root: src/data_pipelines/oltp -> 3 levels up
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

def run_ingestion():
    logger.info("Initializing DB engine for CDP seed ingestion...")
    engine = get_db_engine()
    root_dir = get_workspace_root()

    substack_dir = os.path.join(root_dir, 'data', 'seed', 'substack')
    cdp_dir = os.path.join(root_dir, 'data', 'seed', 'cdp')

    records_processed = 0

    with engine.begin() as conn:
        # 1. Ingest Substack subscriber seed files from data/seed/substack/
        if os.path.exists(substack_dir):
            for fname in os.listdir(substack_dir):
                if fname.endswith('.csv'):
                    fpath = os.path.join(substack_dir, fname)
                    logger.info(f"Processing Substack seed CSV: {fpath}")
                    with open(fpath, mode='r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Substack exports use 'Email' and 'Name' headers (or lowercase fallback)
                            email = (row.get('Email') or row.get('email') or '').strip()
                            if not email:
                                continue
                            full_name = (row.get('Name') or row.get('name') or '').strip()
                            first_name = row.get('first_name', '').strip()
                            last_name = row.get('last_name', '').strip()

                            if full_name and not (first_name or last_name):
                                parts = full_name.split(' ', 1)
                                first_name = parts[0]
                                last_name = parts[1] if len(parts) > 1 else ''

                            country = (row.get('Country') or row.get('country') or '').strip()

                            # Upsert person
                            person_id = str(uuid.uuid4())
                            person_res = conn.execute(
                                text("""
                                    INSERT INTO cdp.persons (id, first_name, last_name, primary_email, country, status, created_at, updated_at)
                                    VALUES (:id, :first_name, :last_name, :email, :country, 'active', NOW(), NOW())
                                    ON CONFLICT (primary_email) DO UPDATE SET
                                        first_name = COALESCE(EXCLUDED.first_name, cdp.persons.first_name),
                                        last_name = COALESCE(EXCLUDED.last_name, cdp.persons.last_name),
                                        country = COALESCE(EXCLUDED.country, cdp.persons.country),
                                        updated_at = NOW()
                                    RETURNING id
                                """),
                                {"id": person_id, "first_name": first_name, "last_name": last_name, "email": email, "country": country}
                            )
                            p_id = person_res.scalar()

                            # Insert lead intake record
                            lead_id = str(uuid.uuid4())
                            conn.execute(
                                text("""
                                    INSERT INTO cdp.leads (id, source, source_lead_id, first_name, last_name, email, person_id, raw_payload, status, intake_at, updated_at)
                                    VALUES (:id, 'substack_seed', :email, :first_name, :last_name, :email, :person_id, :raw_payload, 'processed', NOW(), NOW())
                                """),
                                {
                                    "id": lead_id,
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "email": email,
                                    "person_id": p_id,
                                    "raw_payload": json.dumps(row)
                                }
                            )
                            records_processed += 1

        # 2. Ingest CDP seed lead files from data/seed/cdp/
        if os.path.exists(cdp_dir):
            for fname in os.listdir(cdp_dir):
                if fname.endswith('.json'):
                    fpath = os.path.join(cdp_dir, fname)
                    logger.info(f"Processing CDP seed JSON: {fpath}")
                    with open(fpath, mode='r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            data = [data]
                        for row in data:
                            email = row.get('email', '').strip()
                            if not email:
                                continue
                            first_name = row.get('first_name', '').strip()
                            last_name = row.get('last_name', '').strip()
                            company_name = row.get('company_name', '').strip()
                            job_title = row.get('job_title', '').strip()
                            linkedin_url = row.get('linkedin_url', '').strip()
                            phone = row.get('phone', '').strip()
                            source = row.get('source', 'cdp_seed')

                            # Upsert client_account if company provided
                            client_account_id = None
                            if company_name:
                                account_id = str(uuid.uuid4())
                                domain = company_name.lower().replace(" ", "").replace(",", "") + ".com"
                                acc_res = conn.execute(
                                    text("""
                                        INSERT INTO cdp.client_accounts (id, company_name, domain, status, created_at, updated_at)
                                        VALUES (:id, :company_name, :domain, 'prospect', NOW(), NOW())
                                        ON CONFLICT (domain) DO UPDATE SET
                                            company_name = EXCLUDED.company_name,
                                            updated_at = NOW()
                                        RETURNING id
                                    """),
                                    {"id": account_id, "company_name": company_name, "domain": domain}
                                )
                                client_account_id = acc_res.scalar()

                            # Upsert person
                            person_id = str(uuid.uuid4())
                            person_res = conn.execute(
                                text("""
                                    INSERT INTO cdp.persons (id, first_name, last_name, primary_email, primary_phone, linkedin_url, primary_client_account_id, status, created_at, updated_at)
                                    VALUES (:id, :first_name, :last_name, :email, :phone, :linkedin_url, :client_account_id, 'active', NOW(), NOW())
                                    ON CONFLICT (primary_email) DO UPDATE SET
                                        first_name = COALESCE(EXCLUDED.first_name, cdp.persons.first_name),
                                        last_name = COALESCE(EXCLUDED.last_name, cdp.persons.last_name),
                                        primary_phone = COALESCE(EXCLUDED.primary_phone, cdp.persons.primary_phone),
                                        linkedin_url = COALESCE(EXCLUDED.linkedin_url, cdp.persons.linkedin_url),
                                        primary_client_account_id = COALESCE(EXCLUDED.primary_client_account_id, cdp.persons.primary_client_account_id),
                                        updated_at = NOW()
                                    RETURNING id
                                """),
                                {
                                    "id": person_id,
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "email": email,
                                    "phone": phone,
                                    "linkedin_url": linkedin_url,
                                    "client_account_id": client_account_id
                                }
                            )
                            p_id = person_res.scalar()

                            # Insert lead intake record
                            lead_id = str(uuid.uuid4())
                            conn.execute(
                                text("""
                                    INSERT INTO cdp.leads (id, source, source_lead_id, first_name, last_name, email, phone, company_name, job_title, linkedin_url, person_id, client_account_id, raw_payload, status, intake_at, updated_at)
                                    VALUES (:id, :source, :email, :first_name, :last_name, :email, :phone, :company_name, :job_title, :linkedin_url, :person_id, :client_account_id, :raw_payload, 'processed', NOW(), NOW())
                                """),
                                {
                                    "id": lead_id,
                                    "source": source,
                                    "email": email,
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "phone": phone,
                                    "company_name": company_name,
                                    "job_title": job_title,
                                    "linkedin_url": linkedin_url,
                                    "person_id": p_id,
                                    "client_account_id": client_account_id,
                                    "raw_payload": json.dumps(row)
                                }
                            )

                            # Upsert person account relationship
                            if p_id and client_account_id:
                                rel_id = str(uuid.uuid4())
                                conn.execute(
                                    text("""
                                        INSERT INTO cdp.person_account_relationships (id, person_id, client_account_id, job_title, role_type, status, created_at, updated_at)
                                        VALUES (:id, :person_id, :client_account_id, :job_title, 'decision_maker', 'active', NOW(), NOW())
                                        ON CONFLICT (person_id, client_account_id, role_type) DO UPDATE SET
                                            job_title = EXCLUDED.job_title,
                                            updated_at = NOW()
                                    """),
                                    {
                                        "id": rel_id,
                                        "person_id": p_id,
                                        "client_account_id": client_account_id,
                                        "job_title": job_title
                                    }
                                )

                            records_processed += 1

    logger.info(f"CDP Seed ingestion completed successfully. Processed {records_processed} records.")
    return {"status": "success", "records_processed": records_processed}

if __name__ == "__main__":
    run_ingestion()
