{{ config(
    materialized='table',
    schema='staging',
    alias='stg_cdp__person_company_relationships'
) }}

SELECT
  id AS relationship_id,
  person_id AS person_id,
  company_id AS company_id,
  job_title AS job_title,
  department AS department,
  role_type AS role_type,
  is_primary AS is_primary,
  start_date AS start_date,
  end_date AS end_date,
  status AS status,
  created_at AS created_at,
  updated_at AS updated_at
FROM {{ source('s_cdp', 'person_company_relationships') }}
