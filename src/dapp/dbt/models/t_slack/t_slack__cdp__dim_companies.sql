{{ config(
    materialized='table',
    schema='t_slack',
    alias='cdp_companies'
) }}

SELECT * FROM {{ ref('marts__cdp__dim_companies') }}
