# CDB — Standalone Product Architecture Plan

## Background

The existing `cdp` code inside the Jager repo is a FastAPI service with processors for LinkedIn, Notion meeting notes, manual data, and entity resolution. It connects to an isolated `cdp` PostgreSQL database. The goal is to **extract it into its own standalone product** — with its own repo, backend, frontend, database, and identity — targeting a growth path from solo use → small team → mid-market (200–500 FTE).

---

## Product Identity

| Attribute | Value |
|-----------|-------|
| **Name** | **CDB** (Client DataBase) |
| **Type** | Open-source personal CRM / CDP |
| **Hosting** | Self-hosted (Docker Compose, one-command setup) with optional paid cloud tier |
| **Target users** | Solo → small team → mid-market |
| **License** | Suggested: Apache 2.0 (permissive, enterprise-friendly) |

---

## Core Domain Model

Four top-level entities form the product backbone. **Persons and Companies are peers** — both are first-class entities that independently connect to Activities and Opportunities:

```
Persons ─────────────────────────────── Companies
    │         person_company_relationships   │
    │              (many-to-many)            │
    │                                        │
    ├── Activities ──────────────────────────┤
    │   (meetings, emails, messages, calls)  │
    │                                        │
    └── Opportunities ─────────────────────-┘
        (deals, partnerships, collaborations)
```

### Entity: `persons`
The golden record for a natural person, merged from many sources via Entity Resolution.

| Field | Notes |
|-------|-------|
| `id` | UUID primary key |
| `first_name`, `last_name` | |
| `primary_email` | Strongest identity signal |
| `secondary_emails` | JSONB array |
| `primary_phone` | |
| `linkedin_url` | Normalised (no scheme/www) |
| `twitter_handle`, `facebook_id`, `whatsapp_phone` | |
| `city`, `country` | |
| `avatar_url` | |
| `attributes` | JSONB — flexible extra fields |
| `source_ids` | JSONB — `{"linkedin": "...", "notion": "..."}` per-source ID map |
| `sources` | `text[]` — which sources contributed |
| `created_at`, `updated_at` | |

### Entity: `companies`
Organisations associated with persons.

| Field | Notes |
|-------|-------|
| `id` | UUID |
| `name` | |
| `domain` | e.g. `acme.com` — key deduplication signal |
| `industry`, `size_range`, `country`, `city` | |
| `linkedin_url` | |
| `attributes` | JSONB |
| `created_at`, `updated_at` | |

### Junction: `person_company_relationships`
Many-to-many with metadata.

| Field | Notes |
|-------|-------|
| `person_id`, `company_id` | FKs |
| `role` / `title` | e.g. "CTO", "Investor" |
| `is_current` | bool |
| `started_at`, `ended_at` | |

### Entity: `activities`
Any interaction with a person.

| Field | Notes |
|-------|-------|
| `id` | UUID |
| `person_id` | FK (nullable — company-level activities possible) |
| `company_id` | FK (nullable) |
| `type` | enum: `meeting`, `email`, `linkedin_message`, `whatsapp`, `call`, `note` |
| `source` | e.g. `notion`, `gmail`, `linkedin`, `manual` |
| `source_id` | External ID for idempotent upsert |
| `occurred_at` | |
| `title`, `summary`, `raw_content` | |
| `attributes` | JSONB |

### Entity: `opportunities`
Deals, partnerships, collaborations.

| Field | Notes |
|-------|-------|
| `id` | UUID |
| `title` | |
| `stage` | enum: `prospect`, `qualified`, `proposal`, `negotiation`, `closed_won`, `closed_lost` |
| `value` | decimal, optional |
| `currency` | |
| `probability` | 0–100 |
| `expected_close_date` | |
| `owner_id` | FK to `users` (multi-user ready) |
| `created_at`, `updated_at` | |

### Junction: `opportunity_persons` + `opportunity_companies`
Many-to-many linking opportunities to people and companies.

---

## Intake / Source Layer

Raw source data lands in **source-specific intake tables** before Entity Resolution merges them into the master entities. This preserves raw data and makes ER re-runnable.

