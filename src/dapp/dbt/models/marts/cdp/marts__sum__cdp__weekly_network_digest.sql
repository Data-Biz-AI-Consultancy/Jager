{{ config(
    materialized='table',
    schema='marts',
    alias='sum_cdp_weekly_network_digest'
) }}

WITH leads AS (
    SELECT
        lead_id,
        person_id,
        company_id,
        full_name,
        intent,
        signal_strength,
        opportunity_type,
        status,
        lead_stage_name,
        lead_stage_slug,
        summary,
        CAST(intake_at AT TIME ZONE 'UTC' AS DATE) AS date_utc,
        CAST(intake_at AT TIME ZONE 'Europe/Berlin' AS DATE) AS date_berlin
    FROM {{ ref('marts__cdp__fct_leads') }}
),

activities AS (
    SELECT
        activity_id,
        title,
        activity_type,
        summary_or_content,
        to_dos,
        CAST(activity_date AS DATE) AS date_utc,
        CAST(activity_date AT TIME ZONE 'Europe/Berlin' AS DATE) AS date_berlin
    FROM {{ ref('marts__cdp__fct_activities') }}
),

persons AS (
    SELECT
        person_id,
        in_linkedin_connections,
        in_substack_subscriber_export,
        engagement_temperature,
        CAST(created_at AT TIME ZONE 'UTC' AS DATE) AS date_utc,
        CAST(created_at AT TIME ZONE 'Europe/Berlin' AS DATE) AS date_berlin
    FROM {{ ref('marts__cdp__dim_persons') }}
),

date_spine AS (
    SELECT DISTINCT date_utc, date_berlin FROM activities WHERE date_utc IS NOT NULL
    UNION
    SELECT DISTINCT date_utc, date_berlin FROM leads WHERE date_utc IS NOT NULL
    UNION
    SELECT DISTINCT date_utc, date_berlin FROM persons WHERE date_utc IS NOT NULL
    UNION
    SELECT (CURRENT_DATE AT TIME ZONE 'UTC')::DATE AS date_utc, (CURRENT_DATE AT TIME ZONE 'Europe/Berlin')::DATE AS date_berlin
),

daily_leads AS (
    SELECT
        date_utc,
        COUNT(*) AS new_leads_count,
        COUNT(CASE WHEN UPPER(COALESCE(signal_strength, '')) IN ('HIGH', 'HOT', 'STRONG') THEN 1 END) AS high_signal_leads_count,
        COUNT(CASE WHEN UPPER(COALESCE(lead_stage_slug, '')) IN ('NEW', 'QUALIFIED', 'PROSPECT') THEN 1 END) AS active_pipeline_leads_count
    FROM leads
    GROUP BY date_utc
),

daily_activities AS (
    SELECT
        date_utc,
        COUNT(*) AS activities_count,
        COALESCE(
            to_json(list({
                'activity_id': activity_id,
                'title': title,
                'activity_type': activity_type,
                'summary_or_content': summary_or_content,
                'to_dos': to_dos
            })),
            to_json([])
        ) AS daily_activities_json
    FROM activities
    GROUP BY date_utc
),

daily_persons AS (
    SELECT
        date_utc,
        COUNT(*) AS new_persons_count,
        COUNT(CASE WHEN in_linkedin_connections = TRUE THEN 1 END) AS new_linkedin_connections_count,
        COUNT(CASE WHEN in_substack_subscriber_export = TRUE THEN 1 END) AS new_substack_subscribers_count
    FROM persons
    GROUP BY date_utc
),

cumulative_totals AS (
    SELECT
        (SELECT COUNT(*) FROM {{ ref('marts__cdp__fct_leads') }}) AS total_leads_cumulative,
        (SELECT COUNT(*) FROM {{ ref('marts__cdp__dim_persons') }}) AS total_persons_cumulative,
        (SELECT COUNT(*) FROM {{ ref('marts__cdp__dim_companies') }}) AS total_companies_cumulative,
        (SELECT COUNT(*) FROM {{ ref('marts__cdp__fct_activities') }}) AS total_activities_cumulative
),

high_priority_leads_json AS (
    SELECT
        COALESCE(
            to_json(list({
                'lead_id': lead_id,
                'full_name': full_name,
                'intent': intent,
                'signal_strength': signal_strength,
                'opportunity_type': opportunity_type,
                'status': status,
                'lead_stage_name': lead_stage_name,
                'summary': summary,
                'intake_date_utc': date_utc,
                'intake_date_berlin': date_berlin
            })),
            to_json([])
        ) AS high_priority_leads
    FROM leads
    WHERE UPPER(COALESCE(signal_strength, '')) IN ('HIGH', 'HOT', 'STRONG')
       OR UPPER(COALESCE(lead_stage_slug, '')) IN ('NEW', 'QUALIFIED', 'PROSPECT')
)

SELECT
    ds.date_utc,
    ds.date_berlin,
    COALESCE(dl.new_leads_count, 0) AS new_leads_count,
    COALESCE(dl.high_signal_leads_count, 0) AS high_signal_leads_count,
    COALESCE(dl.active_pipeline_leads_count, 0) AS active_pipeline_leads_count,
    COALESCE(dp.new_persons_count, 0) AS new_persons_count,
    COALESCE(dp.new_linkedin_connections_count, 0) AS new_linkedin_connections_count,
    COALESCE(dp.new_substack_subscribers_count, 0) AS new_substack_subscribers_count,
    COALESCE(da.activities_count, 0) AS daily_activities_count,
    ct.total_leads_cumulative,
    ct.total_persons_cumulative,
    ct.total_companies_cumulative,
    ct.total_activities_cumulative,
    hpl.high_priority_leads,
    COALESCE(da.daily_activities_json, to_json([])) AS daily_activities_json,
    NOW() AT TIME ZONE 'UTC' AS calculated_at_utc,
    NOW() AT TIME ZONE 'Europe/Berlin' AS calculated_at_berlin
FROM date_spine ds
LEFT JOIN daily_leads dl ON ds.date_utc = dl.date_utc
LEFT JOIN daily_activities da ON ds.date_utc = da.date_utc
LEFT JOIN daily_persons dp ON ds.date_utc = dp.date_utc
CROSS JOIN cumulative_totals ct
CROSS JOIN high_priority_leads_json hpl
ORDER BY ds.date_utc DESC
