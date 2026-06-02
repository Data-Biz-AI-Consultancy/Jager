import pytest
from app.models import Source, RawMessage, Lead, Draft, Setting

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to the Jager API" in response.json()["message"]

# --- SETTINGS TESTS ---
def test_get_settings(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    settings = response.json()
    assert len(settings) == 3
    keys = [s["key"] for s in settings]
    assert "ollama_model" in keys
    assert "ollama_url" in keys
    assert "user_profile" in keys

def test_post_setting_new(client):
    response = client.post("/api/settings", json={"key": "test_key", "value": "test_val"})
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "test_key"
    assert data["value"] == "test_val"

def test_post_setting_update(client, db):
    response = client.post("/api/settings", json={"key": "ollama_model", "value": "llama3.1"})
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "ollama_model"
    assert data["value"] == "llama3.1"
    
    # Verify in DB
    setting = db.query(Setting).filter(Setting.key == "ollama_model").first()
    assert setting.value == "llama3.1"

# --- SOURCES TESTS ---
def test_get_sources_empty(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    assert response.json() == []

def test_create_source(client, db):
    payload = {
        "id": "reddit:smallbusiness",
        "platform": "reddit",
        "target": "smallbusiness",
        "active": True
    }
    response = client.post("/api/sources", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "reddit:smallbusiness"
    assert data["platform"] == "reddit"
    assert data["target"] == "smallbusiness"
    
    # Verify DB
    src = db.query(Source).filter(Source.id == "reddit:smallbusiness").first()
    assert src is not None
    assert src.target == "smallbusiness"

def test_create_duplicate_source_error(client):
    payload = {
        "id": "reddit:smallbusiness",
        "platform": "reddit",
        "target": "smallbusiness"
    }
    # First time succeeds
    client.post("/api/sources", json=payload)
    # Second time fails
    response = client.post("/api/sources", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

# --- LEADS & DRAFTS TESTS ---
def test_get_leads_empty(client):
    response = client.get("/api/leads")
    assert response.status_code == 200
    assert response.json() == []

def test_get_leads_populated(client, db):
    # Setup dependencies
    source = Source(id="reddit:saas", platform="reddit", target="saas")
    db.add(source)
    db.commit()

    raw_msg = RawMessage(
        id="reddit:t3_12345",
        platform="reddit",
        source_id="reddit:saas",
        author="john_doe",
        title="Need saas recommendation",
        content="Looking for a tool to generate leads.",
        score=10,
        processed=1
    )
    db.add(raw_msg)
    db.commit()

    lead = Lead(
        raw_message_id="reddit:t3_12345",
        intent_score=0.95,
        pain_point="Lead generation",
        urgency="High",
        status="inbox"
    )
    db.add(lead)
    db.commit()

    draft = Draft(
        lead_id=lead.id,
        draft_content="Hi John, we can help you build custom LLM scraping workflows..."
    )
    db.add(draft)
    db.commit()

    response = client.get("/api/leads")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["raw_message"]["title"] == "Need saas recommendation"
    assert len(data[0]["drafts"]) == 1
    assert data[0]["drafts"][0]["draft_content"] == "Hi John, we can help you build custom LLM scraping workflows..."

def test_update_lead_status(client, db):
    source = Source(id="reddit:saas", platform="reddit", target="saas")
    db.add(source)
    raw_msg = RawMessage(
        id="reddit:t3_123",
        platform="reddit",
        source_id="reddit:saas",
        content="Test content",
        score=1,
        processed=1
    )
    db.add(raw_msg)
    db.commit()

    lead = Lead(raw_message_id="reddit:t3_123", status="inbox")
    db.add(lead)
    db.commit()

    # Update status
    response = client.patch(f"/api/leads/{lead.id}", json={"status": "contacted"})
    assert response.status_code == 200
    assert response.json()["status"] == "contacted"

    # Verify DB
    db.refresh(lead)
    assert lead.status == "contacted"

def test_update_lead_status_not_found(client):
    response = client.patch("/api/leads/9999", json={"status": "contacted"})
    assert response.status_code == 404

def test_update_lead_draft_create_and_update(client, db):
    source = Source(id="reddit:saas", platform="reddit", target="saas")
    db.add(source)
    raw_msg = RawMessage(
        id="reddit:t3_123",
        platform="reddit",
        source_id="reddit:saas",
        content="Test content",
        score=1,
        processed=1
    )
    db.add(raw_msg)
    db.commit()

    lead = Lead(raw_message_id="reddit:t3_123", status="inbox")
    db.add(lead)
    db.commit()

    # Create new draft via PUT
    response = client.put(
        f"/api/leads/{lead.id}/draft", 
        json={"draft_content": "Initial Draft Content"}
    )
    assert response.status_code == 200
    assert response.json()["draft_content"] == "Initial Draft Content"

    # Update the draft
    response = client.put(
        f"/api/leads/{lead.id}/draft", 
        json={"draft_content": "Updated Draft Content", "edited_content": "User Edited Content"}
    )
    assert response.status_code == 200
    assert response.json()["draft_content"] == "Updated Draft Content"
    assert response.json()["edited_content"] == "User Edited Content"

def test_update_lead_draft_not_found(client):
    response = client.put("/api/leads/9999/draft", json={"draft_content": "Hello"})
    assert response.status_code == 404

# --- TRIGGER SCAN ---
def test_trigger_scan(client):
    response = client.post("/api/trigger-scan")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
