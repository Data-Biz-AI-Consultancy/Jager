---
name: jager-n8n-workflow-ops
description: >-
  Use this skill when developing, testing, or updating n8n workflows in Jager, including
  content scheduling & dual-track publishing (LinkedIn personal vs Data Biz Zernio),
  AI agent persona definitions, prompt templates, and syncing workflow JSON files.
---

# Jager n8n Workflows & Automation Architecture

Jager uses **n8n** as its primary workflow orchestrator, scheduling jobs, running AI prompts, and calling external APIs and internal microservices.

---

## 1. Workflow Domains & Directory Structure

All workflow JSON files are tracked under [`src/n8n/workflows/`](../../src/n8n/workflows/):

| Domain | Directory | Purpose |
|--------|-----------|---------|
| **Content Publishing** | `ai_retrieval/` | Content scheduling & dual-track publishing to LinkedIn |
| **AI Memory** | `ai_memory/` | Staging, fact extraction, and episodic memory processing |
| **Data Ingestion** | `data_ingestion/` | Multi-channel monitoring (Reddit, Substack, Meetup, etc.) |
| **OLAP & dlt Sync** | `olap/` | Triggers for dlt ingestion pipelines and dbt transformations |
| **CDB Integration** | `cdb/` | REST API webhook sync to CDB (`CDB_SERVICE_URL`) |

---

## 2. Dual-Track LinkedIn Publishing Architecture (`ai_retrieval/`)

Posts stored in `t_content_generation.linkedin_posts` are dispatched via two distinct paths:

```
Scheduler Cron ──► Calculate Slots (skip weekends) ──► Mark Scheduled
                                                            │
Publisher (every 15m) ──► Query Due (scheduled_at <= NOW()) ┴────────┐
                                                                      ▼
                       ┌──────────────────────────────┬──────────────────────────────┐
                       ▼                                                             ▼
             Track A: Individual Channel                                  Track B: Data Biz Channel
         (Native LinkedIn OAuth2 API)                                        (Zernio Post API)
                       │                                                             │
                       ▼                                                             ▼
           POST api.linkedin.com/rest/posts                              POST zernio.com/api/v1/posts
                       │                                                             │
                       ▼                                                             ▼
             Save external_post_id                                         Save external_post_id
```

### Table Schema: `t_content_generation.linkedin_posts`
- `channel`: `'individual'` or `'databiz'`
- `is_approved`, `is_scheduled`, `is_published`: Booleans controlling stage progression
- `scheduled_at`: Target publication timestamp

---

## 3. AI Persona & Prompt File Conventions

- **Agent Persona Markdown Files**: Stored in `src/n8n/agents/` (one file per agent). Must define `Role`, `LLM`, and `Personality & Grounding`.
- **Language & Formatting**:
  - Must communicate **entirely in English** (at most a single Italian greeting/sign-off).
  - Use real Unicode emojis (💡, 📊), never text codes (`:sparkles:`).
  - Slack links must use `<url|Anchor Text>` syntax.
- **Standalone Prompts**: Stored in `prompts/`. Must use `{{VARIABLE_NAME}}` placeholders and explicitly state output formats (e.g. "Output only the raw JSON block").

---

## 4. Environment & Secrets Injection

- In local development, environment variables are loaded via `.env` and `docker-compose.yml`.
- Never commit secrets to workflow JSON files. Always reference n8n expressions `{{ $env.VARIABLE_NAME }}` or credentials entities.
