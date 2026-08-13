{{ config(
    materialized='view',
    schema='staging',
    alias='stg_cdp__activities'
) }}

SELECT
  id AS activity_id,
  activity_type AS activity_type,
  source AS source,
  source_id AS source_id,
  person_id AS person_id,
  company_id AS company_id,
  title AS title,
  activity_date AS activity_date,
  summary_or_content AS summary_or_content,
  to_dos AS to_dos,
  participants AS participants,
  url AS url,
  metadata AS metadata,
  created_at AS created_at,
  updated_at AS updated_at
FROM {{ source('s_cdp', 'activities') }}
