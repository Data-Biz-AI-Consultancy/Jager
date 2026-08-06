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

def resolve_persons(cdp_conn):
    """
    Consolidates person data from cdp.persons_linkedins, cdp.persons_manual_substack,
    and cdp.activities_notion_meeting_notes into cdp.persons.
    
    Entity resolution strategy:
    1. Primary match on normalized primary_email.
    2. Secondary match on normalized linkedin_url.
    3. Calculate presence flags (in_linkedin_connections, in_substack_subscriber_export).
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

    # Build entity registry maps in memory
    email_to_person = {}
    url_to_person = {}
    name_to_person = {}
    resolved_persons = []

    def find_or_create_person(email, url, first_name="", last_name=""):
        p = None
        name_key = (first_name.strip().lower(), last_name.strip().lower()) if (first_name and last_name) else None

        if email and email in email_to_person:
            p = email_to_person[email]
        elif url and url in url_to_person:
            p = url_to_person[url]
        elif name_key and name_key in name_to_person:
            p = name_to_person[name_key]
        
        if not p:
            p = {
                "first_name": first_name or None,
                "last_name": last_name or None,
                "primary_email": email or None,
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
        else:
            # Merge fields if missing
            if not p["first_name"] and first_name:
                p["first_name"] = first_name
            if not p["last_name"] and last_name:
                p["last_name"] = last_name
            if not p["primary_email"] and email:
                p["primary_email"] = email
                email_to_person[email] = p
            if not p["linkedin_url"] and url:
                p["linkedin_url"] = url
                url_to_person[url] = p
            if name_key and name_key not in name_to_person:
                name_to_person[name_key] = p
                
        return p

    # Process LinkedIn connection intake rows
    for row in linkedin_rows:
        fn = (row.get("first_name") or "").strip()
        ln = (row.get("last_name") or "").strip()
        email = clean_email(row.get("email_address"))
        url = clean_url(row.get("profile_url"))

        if not fn and not ln and not email and not url:
            continue

        p = find_or_create_person(email=email, url=url, first_name=fn, last_name=ln)
        p["in_linkedin_connections"] = True
        p["sources"].add("linkedin")

    # Process Substack subscriber intake rows
    for row in substack_rows:
        fn = (row.get("first_name") or "").strip()
        ln = (row.get("last_name") or "").strip()
        full_name = (row.get("full_name") or "").strip()
        if not fn and not ln and full_name:
            parts = full_name.split(maxsplit=1)
            fn = parts[0]
            ln = parts[1] if len(parts) > 1 else ""

        email = clean_email(row.get("email"))
        phone = (row.get("phone") or "").strip() or None
        url = clean_url(row.get("linkedin_url"))
        country = (row.get("country") or "").strip() or None

        if not fn and not ln and email and "@" in email:
            prefix = email.split("@")[0]
            if "." in prefix:
                parts = prefix.split(".", 1)
                fn = parts[0].capitalize()
                ln = parts[1].capitalize()
            elif "_" in prefix:
                parts = prefix.split("_", 1)
                fn = parts[0].capitalize()
                ln = parts[1].capitalize()

        if not fn and not ln and not email and not url:
            continue

        p = find_or_create_person(email=email, url=url, first_name=fn, last_name=ln)
        p["in_substack_subscriber_export"] = True
        p["sources"].add("substack")
        if not p["primary_phone"] and phone:
            p["primary_phone"] = phone
        if not p["country"] and country:
            p["country"] = country

    # Process Notion Meeting Notes attendees
    for row in notes_rows:
        attendees_str = row.get("attendees") or ""
        names = [n.strip() for n in re.split(r'[\n,]+', attendees_str) if n.strip()]
        for name in names:
            if name.lower() == "jimmy pang":
                continue
            fn, ln = "", ""
            parts = name.split(maxsplit=1)
            fn = parts[0]
            ln = parts[1] if len(parts) > 1 else ""

            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', name)
            email = clean_email(email_match.group(0)) if email_match else None
            
            p = find_or_create_person(email=email, url=None, first_name=fn, last_name=ln)
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
                    "in_linkedin": p["in_linkedin_connections"],
                    "in_substack": p["in_substack_subscriber_export"]
                }
            )
        else:
            cdp_conn.execute(
                text("""
                    INSERT INTO cdp.persons (
                        first_name, last_name, primary_email, primary_phone, linkedin_url,
                        country, in_linkedin_connections, in_substack_subscriber_export,
                        created_at, updated_at
                    ) VALUES (
                        :first_name, :last_name, :primary_email, :primary_phone, :linkedin_url,
                        :country, :in_linkedin, :in_substack,
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
                    "in_linkedin": p["in_linkedin_connections"],
                    "in_substack": p["in_substack_subscriber_export"]
                }
            )
        resolved_count += 1

    logger.info(f"Entity resolution complete: {resolved_count} persons upserted/updated in cdp.persons.")
    return resolved_count
