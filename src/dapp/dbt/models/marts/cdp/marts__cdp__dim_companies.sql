{{ config(
    materialized='table',
    schema='marts',
    alias='dim_cdp_companies'
) }}

SELECT
  companies.company_id AS company_id,
  companies.company_name AS company_name,
  companies.domain AS domain,
  companies.status AS status,
  companies.attributes AS attributes,
  companies.created_at AS created_at,
  companies.updated_at AS updated_at
FROM {{ ref('staging__cdp__companies') }} AS companies
