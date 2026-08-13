{{ config(
    materialized='table',
    schema='marts',
    alias='fct_cdp_activities'
) }}

SELECT
  activities.activity_id AS activity_id,
  activities.activity_type AS activity_type,
  activities.source AS source,
  activities.source_id AS source_id,
  activities.person_id AS person_id,
  activities.company_id AS company_id,
  activities.title AS title,
  activities.activity_date AS activity_date,
  activities.summary_or_content AS summary_or_content,
  activities.to_dos AS to_dos,
  activities.participants AS participants,
  activities.url AS url,
  activities.metadata AS metadata,
  activities.created_at AS created_at,
  activities.updated_at AS updated_at
FROM {{ ref('staging__cdp__activities') }} AS activities
