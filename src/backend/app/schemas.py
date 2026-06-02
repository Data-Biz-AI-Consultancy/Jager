from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Source schemas
class SourceBase(BaseModel):
    id: str
    platform: str
    target: str
    active: Optional[bool] = True

class SourceCreate(SourceBase):
    pass

class SourceRead(SourceBase):
    created_at: datetime

    class Config:
        from_attributes = True

# RawMessage schemas
class RawMessageRead(BaseModel):
    id: str
    platform: str
    source_id: str
    author: Optional[str] = None
    title: Optional[str] = None
    content: str
    url: Optional[str] = None
    score: int
    created_at: Optional[datetime] = None
    processed: int

    class Config:
        from_attributes = True

# Draft schemas
class DraftBase(BaseModel):
    draft_content: str
    edited_content: Optional[str] = None

class DraftCreate(DraftBase):
    lead_id: int

class DraftUpdate(BaseModel):
    draft_content: Optional[str] = None
    edited_content: Optional[str] = None

class DraftRead(DraftBase):
    id: int
    lead_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Lead schemas
class LeadBase(BaseModel):
    raw_message_id: str
    intent_score: Optional[float] = None
    pain_point: Optional[str] = None
    budget: Optional[str] = None
    urgency: Optional[str] = None
    technologies: Optional[str] = None
    status: Optional[str] = "inbox"

class LeadUpdate(BaseModel):
    status: Optional[str] = None

class LeadRead(LeadBase):
    id: int
    created_at: datetime
    raw_message: Optional[RawMessageRead] = None

    class Config:
        from_attributes = True

class LeadWithDrafts(LeadRead):
    drafts: List[DraftRead] = []

    class Config:
        from_attributes = True

# Setting schemas
class SettingBase(BaseModel):
    key: str
    value: str

class SettingRead(SettingBase):
    class Config:
        from_attributes = True

class SettingUpdate(BaseModel):
    value: str
