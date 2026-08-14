{{ config(
    materialized='table',
    schema='t_slack',
    alias='cdp_leads'
) }}

SELECT * FROM {{ ref('marts__cdp__fct_leads') }}
