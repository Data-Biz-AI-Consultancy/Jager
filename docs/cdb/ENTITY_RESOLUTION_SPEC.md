# CDB — Entity Resolution Specification

**Version**: 0.1 (Draft)
**Status**: Under Review
**Last Updated**: 2026-08-20

> This spec is the authoritative reference for CDB's Entity Resolution (ER) engine. It defines the exact normalisation rules, matching signal hierarchy, merge precedence, and test cases that govern how intake records are merged into master `persons` records. All ER code must conform to this document.

---

## 1. Overview

Entity Resolution (ER) answers one question: **are record A and record B the same real-world person?**

CDB uses a **hybrid approach**:
1. **Rule-based matching** (Phase 1) — deterministic, fast, no training data required
2. **ML-based scoring** (Phase 3) — probabilistic fallback for ambiguous pairs

All ER output is one of three outcomes:

| Outcome | Condition | Action |
|---------|-----------|--------|
| **Auto-merge** | High-confidence rule match | Merge immediately; no user review |
| **Review queue** | Low-confidence / ambiguous | Create `er_candidate_pairs` row; await user decision |
| **No match** | No signal overlap | Treat as distinct persons |

---

## 2. Normalisation Functions

All signals are normalised before comparison. These functions must be implemented identically in the rule engine and in any ML feature extraction pipeline.

### 2.1 `normalise_email(raw)`

```python
def normalise_email(raw: str | None) -> str | None:
    if not raw:
        return None
    email = raw.strip().lower()
    # Reject known placeholder / invalid emails
    if "@linkedin.user" in email or "invalid" in email or "@" not in email:
        return None
    return email
```

### 2.2 `normalise_linkedin_url(raw)`

```python
import re

def normalise_linkedin_url(raw: str | None) -> str | None:
    if not raw:
        return None
    url = raw.strip()
    # Strip scheme and www, strip trailing slash
    url = re.sub(r'^https?://(www\.)?', '', url).rstrip('/')
    # Must look like a LinkedIn profile path
    if not url.startswith('linkedin.com/in/'):
        return None
    return url.lower()
```

### 2.3 `normalise_phone(raw)`

```python
import re

def normalise_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    # Strip all non-digit characters except leading +
    digits = re.sub(r'[^\d+]', '', raw.strip())
    if len(digits) < 7:
        return None
    return digits
```

### 2.4 `normalise_name(raw)`

```python
def normalise_name(raw: str | None) -> str | None:
    if not raw:
        return None
    return raw.strip().lower()
```

### 2.5 `email_prefix(email)`

Returns the local part of an email, stripped of trailing digits, if ≥ 5 characters.

```python
def email_prefix(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    local = email.split("@")[0].lower()
    stripped = re.sub(r'\d+$', '', local)
    return stripped if len(stripped) >= 5 else None
```

---

## 3. Rule-Based Matching

### 3.1 Signal Hierarchy

Rules are evaluated top-to-bottom. The **first matching rule** determines the outcome. Rules do not stack.

| Priority | Signal | Condition | Confidence | Outcome |
|----------|--------|-----------|------------|---------|
| 1 | Email exact match | `normalise_email(A) == normalise_email(B)` | **High** | Auto-merge |
| 2 | LinkedIn URL exact match | `normalise_linkedin_url(A) == normalise_linkedin_url(B)` | **High** | Auto-merge |
| 3 | Phone exact match | `normalise_phone(A) == normalise_phone(B)` | **High** | Auto-merge |
| 4 | Email prefix + full name | Same prefix (≥5 chars) **and** `jaro_winkler(full_name_A, full_name_B) ≥ 0.95` | **Medium** | Auto-merge |
| 5 | Full name + company domain | `jaro_winkler(full_name_A, full_name_B) ≥ 0.92` **and** same company domain | **Medium** | Auto-merge |
| 6 | Full name only | `jaro_winkler(full_name_A, full_name_B) ≥ 0.95` | **Low** | Review queue |
| — | No match | None of the above | — | No match |

> **Jaro-Winkler**: Use `jellyfish.jaro_winkler_similarity()`. Always compute on the concatenated `first_name + ' ' + last_name` string after `normalise_name()`.

### 3.2 Blocking Strategy

To avoid O(n²) comparisons, intake records are only compared against master `persons` within the same **block**. A block is defined as sharing at least one of:

- Same email prefix (≥ 5 chars)
- Same first 3 characters of normalised last name
- Same normalised LinkedIn URL domain path prefix (first segment after `/in/`)

Records with no blocking key are compared name-only as a final pass.

---

## 4. Merge Strategy (Field Precedence)

When two records are merged, the **master record** (the `persons` row) is updated using this precedence order. The winning source is always the one with the higher-priority signal for that field.

| Field | Precedence |
|-------|-----------|
| `first_name` | Prefer longer/compound name (e.g. "Pui Man" > "Pui"); then prefer LinkedIn > Notion > manual |
| `last_name` | Same as `first_name` |
| `primary_email` | Prefer existing `primary_email`; move new email to `secondary_emails` |
| `primary_phone` | Prefer non-null; if both non-null, prefer LinkedIn source |
| `linkedin_url` | Prefer normalised URL; keep only one |
| `city`, `country` | Prefer LinkedIn > manual > Notion |
| `avatar_url` | Keep existing; do not overwrite |
| `attributes` | Deep merge (new keys added, existing keys not overwritten) |
| `sources` | Union of both source arrays |
| `source_ids` | Merge JSONB dicts (new keys added, existing not overwritten) |

### 4.1 FK Re-linking on Merge

