# CDB — API Specification

**Version**: v1 (Draft)
**Status**: Under Review
**Last Updated**: 2026-08-20
**Base URL**: `http://cdb-api:8000/api/v1` (internal); `https://api.cdb.yourdomain.com/api/v1` (external)

---

## 1. Conventions

### 1.1 Versioning

All endpoints are prefixed with `/api/v1/`. Breaking changes bump the version prefix.

### 1.2 Authentication

All endpoints require a Bearer JWT except `/auth/login` and `/auth/register`.

```
Authorization: Bearer <access_token>
```

Token shape:
```json
{
  "sub": "<user_uuid>",
  "role": "admin | member",
  "exp": 1234567890
}
```

| Parameter | Value |
|-----------|-------|
| Algorithm | HS256 |
| Access token TTL | 60 minutes |
| Refresh token TTL | 30 days |

Refresh via `POST /auth/refresh` with the refresh token in an `HttpOnly` cookie.

### 1.3 Pagination

All list endpoints support cursor-based pagination.

**Request query params:**
```
?limit=50          # default 50, max 200
?cursor=<opaque>   # omit for first page
?sort=created_at   # column to sort by
?order=desc        # asc | desc
```

**Response envelope (list):**
```json
{
  "data": [ ... ],
  "pagination": {
    "next_cursor": "<opaque_string_or_null>",
    "has_more": true,
    "total": 1243
  }
}
```

### 1.4 Error Envelope

All errors return a consistent body:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Person with id abc123 not found.",
    "details": {}
  }
}
```

| HTTP Status | `code` | When |
|-------------|--------|------|
| 400 | `VALIDATION_ERROR` | Request body fails validation |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT |
| 403 | `FORBIDDEN` | Authenticated but insufficient role |
| 404 | `NOT_FOUND` | Resource doesn't exist |
| 409 | `CONFLICT` | Duplicate unique field (e.g. email already exists) |
| 422 | `UNPROCESSABLE` | Semantically invalid input |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## 2. Auth

### `POST /auth/login`
```json
// Request
{ "email": "alice@example.com", "password": "secret" }

// Response 200
{
  "access_token": "<jwt>",
  "token_type": "Bearer",
  "user": { "id": "<uuid>", "email": "alice@example.com", "role": "admin" }
}
```

### `POST /auth/refresh`
Reads `refresh_token` from HttpOnly cookie; returns new `access_token`.

### `POST /auth/logout`
Invalidates the refresh token.

---

## 3. Persons

### `GET /persons`

List all persons (paginated, soft-deleted excluded by default).

**Query params:** `q` (full-text search), `source` (filter by source), `country`, `has_open_opportunity` (bool), `has_open_lead` (bool), `include_deleted` (bool, admin only).

**Response 200:**
```json
{
  "data": [
    {
      "id": "<uuid>",
      "first_name": "Alice",
      "last_name": "Smith",
      "primary_email": "alice@acme.com",
      "linkedin_url": "linkedin.com/in/alice-smith",
      "current_company": { "id": "<uuid>", "name": "Acme Corp" },
      "current_title": "VP Engineering",
      "sources": ["linkedin", "notion"],
      "last_activity_at": "2026-07-15T10:00:00Z",
      "created_at": "2026-01-10T08:00:00Z"
    }
  ],
  "pagination": { ... }
}
```

### `POST /persons`

Create a person manually.

```json
// Request
{
  "first_name": "Alice",
  "last_name": "Smith",
  "primary_email": "alice@acme.com",
  "linkedin_url": "https://linkedin.com/in/alice-smith",
  "primary_phone": "+44 7911 000000",
  "city": "London",
  "country": "GB"
}

// Response 201 — full person object
```

### `GET /persons/{id}`

Full person detail including career timeline and linked leads/opportunities.

```json
{
  "id": "<uuid>",
  "first_name": "Alice",
  "last_name": "Smith",
  "primary_email": "alice@acme.com",
  "secondary_emails": ["asmith@old.com"],
  "linkedin_url": "linkedin.com/in/alice-smith",
  "primary_phone": "+44...",
  "city": "London",
  "country": "GB",
  "avatar_url": null,
  "sources": ["linkedin", "notion"],
  "source_ids": { "linkedin": "ACoAA..." },
  "attributes": {},
  "career": [
    {
      "company": { "id": "<uuid>", "name": "Acme Corp" },
      "title": "VP Engineering",
      "is_current": true,
      "started_at": "2023-03-01",
      "ended_at": null
    }
  ],
  "open_leads_count": 1,
  "open_opportunities_count": 2,
  "created_at": "2026-01-10T08:00:00Z",
  "updated_at": "2026-07-01T12:00:00Z"
}
```

### `PATCH /persons/{id}`

Partial update of any mutable field. Immutable: `id`, `sources`, `source_ids`, `created_at`.

### `DELETE /persons/{id}`

Soft-delete (sets `deleted_at`). Use `DELETE /persons/{id}?hard=true` (admin only) for permanent deletion.

---

## 4. Companies

### `GET /companies`

**Query params:** `q`, `country`, `industry`.

**Response 200:** paginated list with `{ id, name, domain, industry, country, contacts_count, open_opportunities_count }`.

### `POST /companies`

```json
{ "name": "Acme Corp", "domain": "acme.com", "industry": "Technology", "country": "GB" }
```

### `GET /companies/{id}`

Full detail including linked persons (with current role) and open opportunities.

### `PATCH /companies/{id}` / `DELETE /companies/{id}`

Same conventions as persons.

---

## 5. Person-Company Relationships

### `POST /persons/{person_id}/companies`

Add or update a role at a company.

```json
{
  "company_id": "<uuid>",
  "title": "CTO",
  "is_current": true,
  "started_at": "2023-01-01"
}
```

### `PATCH /persons/{person_id}/companies/{company_id}`

Update `title`, `is_current`, `ended_at`.

### `DELETE /persons/{person_id}/companies/{company_id}`

Removes the relationship row (not the company).

---

## 6. Activities

### `GET /activities`

**Query params:** `person_id`, `company_id`, `type`, `source`, `from` (ISO date), `to` (ISO date).

**Response 200:** paginated list ordered by `occurred_at DESC`.

### `POST /activities`

Create a manual activity.

```json
{
  "person_id": "<uuid>",
  "company_id": null,
  "type": "call",
  "source": "manual",
  "occurred_at": "2026-08-19T14:00:00Z",
  "title": "Discovery call",
  "summary": "Discussed consulting scope. Follow up in 2 weeks."
}
```

### `GET /activities/{id}` / `PATCH /activities/{id}` / `DELETE /activities/{id}`

Standard CRUD. `source_id`-tagged activities (auto-imported) can be patched but not deleted.

---

## 7. Leads

### `GET /leads`

**Query params:** `stage`, `source`, `owner_id`, `person_id`, `company_id`.

### `POST /leads`

```json
{
  "person_id": "<uuid>",
  "company_id": "<uuid>",
  "source": "linkedin_message",
  "source_ref_id": "conversation:abc123",
  "intent": "open to consulting",
  "signal_strength": "strong",
  "notes": "Reached out after my post on async work."
}
```

### `GET /leads/{id}` / `PATCH /leads/{id}`

### `POST /leads/{id}/advance`

Move lead to next stage.

```json
// Request — optional notes
{ "notes": "Confirmed budget available." }

