{{ config(
    materialized='table',
    schema='marts',
    alias='dim_cdp_persons'
) }}

SELECT
  persons.person_id AS person_id,
  persons.first_name AS first_name,
  persons.last_name AS last_name,
  CONCAT(persons.first_name, ' ', persons.last_name) AS full_name,
  persons.primary_email AS primary_email,
  persons.primary_phone AS primary_phone,
  persons.linkedin_url AS linkedin_url,
  persons.city AS city,
  persons.country AS country,
  persons.primary_company_id AS primary_company_id,
  companies.company_name AS primary_company_name,
  persons.status AS status,
  persons.person_segment_id AS person_segment_id,
  persons.person_segment_name AS person_segment_name,
  persons.person_segment_slug AS person_segment_slug,
  persons.engagement_temperature AS engagement_temperature,
  persons.in_linkedin_connections AS in_linkedin_connections,
  persons.in_substack_subscriber_export AS in_substack_subscriber_export,
  persons.created_at AS created_at,
  persons.updated_at AS updated_at
FROM {{ ref('staging__cdp__persons') }} AS persons
LEFT JOIN {{ ref('staging__cdp__companies') }} AS companies
  ON persons.primary_company_id = companies.company_id
