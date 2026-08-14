{{ config(
    materialized='table',
    schema='t_jager',
    alias='cdp_companies'
) }}

SELECT
    company_id,
    company_name,
    domain,
    status,
    attributes,
    created_at AT TIME ZONE 'Europe/Berlin' AS created_at_berlin,
    updated_at AT TIME ZONE 'Europe/Berlin' AS updated_at_berlin
FROM {{ ref('marts__cdp__dim_companies') }}
