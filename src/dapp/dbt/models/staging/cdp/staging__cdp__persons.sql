{{ config(
    materialized='table',
    schema='staging',
    alias='stg_cdp__persons'
) }}

SELECT
  id AS person_id,
  first_name AS first_name,
  last_name AS last_name,
  primary_email AS primary_email,
  primary_phone AS primary_phone,
  linkedin_url AS linkedin_url,
  city AS city,
  country AS country,
  primary_company_id AS primary_company_id,
  status AS status,
  attributes AS attributes,
  created_at AS created_at,
  updated_at AS updated_at,
  in_linkedin_connections AS in_linkedin_connections,
  in_substack_subscriber_export AS in_substack_subscriber_export,
  person_segment_id AS person_segment_id,
  person_segment_name AS person_segment_name,
  person_segment_slug AS person_segment_slug,
  potential_opportunity_types AS potential_opportunity_types,
  engagement_temperature AS engagement_temperature
FROM {{ source('s_cdp', 'persons') }}
