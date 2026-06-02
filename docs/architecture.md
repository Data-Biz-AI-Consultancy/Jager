# Technical Architecture: Jager

This document describes the technical architecture, data model, and API contracts for **Jager**.

---

## 1. System Components

Jager is structured as a mono-repository containing a Python or Node.js backend running a background data worker, and a lightweight React web frontend.

```
Jager/
├── backend/
│   ├── app/
│   │   ├── engines/          # Reddit, Slack ingestion logic
│   │   ├── pipeline/         # Ollama intent, enrichment, drafting execution
│   │   ├── models/           # SQLite DB entities
│   │   └── api/              # Rest API endpoints
│   ├── database.db           # SQLite DB file
│   └── main.py               # Entry point
├── frontend/
│   ├── src/                  # React dashboard code
│   └── index.html
├── prompts/                  # Prompt files loaded at runtime
└── docs/                     # Documentation files
```

---

## 2. Ingestion Engines & Pipelines

Ingestion is handled by modular collectors executing at scheduled intervals:

### 2.1 The Reddit Engine
- Uses `PRAW` (Python Reddit API Wrapper).
- Listens to configured subreddits.
- Fetches submissions matching custom keyword criteria or directly scans the top 50 posts of active subreddits.
- Deep scans comments of matched posts to capture conversational context.

### 2.2 The Slack Engine
- Configured using a Slack App Token or User OAuth Token.
- Pulls from channels via `conversations.history` or registers a WebSocket listener using Slack Socket Mode (`slack_sdk.socket_mode`).
- Flattens threads into a searchable corpus.

---

## 3. Database Schema

The local SQLite database contains five primary tables:

```sql
-- Track target channels to monitor
CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,       -- 'reddit' | 'slack'
    target TEXT NOT NULL,         -- Subreddit name (e.g. 'smallbusiness') or Slack channel ID
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store all ingested posts/messages before AI filtering
CREATE TABLE raw_messages (
    id TEXT PRIMARY KEY,          -- Format: platform:id (e.g. 'reddit:t3_abc123')
    platform TEXT NOT NULL,
    source_id TEXT NOT NULL,
    author TEXT,
    title TEXT,                   -- Nullable for Slack messages
    content TEXT NOT NULL,
    url TEXT,
    score INTEGER DEFAULT 0,      -- Upvotes minus downvotes
    created_at TIMESTAMP,         -- Native post creation time
    processed INTEGER DEFAULT 0,   -- 0 = unprocessed, 1 = processed, -1 = processing error
    FOREIGN KEY(source_id) REFERENCES sources(id)
);

-- Filtered high-intent opportunities
CREATE TABLE leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_message_id TEXT NOT NULL,
    intent_score REAL,            -- Confidence score of relevance (0.0 to 1.0)
    pain_point TEXT,              -- Extracted core challenge
    budget TEXT,                  -- Budget details if mentioned
    urgency TEXT,                 -- Low, Medium, High, Immediate
    technologies TEXT,            -- CSV list of tech mentioned
    status TEXT DEFAULT 'inbox',  -- 'inbox' | 'contacted' | 'ignored' | 'converted'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(raw_message_id) REFERENCES raw_messages(id)
);

-- AI drafted responses
CREATE TABLE drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    draft_content TEXT NOT NULL,
    edited_content TEXT,          -- User's modified version of the draft
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(lead_id) REFERENCES leads(id)
);

-- App configurations
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

---

## 4. Ollama Integration & Orchestration

The AI layer talks to a local Ollama instance running at `http://localhost:11434`.

- **Orchestrator Sequence:**
  1. Read unprocessed entries from `raw_messages`.
  2. Invoke `prompts/intent_detection.md` via Ollama API `/api/generate`.
  3. If classification == `LEAD`, proceed to step 4. Otherwise, mark `raw_messages.processed = 1` and stop.
  4. Invoke `prompts/lead_enrichment.md` to extract metadata JSON. Write data to `leads`.
  5. Read user's business profile from the database (`settings`).
  6. Invoke `prompts/draft_response.md` passing both lead info and user profile to construct a template draft. Save to `drafts`.
  7. Mark `raw_messages.processed = 1`.

---

## 5. API Contracts (Backend to Frontend Face)

The backend exposes a simple REST API on port `8000`:

*   `GET /api/leads` - Returns list of leads, including metadata and linked drafts.
*   `PATCH /api/leads/:id` - Updates lead status (e.g. archive, ignore, mark contacted).
*   `PUT /api/leads/:id/draft` - Updates the custom message draft content.
*   `GET /api/settings` - Fetches settings (Ollama model, monitored sources, API keys).
*   `POST /api/settings` - Saves system settings.
*   `POST /api/trigger-scan` - Force trigger the ingestion and LLM execution pipeline.
