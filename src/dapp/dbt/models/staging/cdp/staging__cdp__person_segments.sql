{{ config(
    materialized='table',
    schema='staging',
    alias='stg_cdp__person_segments'
) }}

SELECT
  id AS person_segment_id,
  slug AS slug,
  name AS name,
  description AS description,
  segment_type AS segment_type,
  potential_opportunity_types AS potential_opportunity_types,
  criteria AS criteria,
  created_at AS created_at,
  updated_at AS updated_at
FROM {{ source('s_cdp', 'person_segments') }}
