{{ config(
    materialized='table',
    schema='staging',
    alias='stg_cdp__leads'
) }}

SELECT
  id AS lead_id,
  person_id,
  company_id,
  full_name,
  description,
  message_count,
  summary,
  convo_history,
  intent,
  signal_strength,
  opportunity_type,
  rate,
  status,
  source,
  raw_payload,
  intake_at,
  updated_at,
  lead_status_id,
  lead_status_name,
  lead_status_slug,
  lead_stage_slug,
  lead_stage_name
FROM {{ source('s_cdp', 'leads') }}
