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
                            email = row.get('email', '').strip()
                            if not email:
                                continue
                            first_name = row.get('first_name', '').strip()
                            last_name = row.get('last_name', '').strip()

                            # Upsert person
                            person_id = str(uuid.uuid4())
                            person_res = conn.execute(
                                text("""
                                    INSERT INTO cdp.persons (id, first_name, last_name, primary_email, status, created_at, updated_at)
                                    VALUES (:id, :first_name, :last_name, :email, 'active', NOW(), NOW())
                                    ON CONFLICT (primary_email) DO UPDATE SET
                                        first_name = COALESCE(EXCLUDED.first_name, cdp.persons.first_name),
                                        last_name = COALESCE(EXCLUDED.last_name, cdp.persons.last_name),
                                        updated_at = NOW()
                                    RETURNING id
                                """),
                                {"id": person_id, "first_name": first_name, "last_name": last_name, "email": email}
                            )
                            p_id = person_res.scalar()

                            # Insert lead intake record
                            lead_id = str(uuid.uuid4())
                            full_name = f"{first_name} {last_name}".strip() or None
                            conn.execute(
                                text("""
                                    INSERT INTO cdp.leads (id, person_id, full_name, description, status, source, raw_payload, intake_at, updated_at)
                                    VALUES (:id, :person_id, :full_name, 'Substack subscriber lead', 'person_linked', 'substack_seed', :raw_payload, NOW(), NOW())
                                """),
                                {
                                    "id": lead_id,
                                    "person_id": p_id,
                                    "full_name": full_name,
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
                                acc_status = row.get('account_status', 'prospect').strip()
                                acc_res = conn.execute(
                                    text("""
                                        INSERT INTO cdp.client_accounts (id, company_name, domain, status, created_at, updated_at)
                                        VALUES (:id, :company_name, :domain, :status, NOW(), NOW())
                                        ON CONFLICT (domain) DO UPDATE SET
                                            company_name = EXCLUDED.company_name,
                                            status = EXCLUDED.status,
                                            updated_at = NOW()
                                        RETURNING id
                                    """),
                                    {"id": account_id, "company_name": company_name, "domain": domain, "status": acc_status}
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
                            full_name = f"{first_name} {last_name}".strip() or None
                            lead_status = 'engaging' if client_account_id else 'prospect'
                            description = row.get('description', f"Role: {job_title}" if job_title else None)
                            rate = row.get('rate')
                            conn.execute(
                                text("""
                                    INSERT INTO cdp.leads (id, person_id, full_name, description, rate, status, source, raw_payload, intake_at, updated_at)
                                    VALUES (:id, :person_id, :full_name, :description, :rate, :status, :source, :raw_payload, NOW(), NOW())
                                """),
                                {
                                    "id": lead_id,
                                    "person_id": p_id,
                                    "full_name": full_name,
                                    "description": description,
                                    "rate": rate,
                                    "status": lead_status,
                                    "source": source,
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
