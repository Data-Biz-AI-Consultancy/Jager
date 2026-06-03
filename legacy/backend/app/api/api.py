from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Any
from app.database import get_db
from app.models import Lead, Draft, Setting, RedditSubredditMonitored
from app.schemas import LeadWithDrafts, LeadUpdate, DraftUpdate, DraftRead, SettingRead

router = APIRouter(prefix="/api")

# --- LEADS ---
@router.get("/leads", response_model=List[LeadWithDrafts])
def get_leads(db: Session = Depends(get_db)):
    leads = db.query(Lead).options(
        joinedload(Lead.post),
        joinedload(Lead.drafts)
    ).order_by(Lead.created_at.desc()).all()
    return leads

@router.patch("/leads/{lead_id}", response_model=LeadWithDrafts)
def update_lead(lead_id: int, lead_update: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if lead_update.status is not None:
        lead.status = lead_update.status
    
    db.commit()
    db.refresh(lead)
    return lead

# --- DRAFTS ---
@router.put("/leads/{lead_id}/draft", response_model=DraftRead)
def update_lead_draft(lead_id: int, draft_update: DraftUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    draft = db.query(Draft).filter(Draft.lead_id == lead_id).order_by(Draft.created_at.desc()).first()
    if not draft:
        if draft_update.draft_content is None:
            raise HTTPException(status_code=400, detail="No existing draft, draft_content is required")
        draft = Draft(lead_id=lead_id, draft_content=draft_update.draft_content)
        db.add(draft)
    
    if draft_update.draft_content is not None:
        draft.draft_content = draft_update.draft_content
    if draft_update.edited_content is not None:
        draft.edited_content = draft_update.edited_content
        
    db.commit()
    db.refresh(draft)
    return draft

# --- SETTINGS ---
@router.get("/settings", response_model=List[SettingRead])
def get_settings(db: Session = Depends(get_db)):
    return db.query(Setting).all()

@router.post("/settings", response_model=SettingRead)
def save_setting(setting_update: SettingRead, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == setting_update.key).first()
    if setting:
        setting.value = setting_update.value
    else:
        setting = Setting(key=setting_update.key, value=setting_update.value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting

# --- MONITORED SOURCES ---
@router.get("/sources")
def get_sources(db: Session = Depends(get_db)):
    # Map the new RedditSubredditMonitored model to backward-compatible Source representation
    subreddits = db.query(RedditSubredditMonitored).all()
    return [
        {
            "id": f"reddit:{sub.name}",
            "platform": "reddit",
            "target": sub.name,
            "active": sub.active
        }
        for sub in subreddits
    ]

@router.post("/sources")
def create_source(source_data: Dict[str, Any], db: Session = Depends(get_db)):
    target_name = source_data.get("target")
    if not target_name:
        raise HTTPException(status_code=400, detail="Subreddit 'target' is required")
    
    target_name = target_name.strip().lower()
    
    existing = db.query(RedditSubredditMonitored).filter(RedditSubredditMonitored.name == target_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subreddit already exists in monitored list")
    
    db_sub = RedditSubredditMonitored(
        name=target_name,
        active=source_data.get("active", True),
        rules=source_data.get("rules")
    )
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    
    return {
        "id": f"reddit:{db_sub.name}",
        "platform": "reddit",
        "target": db_sub.name,
        "active": db_sub.active
    }

# --- DELETE SOURCE ---
@router.delete("/sources/{source_id}")
def delete_source(source_id: str, db: Session = Depends(get_db)):
    # Extract subreddit name from source_id "reddit:saas"
    if not source_id.startswith("reddit:"):
        raise HTTPException(status_code=400, detail="Invalid source ID format")
    
    subreddit_name = source_id[7:].lower()
    db_sub = db.query(RedditSubredditMonitored).filter(RedditSubredditMonitored.name == subreddit_name).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Monitored subreddit not found")
    
    db.delete(db_sub)
    db.commit()
    return {"status": "success", "message": f"r/{subreddit_name} removed from monitored list"}

from app.connectors.reddit.reddit_dlt import run_reddit_ingestion

# --- TRIGGER SCAN ---
@router.post("/trigger-scan")
def trigger_scan(db: Session = Depends(get_db)):
    result = run_reddit_ingestion(db)
    return result
