{{ config(
    materialized='view',
    schema='staging'
) }}

SELECT 
  id AS post_id,
  content AS content,
  url AS post_url,
  published_at AT TIME ZONE 'Europe/Berlin' AS published_at_berlin,
  fetched_at AT TIME ZONE 'Europe/Berlin' AS fetched_at_berlin
FROM {{ source('s_zernio', 'linkedin_posts') }}