// Response 200 — updated lead with new stage
```

### `POST /leads/{id}/disqualify`

```json
{ "reason": "no_budget" }
```

### `POST /leads/{id}/convert`

Convert a qualified lead into an Opportunity.

```json
// Request
{ "title": "Consulting engagement — Acme Corp Q3 2026" }

// Response 201 — new opportunity object
// Also sets lead.stage = 'converted' and lead.converted_opportunity_id
```

---

## 8. Opportunities

### `GET /opportunities`

**Query params:** `stage`, `owner_id`, `person_id`, `company_id`.

### `POST /opportunities`

```json
{
  "title": "Consulting engagement — Acme Corp Q3",
  "stage": "prospect",
  "value": 15000,
  "currency": "EUR",
  "probability": 60,
  "expected_close_date": "2026-09-30",
  "person_ids": [{ "person_id": "<uuid>", "role": "decision_maker" }],
  "company_ids": [{ "company_id": "<uuid>", "role": "client" }]
}
```

### `GET /opportunities/{id}` / `PATCH /opportunities/{id}` / `DELETE /opportunities/{id}`

### `POST /opportunities/{id}/advance`

Advance to next stage.

### `POST /opportunities/{id}/close`

```json
{ "outcome": "closed_won" }   // or "closed_lost"
```

---

## 9. Entity Resolution

### `GET /entity-resolution/queue`

List pending candidate pairs.

**Query params:** `status` (default `pending`), `min_score` (float, Phase 3).

**Response 200:**
```json
{
  "data": [
    {
      "id": "<uuid>",
      "person_a": { "id": "<uuid>", "first_name": "Alice", "last_name": "Smith", "primary_email": "alice@acme.com", "sources": ["linkedin"] },
      "person_b": { "id": "<uuid>", "first_name": "Alice", "last_name": "Smyth", "primary_email": null, "sources": ["notion"] },
      "match_signals": { "name_similarity": 0.96, "company_domain_match": true, "trigger_rule": 6 },
      "ml_score": null,
      "status": "pending",
      "created_at": "2026-08-19T09:00:00Z"
    }
  ],
  "pagination": { ... }
}
```

### `POST /entity-resolution/queue/{id}/accept`

Accepts the merge. Person B is merged into Person A (older record wins).

**Response 200:** `{ "master_person_id": "<uuid>", "merged_person_id": "<uuid>" }`

### `POST /entity-resolution/queue/{id}/reject`

**Response 200:** `{ "status": "rejected" }`

### `POST /entity-resolution/run`

Trigger a full ER re-run (admin only, async — returns job ID).

```json
// Response 202
{ "job_id": "<uuid>", "status": "queued" }
```

---

## 10. Ingestion (Internal — Jager use)

These endpoints are called by Jager's n8n workflows. They require a service-to-service API key header instead of a user JWT:

```
X-API-Key: <service_token>
```

### `POST /ingest/linkedin-connections`

Idempotent batch upsert into `intake_linkedin_connections`. Triggers incremental ER run.

```json
{
  "records": [
    {
      "connection_id": "ACoAA...",
      "first_name": "Bob",
      "last_name": "Jones",
      "profile_url": "https://linkedin.com/in/bob-jones",
      "email_address": "bob@example.com",
      "company": "Acme",
      "position": "CEO",
      "connected_at": "2025-06-01T00:00:00Z"
    }
  ]
}
// Response 202: { "queued": 42, "duplicates_skipped": 3 }
```

### `POST /ingest/linkedin-messages`

Idempotent batch upsert into `intake_linkedin_messages`.

### `POST /ingest/notion-meeting-notes`

Idempotent batch upsert into `intake_notion_meeting_notes`.

### `POST /ingest/manual`

Upload a CSV/XLSX batch. Multipart form:
- `file`: the uploaded file
- `source_label`: string label for the batch (e.g. `"Substack export 2026-07"`)
- `entity_type`: `person | company`
- `column_map`: JSON string mapping source columns to CDB fields

---

*See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for field definitions and [ENTITY_RESOLUTION_SPEC.md](ENTITY_RESOLUTION_SPEC.md) for ER logic.*