| Intake Table | Source |
|--------------|--------|
| `intake_linkedin_connections` | LinkedIn connections CSV export |
| `intake_linkedin_messages` | LinkedIn message export |
| `intake_notion_meeting_notes` | Notion meeting notes (existing) |
| `intake_manual` | Generic manual CSV/XLSX import |
| `intake_gmail` | Gmail (future) |
| `intake_whatsapp` | WhatsApp export (future) |
| `intake_facebook` | Facebook export (future) |

---

## Entity Resolution Design (Hybrid)

**Phase 1 — Rule-based (deterministic):**
- Email exact match → same person
- LinkedIn URL exact match (normalised) → same person
- Phone number match → same person
- Name + Company fuzzy match (Jaro-Winkler ≥ 0.92) → candidate

**Phase 2 — ML-based (probabilistic), for ambiguous candidates:**
- Feature vector: name similarity, email prefix similarity, company overlap, location overlap
- Binary classifier (logistic regression or XGBoost) trained on confirmed matches
- Outputs a confidence score; scores above threshold → auto-merge; below → review queue

**Resolution workflow:**
```
Intake record → Rule-based matching → Match found? → Merge
                                    → No match   → ML scoring → High confidence → Merge
                                                              → Low confidence  → Review queue (UI)
```

The **review queue** is a first-class UI feature (not buried in a script). Users can accept/reject proposed merges.

---

## Tech Stack Decision

### Backend
- **Language**: Python 3.12
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.x (async)
- **Migrations**: Alembic
- **Task Queue**: Celery + Redis (for async ingestion jobs, ER runs)
- **Auth**: JWT-based, multi-user ready from day 1

### Frontend

> [!IMPORTANT]
> Frontend framework is undecided. I recommend **Next.js 15 (App Router)** for these reasons:
> - TypeScript-first — great for a growing codebase
> - Strong ecosystem for data-heavy UIs (tables, graphs)
> - SSR for fast initial loads on person/company detail pages
> - Easy to add auth (NextAuth.js), real-time (SWR/React Query)
> - Easier to hire for when the team grows
>
> **Alternative**: SvelteKit — smaller bundle, simpler DX, but smaller talent pool.
>
> Please confirm your preference.

### Database
- **PostgreSQL 16** — single DB named `cdp`
- Schema: all tables in the `public` schema (this is its own DB, no need for schema namespacing)
- No MotherDuck/DuckDB for now — OLAP can be added later when analytics are needed

### Infrastructure
- **Docker Compose** — CDB has its own `docker-compose.yml` that spins up: `cdb-api`, `cdb-worker` (Celery), `cdb-db` (Postgres), `cdb-redis`, `cdb-frontend`
- **Co-deployed on the same VPS as Jager** — CDB services join Jager's external Docker network so n8n can call `http://cdb-api:8000` directly
- **One-command setup**: `docker compose up -d`

---

## Repo Structure

```
cdp/                          # New standalone repo
├── backend/
│   ├── alembic/              # DB migrations
│   ├── app/
│   │   ├── api/              # FastAPI routers (persons, companies, activities, opportunities)
│   │   ├── core/             # Config, auth, database session
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic (entity resolution, ingestion)
│   │   │   ├── entity_resolution/
│   │   │   │   ├── rules.py           # Rule-based matcher (migrated + refactored from Jager)
│   │   │   │   ├── ml_scorer.py       # ML probabilistic scorer (new)
│   │   │   │   └── merger.py          # Merge logic
│   │   │   └── ingestion/
│   │   │       ├── linkedin.py        # Migrated from Jager
│   │   │       ├── notion.py          # Migrated from Jager
│   │   │       └── manual.py          # Migrated from Jager
│   │   ├── workers/          # Celery tasks
│   │   └── main.py
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── app/                  # Next.js App Router pages
│   │   ├── persons/
│   │   ├── companies/
│   │   ├── activities/
│   │   └── opportunities/
│   ├── components/
│   ├── lib/
│   └── package.json
├── docker-compose.yml
├── .env.example
├── README.md
└── LICENSE
```

