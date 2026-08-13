# Database Schema & Entity Relationship Diagram

This directory contains the database setup and initialization scripts for PostgreSQL database `jager`.

## CDP Schema Entity Relationship Diagram (ERD)

The `cdp` schema is the Customer Data Platform (CDP) processing/domain schema managing entity profiles, lead intake, organizational relationships, and interactions.

For detailed status definitions and stage transition diagrams, see [CDP Status Lifecycle Documentation](../cdp/README.md#status-lifecycles--state-transitions).

```mermaid
erDiagram
    COMPANIES {
        uuid id PK
        string company_name
        string domain UK
        string status "prospect | reached | decision_maker_reached | contract_signed | engaging | completed"
        jsonb attributes
        timestamp_tz created_at
        timestamp_tz updated_at
    }

    PERSONS {
        uuid id PK
        string first_name
        string last_name
        string primary_email UK
        string primary_phone
        string linkedin_url
        string city
        string country
        uuid primary_company_id FK
        string status
        jsonb attributes
        timestamp_tz created_at
        timestamp_tz updated_at
    }

    LEADS {
        uuid id PK
        uuid person_id FK
        string full_name
        text description
        string rate
        string status "prospect | negotiating | offer_accepted | contract_signed | engaging | completed | nurture | disqualified"
        string source
        jsonb raw_payload
        timestamp_tz intake_at
        timestamp_tz updated_at
    }

    PERSON_ACCOUNT_RELATIONSHIPS {
        uuid id PK
        uuid person_id FK
        uuid company_id FK
        string job_title
        string department
        string role_type
        boolean is_primary
        date start_date
        date end_date
        string status
        timestamp_tz created_at
        timestamp_tz updated_at
    }

    ENGAGEMENTS {
        uuid id PK
        uuid person_id FK
        uuid company_id FK
        string engagement_type
        string direction
        string subject
        text summary_or_content
        string channel
        string status
        timestamp_tz occurred_at
        jsonb metadata
        timestamp_tz created_at
        timestamp_tz updated_at
    }

    PERSONS }|--o| COMPANIES : "primary_company_id"
    LEADS }|--o| PERSONS : "person_id"
    LEADS }|--o| COMPANIES : "company_id"
    PERSONS ||--o{ PERSON_ACCOUNT_RELATIONSHIPS : "person_id"
    COMPANIES ||--o{ PERSON_ACCOUNT_RELATIONSHIPS : "company_id"
    PERSONS ||--o{ ENGAGEMENTS : "person_id"
    COMPANIES ||--o{ ENGAGEMENTS : "company_id"
```

## Schema & Tables Overview

- **`cdp.companies`**: Accounts / organizations profiles.
- **`cdp.persons`**: Individual profiles (prospects, leads, contacts) with optional `primary_company_id` foreign key.
- **`cdp.leads_linkedin`**: Intake table for LinkedIn message-derived leads (`s_linkedin.messages`).
- **`cdp.leads_manual`**: Intake table for manual data-derived leads (`s_manual`).
- **`cdp.leads`**: Aggregated table for inbound leads, featuring a `source` column stating if the lead is from `Linkedin` or `Manual`.
- **`cdp.person_account_relationships`**: Dynamic mapping of persons to client accounts with roles (`role_type`, `job_title`, `department`) and date boundaries.
- **`cdp.engagements`**: Activity log (emails, calls, meetings, notes, form submissions, LinkedIn messages).

## Files in `src/db/`
- [init-user-db.sh](init-user-db.sh): PostgreSQL initialization script run automatically on Docker startup.
- [migrate-db.js](migrate-db.js): Database migration and DDL synchronization script.
