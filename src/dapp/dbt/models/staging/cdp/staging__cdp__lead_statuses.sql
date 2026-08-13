{{ config(
    materialized='table',
    schema='staging',
    alias='stg_cdp__lead_statuses'
) }}

SELECT
  id AS lead_status_id,
  slug AS slug,
  name AS name,
  stage AS stage,
  is_end_state AS is_end_state,
  description AS description,
  criteria AS criteria,
  created_at AS created_at,
  updated_at AS updated_at
FROM {{ source('s_cdp', 'lead_statuses') }}
