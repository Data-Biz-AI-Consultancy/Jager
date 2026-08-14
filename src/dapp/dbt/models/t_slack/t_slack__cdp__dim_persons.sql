{{ config(
    materialized='table',
    schema='t_slack',
    alias='cdp_persons'
) }}

SELECT
    person_id,
    first_name,
    last_name,
    full_name,
    primary_email,
    primary_phone,
    linkedin_url,
    city,
    country,
    primary_company_id,
    primary_company_name,
    status,
    person_segment_id,
    person_segment_name,
    person_segment_slug,
    engagement_temperature,
    in_linkedin_connections,
    in_substack_subscriber_export,
    created_at AT TIME ZONE 'Europe/Berlin' AS created_at_berlin,
    updated_at AT TIME ZONE 'Europe/Berlin' AS updated_at_berlin
FROM {{ ref('marts__cdp__dim_persons') }}
