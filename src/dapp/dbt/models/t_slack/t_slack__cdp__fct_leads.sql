{{ config(
    materialized='table',
    schema='t_slack',
    alias='cdp_leads'
) }}

SELECT
    lead_id,
    person_id,
    company_id,
    full_name,
    description,
    message_count,
    summary,
    convo_history,
    intent,
    signal_strength,
    opportunity_type,
    rate,
    status,
    source,
    lead_status_id,
    lead_status_name,
    lead_status_slug,
    lead_stage_slug,
    lead_stage_name,
    intake_at AT TIME ZONE 'Europe/Berlin' AS intake_at_berlin,
    updated_at AT TIME ZONE 'Europe/Berlin' AS updated_at_berlin
FROM {{ ref('marts__cdp__fct_leads') }}
