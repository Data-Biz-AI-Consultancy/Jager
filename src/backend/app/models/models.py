from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class RedditSubredditMonitored(Base):
    __tablename__ = "reddit_subreddits_monitored"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)       # Subreddit name (e.g. 'smallbusiness')
    active = Column(Boolean, default=True)
    rules = Column(Text, nullable=True)                      # Custom rules for checking/AI
    title = Column(String, nullable=True)                    # RSS feed title
    updated_at = Column(DateTime(timezone=True), nullable=True) # RSS feed updated timestamp
    icon = Column(String, nullable=True)                     # Subreddit RSS icon link
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    posts = relationship("RedditPost", back_populates="subreddit", cascade="all, delete-orphan")


class RedditPost(Base):
    __tablename__ = "reddit_posts"

    id = Column(String, primary_key=True)                    # Format: t3_abc123
    subreddit_id = Column(Integer, ForeignKey("reddit_subreddits_monitored.id", ondelete="CASCADE"), nullable=False)
    author = Column(String, nullable=True)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    url = Column(String, nullable=True)
    score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), nullable=True)
    processed = Column(Integer, default=0)                   # 0 = unprocessed, 1 = processed, -1 = error

    subreddit = relationship("RedditSubredditMonitored", back_populates="posts")
    comments = relationship("RedditComment", back_populates="post", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="post", cascade="all, delete-orphan")


class RedditComment(Base):
    __tablename__ = "reddit_comments"

    id = Column(String, primary_key=True)                    # Format: t1_xyz789
    post_id = Column(String, ForeignKey("reddit_posts.id", ondelete="CASCADE"), nullable=False)
    author = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), nullable=True)

    post = relationship("RedditPost", back_populates="comments")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String, ForeignKey("reddit_posts.id", ondelete="CASCADE"), nullable=False)
    intent_score = Column(Float, nullable=True)              # Confidence score of relevance (0.0 to 1.0)
    pain_point = Column(Text, nullable=True)                 # Extracted core challenge
    budget = Column(String, nullable=True)                   # Budget details if mentioned
    urgency = Column(String, nullable=True)                  # Low, Medium, High, Immediate
    technologies = Column(String, nullable=True)             # CSV list of tech mentioned
    status = Column(String, default="inbox")                 # 'inbox' | 'contacted' | 'ignored' | 'converted'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("RedditPost", back_populates="leads")
    drafts = relationship("Draft", back_populates="lead", cascade="all, delete-orphan")


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    draft_content = Column(Text, nullable=False)
    edited_content = Column(Text, nullable=True)             # User's modified version of the draft
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lead = relationship("Lead", back_populates="drafts")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
