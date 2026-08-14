{{ config(
    materialized='table',
    schema='t_slack',
    alias='cdp_persons'
) }}

SELECT * FROM {{ ref('marts__cdp__dim_persons') }}
