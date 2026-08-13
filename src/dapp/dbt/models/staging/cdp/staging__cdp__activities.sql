{{ config(
    materialized='table',
    schema='staging',
    alias='stg_cdp__activities'
) }}

SELECT
  id AS activity_id,
  activity_type,
  source,
  source_id,
  person_id,
  company_id,
  title,
  activity_date,
  summary_or_content,
  to_dos,
  participants,
  url,
  metadata,
  created_at,
  updated_at
FROM {{ source('s_cdp', 'activities') }}