---

## API Endpoint Structure

```
GET    /api/persons                  # List persons (search, filter, pagination)
POST   /api/persons                  # Create person manually
GET    /api/persons/{id}             # Person detail + linked companies/activities/opps
PATCH  /api/persons/{id}             # Update
DELETE /api/persons/{id}             # Delete

GET    /api/companies                # List companies
POST   /api/companies
GET    /api/companies/{id}
PATCH  /api/companies/{id}

GET    /api/activities               # List activities (filter by person/company/type)
POST   /api/activities
GET    /api/activities/{id}

GET    /api/opportunities            # List opportunities (filter by stage, person, company)
POST   /api/opportunities
GET    /api/opportunities/{id}
PATCH  /api/opportunities/{id}

POST   /api/ingestion/linkedin       # Trigger LinkedIn import
POST   /api/ingestion/notion         # Trigger Notion sync
POST   /api/ingestion/manual         # Upload CSV/XLSX

GET    /api/entity-resolution/queue  # Review queue for ambiguous merges
POST   /api/entity-resolution/resolve/{candidate_id}  # Accept/reject merge
POST   /api/entity-resolution/run    # Trigger full ER run
```

---

## Jager ↔ CDB Integration

**CDB is the source of truth for all person and company data.** Data flows bidirectionally:

