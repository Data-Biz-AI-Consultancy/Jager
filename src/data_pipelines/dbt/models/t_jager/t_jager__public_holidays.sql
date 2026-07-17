{{ config(
    materialized='table',
    schema='t_jager',
    alias='public_holidays'
) }}

SELECT * FROM {{ ref('marts__public_holidays') }}
