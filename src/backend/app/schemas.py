from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# Subreddit Monitored schemas
class RedditSubredditMonitoredBase(BaseModel):
    name: str
    active: Optional[bool] = True
    rules: Optional[str] = None

class RedditSubredditMonitoredCreate(RedditSubredditMonitoredBase):
    pass

class RedditSubredditMonitoredRead(RedditSubredditMonitoredBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Comment schemas
class RedditCommentRead(BaseModel):
    id: str
    post_id: str
    author: Optional[str] = None
    content: str
    score: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Post schemas
class RedditPostRead(BaseModel):
    id: str
    subreddit_id: int
    author: Optional[str] = None
    title: Optional[str] = None
    content: str
    url: Optional[str] = None
    score: int
    created_at: Optional[datetime] = None
    processed: int

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

# Lead schemas
class LeadBase(BaseModel):
    post_id: str
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
    post: Optional[RedditPostRead] = None

    model_config = ConfigDict(from_attributes=True)

class LeadWithDrafts(LeadRead):
    drafts: List[DraftRead] = []

    model_config = ConfigDict(from_attributes=True)

# Setting schemas
class SettingBase(BaseModel):
    key: str
    value: str

class SettingRead(SettingBase):
    model_config = ConfigDict(from_attributes=True)

class SettingUpdate(BaseModel):
    value: str