```
┌─────────────────────────────────────────────────────────────┐
│                        Jager VPS                            │
│                                                             │
│  ┌──────────────┐   push raw data    ┌──────────────────┐  │
│  │   Jager n8n  │ ─────────────────► │   CDB API        │  │
│  │  (workflows) │                    │  (port 8000)     │  │
│  │              │ ◄───────────────── │                  │  │
│  └──────────────┘  query persons/    └──────────────────┘  │
│                    companies context       │                │
│                                       ┌───▼──────────────┐  │
│                                       │  CDB Postgres DB │  │
│                                       │  (port 5433)     │  │
│                                       └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Data flow: Jager → CDB (push)
Jager's n8n workflows push raw data into CDB after each sync:

| Jager Trigger | CDB Endpoint Called |
|---------------|---------------------|
| LinkedIn connections sync completes | `POST /api/ingestion/linkedin` |
| Notion meeting notes sync completes | `POST /api/ingestion/notion` |
| Manual CSV upload in n8n | `POST /api/ingestion/manual` |

### Data flow: CDB → Jager (query)
Jager's n8n workflows query CDB for enriched person/company context:

| n8n Workflow Need | CDB Endpoint Queried |
|-------------------|---------------------|
| "Who sent this LinkedIn message?" | `GET /api/persons?linkedin_url=...` |
| "What company is this contact at?" | `GET /api/persons/{id}` (includes company) |
| "Are there open opportunities for this person?" | `GET /api/opportunities?person_id=...` |
| "Log this meeting as an activity" | `POST /api/activities` |

### Environment variable in Jager
Jager's `docker-compose.yml` will expose:
```
CDB_API_URL=http://cdb-api:8000
```
All n8n HTTP Request nodes calling CDB use this variable.

---

## Deployment Topology

**Single VPS, two Docker Compose stacks sharing one Docker network.**

```
VPS
├── docker-compose.yml          ← Jager stack (existing)
│   services: n8n, jager-db, dapp, cdp (transitional), ...
│   networks: jager_network (external)
│
└── cdb/
    └── docker-compose.yml      ← CDB stack (new)
        services:
          cdb-api      → port 8000 (internal), optionally 8001 (host)
          cdb-worker   → Celery, no external port
          cdb-db       → Postgres on port 5433 (host-mapped, avoids conflict with Jager's 5432)
          cdb-redis    → port 6380 (host-mapped)
          cdb-frontend → port 3001 (host-mapped)
        networks: jager_network (external, shared with Jager)
```

### Why a shared Docker network?
- n8n (in the Jager stack) can call `http://cdb-api:8000` without going over the public internet
- No API gateway or reverse proxy needed at this stage
- CDB's DB is fully isolated on its own container — Jager cannot accidentally access it

### Nginx / reverse proxy (optional, recommended)
A single Nginx on the VPS host routes:
- `cdb.yourdomain.com` → `cdb-frontend:3000`
- `api.cdb.yourdomain.com` → `cdb-api:8000`

### Port allocation plan
| Service | Internal port | Host-mapped port |
|---------|--------------|------------------|
| Jager Postgres | 5432 | 5432 |
| CDB Postgres | 5432 (container) | 5433 (host) |
| CDB API | 8000 | 8001 |
| CDB Redis | 6379 | 6380 |
| CDB Frontend | 3000 | 3001 |

---

## Migration Plan from Jager

| What | Action |
|------|--------|
| `src/cdp/processors/entity_resolution.py` | Migrate → `backend/app/services/entity_resolution/` (refactor into rules + merger modules) |
| `src/cdp/processors/process_linkedin_connections.py` | Migrate → `backend/app/services/ingestion/linkedin.py` |
| `src/cdp/processors/process_linkedin_messages.py` | Migrate → `backend/app/services/ingestion/linkedin.py` |
| `src/cdp/processors/process_notion_meeting_notes.py` | Migrate → `backend/app/services/ingestion/notion.py` |
| `src/cdp/processors/process_manual_data.py` | Migrate → `backend/app/services/ingestion/manual.py` |
| `src/cdp/processors/evaluate_segments.py` | **Hold** — segments are advanced; design later |
| DB schema (`cdp` database in Jager) | Re-define via Alembic migrations in new repo |
| Jager n8n workflows calling CDP endpoints | Update URLs after new service is deployed |

---

## Phase Roadmap

### Phase 0 — New Repo Foundation (immediate)
- [ ] Create new repo with the structure above
- [ ] Docker Compose with Postgres, Redis, FastAPI, Celery stubs
- [ ] Alembic setup + initial migrations for all 4 core entities
- [ ] Auth scaffold (JWT, users table)

### Phase 1 — Core Backend (Weeks 1–3)
- [ ] CRUD API for Persons, Companies, Activities, Opportunities
- [ ] Migrate ingestion processors from Jager
- [ ] Migrate and refactor Entity Resolution (rules engine)
- [ ] Celery worker for async ingestion jobs
- [ ] Unit tests for all services

### Phase 2 — Frontend MVP (Weeks 3–6)
- [ ] Persons list + detail page
- [ ] Companies list + detail page
- [ ] Activities timeline (per person)
- [ ] Opportunities pipeline view (Kanban)
- [ ] ER Review Queue UI

### Phase 3 — ML Entity Resolution (Weeks 6–10)
- [ ] Feature extraction pipeline
- [ ] Train initial classifier on manually confirmed matches
- [ ] Integrate ML scorer into ER pipeline
- [ ] Confidence score display in Review Queue UI

### Phase 4 — New Sources (ongoing)
- [ ] Gmail integration
- [ ] WhatsApp export parser
- [ ] Facebook export parser

---

## Confirmed Decisions

| Decision | Choice |
|----------|--------|
| Product name | **CDB** (Client DataBase) |
| Integration with Jager | CDB is source of truth; bidirectional API (Jager pushes data in, queries context out) |
| Deployment | Same VPS as Jager; shared Docker network; separate Docker Compose stack |
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL 16 (own container, port 5433 on host) |
| Entity Resolution | Hybrid: rule-based first, ML fallback for ambiguous cases |

## Remaining Open Questions

> [!IMPORTANT]
> **Frontend framework**: Confirm **Next.js 15** (recommended) or SvelteKit.

> [!IMPORTANT]
> **New repo location on disk**: Suggest `/Users/jimmypang/AntigravityProjects/JagerProjects/CDB/`. Confirm or provide preferred path.

> [!IMPORTANT]
> **Jager decoupling**: After CDB is live, should `src/cdp/` be **removed from Jager** immediately, or run in parallel during a transition period until all n8n workflows are updated?

> [!NOTE]
> **Segments** (`evaluate_segments.py`): Move to CDB as a future "Segments" feature, or leave in Jager for now?
