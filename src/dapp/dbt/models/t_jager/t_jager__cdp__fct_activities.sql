{{ config(
    materialized='table',
    schema='t_jager',
    alias='cdp_activities'
) }}

SELECT
    activity_id,
    activity_type,
    source,
    source_id,
    person_id,
    company_id,
    title,
    CAST(activity_date AT TIME ZONE 'Europe/Berlin' AS DATE) AS activity_date_berlin,
    summary_or_content,
    to_dos,
    participants,
    url,
    metadata,
    created_at AT TIME ZONE 'Europe/Berlin' AS created_at_berlin,
    updated_at AT TIME ZONE 'Europe/Berlin' AS updated_at_berlin
FROM {{ ref('marts__cdp__fct_activities') }}
