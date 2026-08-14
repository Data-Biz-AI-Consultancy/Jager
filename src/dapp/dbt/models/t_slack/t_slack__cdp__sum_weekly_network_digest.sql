{{ config(
    materialized='table',
    schema='t_slack',
    alias='sum_cdp_weekly_network_digest'
) }}

SELECT *
FROM {{ ref('marts__sum__cdp__weekly_network_digest') }}
WHERE date_berlin >= CURRENT_DATE - INTERVAL '14 days'
ORDER BY date_berlin DESC
