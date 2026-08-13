{{ config(
    materialized='table',
    schema='staging',
    alias='stg_cdp__leads'
) }}

SELECT
  id AS lead_id,
  person_id AS person_id,
  company_id AS company_id,
  full_name AS full_name,
  description AS description,
  message_count AS message_count,
  summary AS summary,
  convo_history AS convo_history,
  intent AS intent,
  signal_strength AS signal_strength,
  opportunity_type AS opportunity_type,
  rate AS rate,
  status AS status,
  source AS source,
  raw_payload AS raw_payload,
  intake_at AS intake_at,
  updated_at AS updated_at,
  lead_status_id AS lead_status_id,
  lead_status_name AS lead_status_name,
  lead_status_slug AS lead_status_slug,
  lead_stage_slug AS lead_stage_slug,
  lead_stage_name AS lead_stage_name
FROM {{ source('s_cdp', 'leads') }}
