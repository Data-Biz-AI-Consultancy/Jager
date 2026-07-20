{{ config(
    materialized='table',
    schema='t_reporting',
    alias='content_marketing_daily_performance'
) }}

SELECT * FROM {{ ref('marts__sum__content_marketing__daily_performance') }}
