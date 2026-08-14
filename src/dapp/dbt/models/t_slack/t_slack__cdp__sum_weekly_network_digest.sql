{{ config(
    materialized='table',
    schema='t_slack',
    alias='sum_cdp_weekly_network_digest'
) }}

SELECT
    date_berlin,
    new_leads_count,
    high_signal_leads_count,
    active_pipeline_leads_count,
    new_persons_count,
    new_linkedin_connections_count,
    new_substack_subscribers_count,
    daily_activities_count,
    total_leads_cumulative,
    total_persons_cumulative,
    total_companies_cumulative,
    total_activities_cumulative,
    high_priority_leads,
    daily_activities_json,
    calculated_at_berlin
FROM {{ ref('marts__sum__cdp__weekly_network_digest') }}
WHERE date_berlin >= CURRENT_DATE - INTERVAL '14 days'
ORDER BY date_berlin DESC
