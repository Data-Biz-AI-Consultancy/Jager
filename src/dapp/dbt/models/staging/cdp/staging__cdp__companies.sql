{{ config(
    materialized='view',
    schema='staging',
    alias='stg_cdp__companies'
) }}

SELECT
  id AS company_id,
  company_name AS company_name,
  domain AS domain,
  status AS status,
  attributes AS attributes,
  created_at AS created_at,
  updated_at AS updated_at
FROM {{ source('s_cdp', 'companies') }}
