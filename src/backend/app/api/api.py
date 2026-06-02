from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict
from app.database import get_db
from app.models import Lead, Draft, Setting, Source
from app.schemas import LeadWithDrafts, LeadUpdate, DraftUpdate, DraftRead, SettingRead, SettingUpdate, SourceRead, SourceCreate

router = APIRouter(prefix="/api")

# --- LEADS ---
@router.get("/leads", response_model=List[LeadWithDrafts])
def get_leads(db: Session = Depends(get_db)):
    # Retrieve leads joined with their raw_message and drafts
    leads = db.query(Lead).options(
        joinedload(Lead.raw_message),
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
    # Find lead first
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get the latest draft or create one if none exists
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
@router.get("/sources", response_model=List[SourceRead])
def get_sources(db: Session = Depends(get_db)):
    return db.query(Source).all()

@router.post("/sources", response_model=SourceRead)
def create_source(source: SourceCreate, db: Session = Depends(get_db)):
    existing = db.query(Source).filter(Source.id == source.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Source with this ID already exists")
    db_source = Source(**source.model_dump())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source

from app.connectors.reddit.reddit_dlt import run_reddit_ingestion

# --- TRIGGER SCAN ---
@router.post("/trigger-scan")
def trigger_scan(db: Session = Depends(get_db)):
    result = run_reddit_ingestion(db)
    return result

