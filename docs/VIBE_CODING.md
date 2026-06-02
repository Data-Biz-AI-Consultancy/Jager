# AI Developer Guide (Vibe Coding with Jager)

Welcome, agent! This document is a dedicated reference guide for **AI native development (vibe coding)** on **Jager**. It details developer preferences, project vibes, architecture assumptions, and code styles to help you iterate quickly and harmoniously.

---

## 1. The Jager Vibe & Philosophy

*   **Data-First, Thin Frontend:** Jager is a data harvester and filter. The backend and background ingestion workers do the heavy lifting. The frontend is a clean "face" for review and configuration. Keep backend logic decoupled from presentation.
*   **Local-First & Free:** Default to **Ollama** running locally. Minimize dependency on costly external Cloud APIs. If cloud providers (Gemini, OpenAI) are added, make them strictly optional overrides.
*   **Value-First Outreach:** Never generate spam templates. The response drafts should read like thoughtful human interactions.

---

## 2. Technology Blueprint

When adding code or features, adhere to this stack:

| Layer | Technology | Key Patterns / Preferences |
| :--- | :--- | :--- |
| **Backend** | Python (FastAPI) | Lightweight, fast async routes, easy integration with PRAW (Reddit API) and Slack SDK. |
| **Database** | SQLite | Keep it simple. Avoid heavy ORMs unless necessary; raw SQL or basic `sqlite3` bindings work great. |
| **LLM Inference** | Ollama API | Querying `http://localhost:11434/api/generate` or `/api/chat`. Default model: `llama3`. |
| **Frontend** | React (Vite) | Single page dashboard, clean CSS grids/flexbox, custom dark mode, premium micro-animations. |

---

## 3. The Core Ingestion & Processing Pipeline

Any agent adding data sources (e.g., Discord watcher, Twitter stream) must adhere to the following sequence:

```
Ingestion Engine ➔ Raw SQLite Cache ➔ LLM Intent Filter ➔ SQLite Leads ➔ LLM Draft Generator ➔ SQLite Drafts
```

1.  **Ingestion:** Scrape/listen to the platform and dump raw text + metadata into `raw_messages` with `processed = 0`.
2.  **Intent Filter:** Read `processed = 0` raw posts. Pass to `prompts/intent_detection.md`.
    *   If `is_lead` is true, write to `leads` table and mark `processed = 1`.
    *   Else, update `raw_messages.processed = 1` and ignore.
3.  **Lead Enrichment:** Run `prompts/lead_enrichment.md` on the lead. Extract pain points and budget.
4.  **Drafting:** Read settings (`settings` table) to find the user profile. Run `prompts/draft_response.md` using the profile and lead metadata. Write to `drafts`.

---

## 4. Coding Rules & Conventions

*   **SQL Schema:** Keep all tables in a single SQLite database file (`database.db`). Track timestamps in ISO 8601 UTC.
*   **Prompt Management:** Never hardcode LLM prompts in code. Always load them dynamically from the `prompts/` folder (e.g., load [intent_detection.md](file:///Users/jimmypang/AntigravityProjects/Jager/prompts/intent_detection.md)). This allows the user to easily tweak prompt instructions.
*   **Frontend Design:** Use a rich dark-mode theme. Avoid plain default colors. Opt for modern typography, subtle cards, and interactive hover feedback.
