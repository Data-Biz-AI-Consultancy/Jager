{{ config(
    materialized='table',
    schema='t_slack',
    alias='cdp_activities'
) }}

SELECT * FROM {{ ref('marts__cdp__fct_activities') }}
