{{ config(
    materialized='table',
    schema='staging',
    alias='stg_cdp__person_segments'
) }}

SELECT
  id AS person_segment_id,
  slug,
  name,
  description,
  segment_type,
  potential_opportunity_types,
  criteria,
  created_at,
  updated_at
FROM {{ source('s_cdp', 'person_segments') }}
