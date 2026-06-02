from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    platform = Column(String, nullable=False)       # 'reddit' | 'slack'
    target = Column(String, nullable=False)         # Subreddit name or Slack channel ID
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    raw_messages = relationship("RawMessage", back_populates="source", cascade="all, delete-orphan")


class RawMessage(Base):
    __tablename__ = "raw_messages"

    id = Column(String, primary_key=True)          # Format: platform:id (e.g. 'reddit:t3_abc123')
    platform = Column(String, nullable=False)
    source_id = Column(String, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    author = Column(String, nullable=True)
    title = Column(String, nullable=True)           # Nullable for Slack messages
    content = Column(Text, nullable=False)
    url = Column(String, nullable=True)
    score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), nullable=True) # Native post creation time
    processed = Column(Integer, default=0)          # 0 = unprocessed, 1 = processed, -1 = error

    source = relationship("Source", back_populates="raw_messages")
    leads = relationship("Lead", back_populates="raw_message", cascade="all, delete-orphan")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_message_id = Column(String, ForeignKey("raw_messages.id", ondelete="CASCADE"), nullable=False)
    intent_score = Column(Float, nullable=True)     # Confidence score of relevance (0.0 to 1.0)
    pain_point = Column(Text, nullable=True)        # Extracted core challenge
    budget = Column(String, nullable=True)           # Budget details if mentioned
    urgency = Column(String, nullable=True)          # Low, Medium, High, Immediate
    technologies = Column(String, nullable=True)     # CSV list of tech mentioned
    status = Column(String, default="inbox")         # 'inbox' | 'contacted' | 'ignored' | 'converted'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    raw_message = relationship("RawMessage", back_populates="leads")
    drafts = relationship("Draft", back_populates="lead", cascade="all, delete-orphan")


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    draft_content = Column(Text, nullable=False)
    edited_content = Column(Text, nullable=True)     # User's modified version of the draft
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lead = relationship("Lead", back_populates="drafts")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
