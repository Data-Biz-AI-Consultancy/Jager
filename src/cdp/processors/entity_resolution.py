import logging
import json
import re
from sqlalchemy import text

logger = logging.getLogger("cdp-entity-resolution")

def clean_email(email_raw):
    if not email_raw:
        return None
    email = str(email_raw).strip().lower()
    if not email or "@linkedin.user" in email or "invalid" in email:
        return None
    return email

def clean_url(url_raw):
    if not url_raw:
        return None
    url = str(url_raw).strip()
    if not url:
        return None
    url = re.sub(r'https?://(www\.)?', '', url).rstrip('/')
    return url

def deduplicate_master_persons(cdp_conn):
    """
    Scans cdp.persons for existing duplicate records (by clean_url, email, or name),
    merges their attributes, re-links foreign keys, and deletes secondary duplicate rows.
    """
    logger.info("Running post-resolution master deduplication on cdp.persons...")
    
    all_persons = cdp_conn.execute(
        text("SELECT id, first_name, last_name, primary_email, linkedin_url, in_linkedin_connections, in_substack_subscriber_export, created_at FROM cdp.persons")
    ).mappings().all()

    url_groups = {}
    email_groups = {}

    for p in all_persons:
        url = clean_url(p["linkedin_url"])
        email = clean_email(p["primary_email"])

        if url:
            url_groups.setdefault(url, []).append(p)
        if email:
            email_groups.setdefault(email, []).append(p)

    merged_duplicates = 0

    # Process URL duplicates
    for url, group in url_groups.items():
        if len(group) <= 1:
            continue
        # Pick master (prefer row with double first name e.g. "Pui Man" over "Pui", or oldest created)
        group_sorted = sorted(group, key=lambda x: (0 if " " in (x["first_name"] or "") else 1, x["created_at"]))
        master = group_sorted[0]
        duplicates = group_sorted[1:]

        master_id = master["id"]
        dup_ids = [d["id"] for d in duplicates]

        # Merge presence flags
        any_in_linkedin = any(d["in_linkedin_connections"] for d in group)
        any_in_substack = any(d["in_substack_subscriber_export"] for d in group)

        # Update master record with clean URL
        cdp_conn.execute(
            text("""
                UPDATE cdp.persons SET 
                    linkedin_url = :url,
                    in_linkedin_connections = :in_linkedin,
                    in_substack_subscriber_export = :in_substack,
                    updated_at = NOW()
                WHERE id = :master_id
            """),
            {"url": url, "in_linkedin": any_in_linkedin, "in_substack": any_in_substack, "master_id": master_id}
        )

        # Re-link foreign keys across all 7 referencing tables to master_id and remove duplicate
        for dup_id in dup_ids:
            cdp_conn.execute(text("UPDATE cdp.leads SET person_id = :master_id WHERE person_id = :dup_id"), {"master_id": master_id, "dup_id": dup_id})
            cdp_conn.execute(text("UPDATE cdp.leads_linkedin SET person_id = :master_id WHERE person_id = :dup_id"), {"master_id": master_id, "dup_id": dup_id})
            cdp_conn.execute(text("UPDATE cdp.leads_manual SET person_id = :master_id WHERE person_id = :dup_id"), {"master_id": master_id, "dup_id": dup_id})
            cdp_conn.execute(text("UPDATE cdp.activities SET person_id = :master_id WHERE person_id = :dup_id"), {"master_id": master_id, "dup_id": dup_id})
            cdp_conn.execute(text("UPDATE cdp.activities_notion_meeting_notes SET person_id = :master_id WHERE person_id = :dup_id"), {"master_id": master_id, "dup_id": dup_id})
            cdp_conn.execute(text("UPDATE cdp.engagements SET person_id = :master_id WHERE person_id = :dup_id"), {"master_id": master_id, "dup_id": dup_id})
            cdp_conn.execute(text("UPDATE cdp.person_company_relationships SET person_id = :master_id WHERE person_id = :dup_id"), {"master_id": master_id, "dup_id": dup_id})
            cdp_conn.execute(text("DELETE FROM cdp.persons WHERE id = :dup_id"), {"dup_id": dup_id})
            merged_duplicates += 1

    logger.info(f"Deduplication complete: Merged and removed {merged_duplicates} duplicate records from cdp.persons.")
    return merged_duplicates


