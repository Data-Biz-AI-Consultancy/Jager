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

### 3.1 Unified Contact Profile
**As a user, I want a single profile for every person I know, regardless of where I met them or what tool they came from.**

- Search and find any contact by name, email, company, or LinkedIn URL
- See all known contact details (emails, phone, LinkedIn, socials) in one place
- See exactly which sources contributed to this person's record (LinkedIn, Notion, manual import, etc.)
- Edit or enrich a profile manually at any time
- Soft-delete contacts without losing history
- **Automatic deduplication across sources**: CDB recognises when the same person appears in LinkedIn, Notion, and a spreadsheet — and merges them into one record
- Ambiguous matches surface in a **Review Queue** to accept or reject proposed merges side-by-side
- Re-run deduplication at any time without data loss

**Contact sources supported:**

| Source | Mechanism | Phase |
|--------|-----------|-------|
| LinkedIn connections | Upload LinkedIn GDPR export CSV | 1 |
| Any spreadsheet | Upload CSV/XLSX + map columns | 1 |
| Substack subscribers | Upload subscriber export CSV | 2 |
| Gmail contacts | Connect via Google OAuth | 3 |
| Facebook connections | Upload Facebook export ZIP | 4 |

### 3.2 Company Intelligence
**As a user, I want to see all the people I know at a company in one place, so I can understand my relationship with that organisation as a whole.**

- View a company profile with all linked contacts and their current/past roles
- See all activities and opportunities associated with a company, not just individual people
- Manually create companies or have them auto-extracted from person profiles
- Navigate between a person and their company with one click

### 3.3 Full History
**As a user, I want to see the complete history of a person — both my interactions with them and what has happened in their career — so I always have full context.**

#### My interactions with them
- Browse a chronological activity timeline per person or company
- Activities are auto-imported from connected sources (Notion meeting notes, LinkedIn messages, Gmail — future)
- Log manual notes, calls, or meetings directly in CDB
- Filter the global activity feed by type, source, date range, or person

**Activity sources supported:**

| Source | What's captured | Phase |
|--------|----------------|-------|
| Notion meeting notes | Meeting title, date, attendees, summary, to-dos | 1 |
| LinkedIn messages | Message threads and participants | 1 |
| Manual entry | Notes, calls, meetings logged directly in CDB | 1 |
| WhatsApp | Conversation exports | 3 |
| Gmail | Email threads | 3 |
| Google / Outlook Calendar | Meeting events and attendees | 3 |

#### Their personal timeline
- Track a person's career history: previous companies, roles, and dates
- Record when someone changes jobs, gets promoted, or starts a new venture
- See their full employment timeline (past and current roles) on their profile
- Get prompted to re-engage when a key contact changes companies (future: notification trigger)


### 3.4 Lead Management
**As a user, I want to track people who have shown interest or who I'm actively qualifying, so I can manage my pipeline before committing them to a formal opportunity.**

A **Lead** is a Person who has a relevant interest signal — an inbound LinkedIn message, a referral, an inbound inquiry — that hasn't yet been qualified into a specific deal. Leads are the qualification layer between a contact and an opportunity.

**Lead lifecycle:**
```
New → Contacted → Qualified → Converted (→ Opportunity) / Disqualified
```

- Create a lead from any Person profile with one click
- Capture the lead source (LinkedIn message, referral, inbound, event, manual)
- Record intent signals and signal strength (e.g. actively hiring, open to consulting)
- Add notes on qualification progress
- Convert a qualified lead directly into an Opportunity — person and company are carried over
- Disqualify with a reason (wrong timing, wrong fit, no budget, etc.)
- View all leads in a list filterable by stage, source, and owner

> **Leads vs. Opportunities**: A Lead is about *qualifying a person's interest*. An Opportunity is about *pursuing a specific, named deal*. One person can have multiple leads over time, and a lead can convert into one or more opportunities.

### 3.5 Opportunity Pipeline
**As a user, I want to track deals, partnerships, and collaborations through a clear pipeline, so I always know what needs action.**

- Visualise all opportunities in a Kanban board (stages: prospect → qualified → proposal → negotiation → closed)
- Link each opportunity to one or more persons and companies
- Add value, probability, and expected close date
- Advance stages by dragging cards or from person/company detail pages
- Assign opportunities to team members (multi-user)
- Create opportunities manually or by converting a qualified Lead


---

## 4. Key UX Screens

### 👤 People

#### Persons List
- Full-text search (name, email, company)
- Filter: source, country, has open opportunity, has open lead
- Sortable columns: name, last activity, created date
- Slide-in quick-view panel on row click
- Source badges per row (LinkedIn, Notion, manual, etc.)

#### Person Detail
- Header: avatar, name, current title + company
- Contact info: email, phone, LinkedIn, social handles
- Source attribution badges
- **Career timeline**: full employment history (current + past roles with dates)
- **Interaction timeline**: chronological feed of all activities with this person
- Linked leads and open opportunities mini-view
- Deduplication Review Queue entry (if flagged as a potential duplicate)

---

### 🏢 Companies

#### Companies List
- Search by name or domain
- Filter by industry, country, size
- Columns: name, domain, # of known contacts, # of open opportunities

#### Company Detail
- Header: company name, domain, industry, size, location
- **Linked Persons**: table of all contacts with role and is_current
- **Interaction timeline**: activities associated with this company
- Linked leads and open opportunities

---

### 📋 Activities

#### Activities Feed
- Global chronological feed across all persons and companies
- Filter by type (meeting, email, message, call, note), source, date range, person, company
- Click-through to the associated person or company record

---

### 🎯 Leads

#### Leads List
- Filter by stage (new, contacted, qualified, converted, disqualified), source, owner
- Columns: person name, company, stage, source, last updated
- Quick-convert to Opportunity from the list view

#### Lead Detail
- Linked person and company
- Stage progression tracker
- Intent signals and signal strength
- Activity thread for this lead (calls, notes, messages)
- Convert to Opportunity / Disqualify actions

---

### 💼 Opportunities

#### Opportunities Pipeline
- Kanban board with columns per stage (prospect → qualified → proposal → negotiation → closed)
- Card: person name, company, value, expected close date
- Drag-to-advance stage
- Quick-add from any person, company, or lead

#### Opportunity Detail
- Linked persons and companies (with their roles in this deal)
- Stage history log
- Related activities and notes

---

### ⚙️ System

#### Entity Resolution Review Queue
- Side-by-side comparison of two candidate person records
- Matched signals highlighted (email, LinkedIn URL, name, company)
- ML confidence score (Phase 3)
- Accept Merge / Keep Separate actions — decision feeds back into ML training

#### Settings
- Connected sources (Notion API key, Gmail OAuth — future)
- Users and roles (Phase 2+)
- Data export (full JSON/CSV)


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

- **CDB repo** publishes a Docker image to **GitHub Container Registry (GHCR)** on every merge to `main` via GitHub Actions, tagged as `ghcr.io/data-biz-ai-consultancy/cdb:production`
- **Jager's `docker-compose.yml`** adds `cdb-api` and `cdb-db` services that pull this image directly — no separate compose file, no cross-stack network complexity
- Both `cdb-api` and `cdb-db` join Jager's existing Docker network, so n8n reaches CDB at `http://cdb-api:8000`
- `cdb-db` runs on host port `5433` to avoid collision with Jager's Postgres on `5432`
- **To upgrade**: `docker compose pull cdb-api && docker compose up -d cdb-api`

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
