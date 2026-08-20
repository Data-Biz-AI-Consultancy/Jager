# CDB — Product Requirements Document (PRD)

**Version**: 0.1 (Draft)
**Status**: Under Review
**Last Updated**: 2026-08-20

---

## 1. Product Overview & Vision

### What is CDB?

**CDB (Client DataBase)** is an open-source, self-hosted personal CRM and Customer Data Platform (CDP) designed to give professionals a single, unified view of everyone they know — across all channels and tools.

CDB solves a fundamental problem: your professional network is scattered across LinkedIn, email, WhatsApp, meeting notes, spreadsheets, and every SaaS tool you use. No single place holds the full picture of a person. CDB is that place.

At its core, CDB:
- **Unifies** person and company data from many sources into a single golden record per entity
- **Resolves** duplicate identities across sources using rule-based and ML-powered entity resolution
- **Tracks** all activities (meetings, messages, emails) against those records
- **Manages** opportunities (deals, partnerships, collaborations) linked to people and companies

### Vision Statement

> Give every professional — from solo consultants to growing teams — the same quality of customer intelligence that enterprise CRMs provide, without the cost, lock-in, or complexity.

### Design Principles

1. **People-first**: The person is the primary unit of value, not the lead or the deal.
2. **Source-agnostic**: Any data source can feed into CDB. The product is not tied to any single platform.
3. **Transparent by default**: Entity resolution decisions are visible and overridable by the user.
4. **Open and self-hostable**: One `docker compose up -d` to run it. No SaaS required.
5. **Grows with you**: Designed for solo use today, small team tomorrow, mid-market the day after.

---

## 2. Target Users & Personas

### Persona 1: Solo Professional *(Initial target)*
**Who**: Consultant, founder, investor, sales professional operating individually.
**Pain**: Contacts scattered across LinkedIn exports, email threads, and Notion notes. No memory of last interaction. Misses follow-ups.
**Goal**: One place to see who they know, how they know them, and what's pending.
**Key needs**: Fast import of LinkedIn connections, automatic deduplication, simple activity log.

### Persona 2: Small Team *(3–10 people)*
**Who**: Early-stage startup, boutique consultancy, fund.
**Pain**: Multiple people track the same person in different tools. No shared pipeline.
**Goal**: Shared, team-wide view of contacts and deals.
**Key needs**: Multi-user access, shared opportunity pipeline, team activity feed, role-based access.

### Persona 3: Mid-Market Team *(50–500 FTE)*
**Who**: Growth-stage company, professional services firm, VC fund.
**Pain**: Existing CRMs are expensive, rigid, and require manual data entry.
**Goal**: Automated, high-quality contact intelligence platform integrated with existing workflows.
**Key needs**: API-first integration, ML entity resolution, segment evaluation, audit logs, SSO.

---

## 3. Core Features

### 3.1 Persons

A unified golden record for every natural person, merged from all sources via Entity Resolution.

- Full contact profile: name, email(s), phone, LinkedIn, social handles, location
- Source attribution: which systems contributed to this record
- Activity timeline: all interactions with this person in chronological order
- Linked companies: current and past roles

### 3.2 Companies

A first-class entity — peer to Persons, not subordinate.

- Company profile: name, domain, industry, size, location, LinkedIn
- Linked persons: all known contacts at this company with their roles
- Activity and opportunity history at the company level

### 3.3 Activities

Any recorded interaction with a person or company.

- Types: `meeting`, `email`, `linkedin_message`, `whatsapp`, `call`, `note`
- Source-tagged: which system the activity came from (`notion`, `gmail`, `linkedin`, `manual`)
- Idempotent upsert via `source_id` — re-ingesting the same source never creates duplicates
- AI-generated or manual summaries

### 3.4 Opportunities

Deals, partnerships, and collaborations being tracked.

- Pipeline stages: `prospect → qualified → proposal → negotiation → closed_won / closed_lost`
- Linked to one or more persons and companies
- Optional value, currency, probability, expected close date
- Owner assignment (multi-user ready from day 1)

### 3.5 Entity Resolution

Automatic identification that two records from different sources represent the same real person.

- **Rule-based** (Phase 1): email match, LinkedIn URL match, phone match, name+company fuzzy match
- **ML-based fallback** (Phase 3): probabilistic scoring for ambiguous pairs
- **Review Queue**: a first-class UI for users to accept/reject proposed merges — not a backend script

### 3.6 Source Integrations