When record B is merged into record A (A becomes master, B is deleted), all FK references to B must be updated to A **before** B is deleted:

```sql
UPDATE activities          SET person_id = :master_id WHERE person_id = :dup_id;
UPDATE leads               SET person_id = :master_id WHERE person_id = :dup_id;
UPDATE opportunity_persons SET person_id = :master_id WHERE person_id = :dup_id;
UPDATE person_company_relationships SET person_id = :master_id WHERE person_id = :dup_id;
UPDATE er_candidate_pairs  SET person_a_id = :master_id WHERE person_a_id = :dup_id;
UPDATE er_candidate_pairs  SET person_b_id = :master_id WHERE person_b_id = :dup_id;
DELETE FROM persons WHERE id = :dup_id;
```

> All FK updates and the DELETE must run in a single transaction.

### 4.2 Choosing the Master Record

When two records match, the master is chosen by:
1. **Older `created_at`** (the earlier record is the master)
2. If tied: prefer the record with more non-null fields

---

## 5. Review Queue

Ambiguous matches (rule priority 6, or ML score 0.5–0.85 in Phase 3) are written to `er_candidate_pairs` with `status = 'pending'`.

### 5.1 `er_candidate_pairs` row structure

```json
{
  "person_a_id": "<uuid>",
  "person_b_id": "<uuid>",
  "match_signals": {
    "name_similarity": 0.96,
    "email_prefix_match": false,
    "company_domain_match": true,
    "linkedin_url_match": false,
    "trigger_rule": 6
  },
  "ml_score": null,
  "status": "pending"
}
```

### 5.2 User Actions

| Action | Endpoint | Effect |
|--------|----------|--------|
| Accept merge | `POST /api/v1/entity-resolution/queue/{id}/accept` | Runs FK re-link + DELETE on losing record; sets `status = 'accepted'` |
| Reject | `POST /api/v1/entity-resolution/queue/{id}/reject` | Sets `status = 'rejected'`; pair is never surfaced again |

### 5.3 Preventing Duplicate Pairs

Before inserting a new candidate pair, check:
```sql
SELECT 1 FROM er_candidate_pairs
WHERE (person_a_id = :a AND person_b_id = :b)
   OR (person_a_id = :b AND person_b_id = :a)
   AND status != 'rejected';
```
Do not insert if a non-rejected pair already exists for this combination.

---

## 6. ER Run Modes

| Mode | Trigger | Scope |
|------|---------|-------|
| **Incremental** | After each ingestion job completes | Only newly ingested intake records |
| **Full re-run** | `POST /api/v1/entity-resolution/run` | All `pending` intake records |
| **Post-merge deduplication** | After any accepted Review Queue merge | Scan for remaining duplicates of the newly merged master |

---

## 7. Module Structure

The ER engine is split into three modules under `backend/app/services/entity_resolution/`:

| Module | Responsibility |
|--------|---------------|
| `normalise.py` | All normalisation functions (Section 2) |
| `rules.py` | Signal evaluation, blocking, auto-merge decisions (Section 3) |
| `merger.py` | FK re-linking, field merge precedence, master selection (Sections 4–5) |
| `ml_scorer.py` *(Phase 3)* | Feature extraction, model inference, confidence scoring |

---

## 8. Test Cases

All test cases live in `tests/cdb/entity_resolution/`.

### 8.1 Normalisation

| Input | Function | Expected output |
|-------|----------|----------------|
| `"  Alice@Example.COM  "` | `normalise_email` | `"alice@example.com"` |
| `"fake@linkedin.user"` | `normalise_email` | `None` |
| `"https://www.linkedin.com/in/alice-smith/"` | `normalise_linkedin_url` | `"linkedin.com/in/alice-smith"` |
| `"+44 (0) 7911 123456"` | `normalise_phone` | `"+44079111234567"` |
| `"alice123"` | `email_prefix` | `"alice"` (5 chars ✓) |
| `"al123"` | `email_prefix` | `None` (< 5 chars after stripping) |

### 8.2 Auto-Merge Cases

| Scenario | Record A | Record B | Expected |
|----------|----------|----------|----------|
| Email match | `alice@acme.com` | `alice@acme.com` | Auto-merge (rule 1) |
| LinkedIn match | `linkedin.com/in/alice` | `https://linkedin.com/in/alice/` | Auto-merge (rule 2) |
| Email prefix + name | `al.smith@acme.com` / Alice Smith | `alsmith@other.com` / Alice Smith | Auto-merge (rule 4) |
| Name + company | Alice Smith @ acme.com | Alice Smith @ acme.com | Auto-merge (rule 5) |

### 8.3 Review Queue Cases

| Scenario | Record A | Record B | Expected |
|----------|----------|----------|----------|
| Name only, high similarity | Alice Smith | Alicia Smith | Review queue (rule 6) |
| Name only, low similarity | Alice Smith | Bob Jones | No match |

### 8.4 No-Match Cases

| Scenario | Record A | Record B | Expected |
|----------|----------|----------|----------|
| Different emails, no name | `alice@acme.com` | `bob@acme.com` | No match |
| Same company, different names | Alice Smith @ acme | Bob Jones @ acme | No match |

### 8.5 Merge Precedence Cases

| Scenario | Expected |
|----------|----------|
| A has `first_name = "Pui"`, B has `first_name = "Pui Man"` | Master gets `"Pui Man"` |
| A has `primary_email`, B has different email | A keeps primary; B's email added to `secondary_emails` |
| Both have `country`, A = LinkedIn, B = manual | A's `country` wins |
