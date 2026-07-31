{{ config(
    materialized='table',
    schema='t_jager',
    alias='sum_content_marketing_daily_performance'
) }}

SELECT * FROM {{ ref('marts__sum__content_marketing__daily_performance') }}