| Source | Mechanism | Phase |
|--------|-----------|-------|
| LinkedIn connections | CSV export upload | 1 |
| LinkedIn messages | ZIP export upload | 1 |
| Notion meeting notes | Notion API | 1 |
| Manual CSV / XLSX | File upload + column mapper | 1 |
| Substack subscribers | CSV export upload | 2 |
| Gmail | Google OAuth | 3 |
| WhatsApp | Export ZIP parser | 3 |
| Google / Outlook Calendar | OAuth + Calendar API | 3 |
| Facebook connections | Export ZIP parser | 4 |

---

## 4. Key UX Screens

### Persons List
- Full-text search (name, email, company)
- Filter: source, country, has open opportunity
- Sortable columns: name, last activity, created date
- Slide-in quick-view panel on row click

### Person Detail
- Header: avatar, name, current title + company
- Contact info: email, phone, LinkedIn, social handles
- Source badges showing which systems contributed
- Activity timeline (chronological)
- Linked companies with role history
- Open opportunities mini-view

### Companies List & Detail
- Peer to Persons — same visual weight in navigation
- Company detail shows all linked persons with roles, activity history, opportunities

### Activities Feed
- Global chronological feed across all persons and companies
- Filter by type, source, date range, person, company

### Opportunities Pipeline
- Kanban view with columns per stage
- Drag-to-advance
- Quick-add from any person or company detail page

### Entity Resolution Review Queue
- Side-by-side comparison of two candidate records
- Matched signals highlighted
- ML confidence score (Phase 3)
- Accept Merge / Keep Separate — decision feeds back into ML training

---

## 5. Non-Functional Requirements

### Authentication & Multi-User
- JWT-based auth from day 1
- `users` table with `role`: `admin`, `member`
- RBAC introduced in Phase 2
- SSO (SAML/OIDC) in Phase 4

### Open Source
- License: **Apache 2.0**
- One-command self-host: `docker compose up -d`
- Future hosted cloud tier (same codebase, managed infra)

### Data Privacy
- All data stays in the user's own PostgreSQL instance
- No data leaves the server in self-hosted mode
- Passwords hashed with bcrypt

### Performance Targets

| Operation | Target |
|-----------|--------|
| Persons list (1,000 records) | < 200ms |
| Person detail page | < 300ms |
| ER rule-based run (10k records) | < 60s |
| LinkedIn ingestion (500 connections) | < 30s |

---

## 6. Integration with Jager

CDB is a standalone product, but co-exists with Jager in its initial deployment. **CDB is the source of truth for all person and company data.**

Data flows bidirectionally:
- **Jager → CDB**: n8n workflows push raw data after each sync (LinkedIn, Notion, manual uploads)
- **CDB → Jager**: n8n workflows query CDB for enriched person/company context (identity lookups, activity logging, opportunity checks)

Connected via `CDB_API_URL=http://cdb-api:8000` over a shared Docker network — no public internet round-trip.

See [Implementation_plan.md](Implementation_plan.md) for full technical details.

---

## 7. Deployment

- **Self-hosted** on the same VPS as Jager
- Separate Docker Compose stack (`cdb/docker-compose.yml`) joining Jager's Docker network
- Services: `cdb-api`, `cdb-worker` (Celery), `cdb-db` (Postgres on port 5433), `cdb-redis`, `cdb-frontend`
- Optional Nginx routing: `cdb.yourdomain.com` → frontend, `api.cdb.yourdomain.com` → API

---

## 8. Phased Roadmap

| Phase | Focus | Timeline |
|-------|-------|----------|
| **Phase 0** | Repo scaffold, Docker Compose, DB migrations, auth skeleton | Immediate |
| **Phase 1** | Core CRUD API, migrate ingestion from Jager, rule-based ER | Weeks 1–3 |
| **Phase 2** | Frontend MVP (all 4 entity screens + ER Review Queue) | Weeks 3–6 |
| **Phase 3** | ML entity resolution, Gmail integration, Calendar | Weeks 6–10 |
| **Phase 4** | WhatsApp/Facebook, RBAC, Segments, SSO, hosted cloud tier | Ongoing |

---

## 9. Open Questions

| # | Question | Priority |
|---|----------|----------|
| 1 | Frontend framework: Next.js 15 (recommended) or SvelteKit? | High |
| 2 | New repo disk location: `/Users/jimmypang/AntigravityProjects/JagerProjects/CDB/`? | High |
| 3 | Jager decoupling: remove `src/cdp/` immediately after CDB is live, or transition period? | Medium |
| 4 | Should `evaluate_segments.py` move to CDB (Phase 4 Segments) or stay in Jager? | Low |
| 5 | UI component library: shadcn/ui (recommended) or other? | Medium |

---

*This PRD is a living document and will be updated as decisions are made.*