def resolve_persons(cdp_conn):
    """
    Consolidates person data from cdp.persons_linkedins, cdp.persons_manual_substack,
    and cdp.activities_notion_meeting_notes into cdp.persons.
    """
    logger.info("Starting CDP Entity Resolution into cdp.persons...")
    
    # 1. Fetch all intake records from cdp.persons_linkedins
    linkedin_rows = cdp_conn.execute(
        text("""
            SELECT connection_id, first_name, last_name, profile_url, email_address, company, position, connected_at, raw_payload
            FROM cdp.persons_linkedins
        """)
    ).mappings().all()

    # 2. Fetch all intake records from cdp.persons_manual_substack
    substack_rows = cdp_conn.execute(
        text("""
            SELECT id, email, first_name, last_name, full_name, phone, linkedin_url, country, subscribed_at, source_table, raw_payload
            FROM cdp.persons_manual_substack
        """)
    ).mappings().all()

    # 3. Fetch meeting notes attendees from cdp.activities_notion_meeting_notes
    notes_rows = cdp_conn.execute(
        text("""
            SELECT page_id, attendees, person_id
            FROM cdp.activities_notion_meeting_notes
            WHERE attendees IS NOT NULL AND attendees != ''
        """)
    ).mappings().all()

    email_to_person = {}
    email_prefix_to_person = {}
    url_to_person = {}
    name_to_person = {}
    resolved_persons = []

    def find_or_create_person(email, url, first_name="", last_name=""):
        p = None
        name_key = (first_name.strip().lower(), last_name.strip().lower()) if (first_name and last_name) else None
        
        email_prefix = None
        if email and "@" in email:
            raw_pre = email.split("@")[0].lower()
            clean_pre = re.sub(r'\d+$', '', raw_pre)
            if len(clean_pre) >= 5:
                email_prefix = clean_pre

        if email and email in email_to_person:
            p = email_to_person[email]
        elif url and url in url_to_person:
            p = url_to_person[url]
        elif name_key and name_key in name_to_person:
            p = name_to_person[name_key]
        elif email_prefix and email_prefix in email_prefix_to_person:
            p = email_prefix_to_person[email_prefix]
        
        if not p:
            p = {
                "first_name": first_name or None,
                "last_name": last_name or None,
                "primary_email": email or None,
                "secondary_emails": [],
                "primary_phone": None,
                "linkedin_url": url or None,
                "city": None,
                "country": None,
                "in_linkedin_connections": False,
                "in_substack_subscriber_export": False,
                "sources": set()
            }
            resolved_persons.append(p)
            if email:
                email_to_person[email] = p
            if url:
                url_to_person[url] = p
            if name_key:
                name_to_person[name_key] = p
            if email_prefix:
                email_prefix_to_person[email_prefix] = p
        else:
            if not p["first_name"] and first_name:
                p["first_name"] = first_name
            if not p["last_name"] and last_name:
                p["last_name"] = last_name
            if email and email != p["primary_email"] and email not in p["secondary_emails"]:
                p["secondary_emails"].append(email)
                email_to_person[email] = p
            if url and not p["linkedin_url"]:
                p["linkedin_url"] = url
                url_to_person[url] = p

        return p

    # Process LinkedIn rows
    for row in linkedin_rows:
        e = clean_email(row["email_address"])
        u = clean_url(row["profile_url"])
        fn = row["first_name"] or ""
        ln = row["last_name"] or ""
        
        p = find_or_create_person(e, u, fn, ln)
        p["in_linkedin_connections"] = True
        p["sources"].add("linkedin")

    # Process Substack rows
    for row in substack_rows:
        e = clean_email(row["email"])
        u = clean_url(row["linkedin_url"])
        fn = row["first_name"] or ""
        ln = row["last_name"] or ""
        if not fn and not ln and row["full_name"]:
            parts = row["full_name"].strip().split(maxsplit=1)
            fn = parts[0]
            ln = parts[1] if len(parts) > 1 else ""

        p = find_or_create_person(e, u, fn, ln)
        p["in_substack_subscriber_export"] = True
        p["sources"].add("substack")
        if row["phone"] and not p["primary_phone"]:
            p["primary_phone"] = row["phone"]
        if row["country"] and not p["country"]:
            p["country"] = row["country"]

    # Process Meeting Notes Attendees
    for row in notes_rows:
        raw_att = row["attendees"] or ""
        attendees = [a.strip() for a in raw_att.replace(';', ',').split(',') if a.strip()]
        for att in attendees:
            if "@" in att:
                e = clean_email(att)
                p = find_or_create_person(e, None)
                p["sources"].add("notion_meeting_notes")
            else:
                parts = att.split(maxsplit=1)
                fn = parts[0]
                ln = parts[1] if len(parts) > 1 else ""
                p = find_or_create_person(None, None, fn, ln)
                p["sources"].add("notion_meeting_notes")

    logger.info(f"Resolved {len(resolved_persons)} distinct master persons from intake sources.")

    # Upsert resolved persons into cdp.persons
    resolved_count = 0
    for p in resolved_persons:
        email = p["primary_email"]
        url = p["linkedin_url"]
        fn = p["first_name"]
        ln = p["last_name"]

        existing = None
        if email:
            existing = cdp_conn.execute(
                text("SELECT id FROM cdp.persons WHERE primary_email = :email"),
                {"email": email}
            ).fetchone()
        
        if not existing and url:
            clean_u = clean_url(url)
            existing = cdp_conn.execute(
                text("""
                    SELECT id FROM cdp.persons
                    WHERE linkedin_url = :url
                       OR linkedin_url = :clean_url
                       OR linkedin_url = :https_url
                       OR linkedin_url = :www_url
                    LIMIT 1
                """),
                {
                    "url": url,
                    "clean_url": clean_u,
                    "https_url": f"https://{clean_u}" if clean_u else url,
                    "www_url": f"https://www.{clean_u}" if clean_u else url
                }
            ).fetchone()
        if not existing and fn and ln:
            existing = cdp_conn.execute(
                text("""
                    SELECT id FROM cdp.persons
                    WHERE LOWER(first_name) = LOWER(:fn) AND LOWER(last_name) = LOWER(:ln)
                    LIMIT 1
                """),
                {"fn": fn, "ln": ln}
            ).fetchone()

        sec_emails = json.dumps({"secondary_emails": p["secondary_emails"]}) if p["secondary_emails"] else "{}"

        if existing:
            cdp_conn.execute(
                text("""
                    UPDATE cdp.persons SET
                        first_name = COALESCE(:first_name, cdp.persons.first_name),
                        last_name = COALESCE(:last_name, cdp.persons.last_name),
                        primary_email = COALESCE(:primary_email, cdp.persons.primary_email),
                        primary_phone = COALESCE(:primary_phone, cdp.persons.primary_phone),
                        linkedin_url = COALESCE(:linkedin_url, cdp.persons.linkedin_url),
                        country = COALESCE(:country, cdp.persons.country),
                        attributes = CASE WHEN :attributes != '{}'::jsonb THEN cdp.persons.attributes || CAST(:attributes AS jsonb) ELSE cdp.persons.attributes END,
                        in_linkedin_connections = (cdp.persons.in_linkedin_connections OR :in_linkedin),
                        in_substack_subscriber_export = (cdp.persons.in_substack_subscriber_export OR :in_substack),
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "id": existing[0],
                    "first_name": fn,
                    "last_name": ln,
                    "primary_email": email,
                    "primary_phone": p["primary_phone"],
                    "linkedin_url": url,
                    "country": p["country"],
                    "attributes": sec_emails,
                    "in_linkedin": p["in_linkedin_connections"],
                    "in_substack": p["in_substack_subscriber_export"]
                }
            )
        else:
            cdp_conn.execute(
                text("""
                    INSERT INTO cdp.persons (
                        first_name, last_name, primary_email, primary_phone, linkedin_url,
                        country, attributes, in_linkedin_connections, in_substack_subscriber_export,
                        created_at, updated_at
                    ) VALUES (
                        :first_name, :last_name, :primary_email, :primary_phone, :linkedin_url,
                        :country, CAST(:attributes AS jsonb), :in_linkedin, :in_substack,
                        NOW(), NOW()
                    )
                """),
                {
                    "first_name": fn,
                    "last_name": ln,
                    "primary_email": email,
                    "primary_phone": p["primary_phone"],
                    "linkedin_url": url,
                    "country": p["country"],
                    "attributes": sec_emails,
                    "in_linkedin": p["in_linkedin_connections"],
                    "in_substack": p["in_substack_subscriber_export"]
                }
            )
        resolved_count += 1

    # Execute post-resolution master deduplication cleanup
    deduplicate_master_persons(cdp_conn)

    logger.info(f"Entity resolution complete: {resolved_count} persons resolved in cdp.persons.")
    return resolved_count
