from unittest.mock import MagicMock, patch
from processors.entity_resolution import resolve_persons, clean_email, clean_url

def test_clean_email():
    assert clean_email("John.Doe@Example.com ") == "john.doe@example.com"
    assert clean_email("user@linkedin.user") is None
    assert clean_email(None) is None

def test_clean_url():
    assert clean_url("https://www.linkedin.com/in/johndoe/") == "linkedin.com/in/johndoe"
    assert clean_url("http://linkedin.com/in/janedoe") == "linkedin.com/in/janedoe"
    assert clean_url(None) is None

def test_resolve_persons():
    mock_cdp_conn = MagicMock()

    linkedin_rows = [
        {
            "connection_id": "conn1",
            "first_name": "Alice",
            "last_name": "Smith",
            "profile_url": "https://linkedin.com/in/alicesmith",
            "email_address": "alice@example.com",
            "company": "Tech Corp",
            "position": "Engineer",
            "connected_at": None,
            "raw_payload": "{}"
        }
    ]
    substack_rows = [
        {
            "id": "sub1",
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "full_name": "Alice Smith",
            "phone": "+123456789",
            "linkedin_url": None,
            "country": "Germany",
            "subscribed_at": None,
            "source_table": "notion__substack",
            "raw_payload": "{}"
        }
    ]
    notes_rows = [
        {
            "page_id": "page1",
            "attendees": "Alice Smith, Bob Jones (bob@example.com)",
            "person_id": None
        }
    ]

    mock_cdp_conn.execute.return_value.mappings.return_value.all.side_effect = [
        linkedin_rows,
        substack_rows,
        notes_rows
    ]
    mock_cdp_conn.execute.return_value.fetchone.return_value = None

    resolved_count = resolve_persons(mock_cdp_conn)
    assert resolved_count == 2  # Alice (merged) and Bob Jones (name & email merged)
