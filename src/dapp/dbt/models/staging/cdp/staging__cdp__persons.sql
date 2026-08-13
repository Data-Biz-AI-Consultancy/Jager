{{ config(
    materialized='table',
    schema='staging',
    alias='stg_cdp__persons'
) }}

SELECT
  id AS person_id,
  first_name,
  last_name,
  primary_email,
  primary_phone,
  linkedin_url,
  city,
  country,
  primary_company_id,
  status,
  attributes,
  created_at,
  updated_at,
  in_linkedin_connections,
  in_substack_subscriber_export,
  person_segment_id,
  person_segment_name,
  person_segment_slug,
  potential_opportunity_types,
  engagement_temperature
FROM {{ source('s_cdp', 'persons') }}
