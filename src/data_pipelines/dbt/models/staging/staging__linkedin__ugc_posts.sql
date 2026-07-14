{{ config(
    materialized='view',
    schema='staging'
) }}

SELECT 
  id AS post_id,
  content AS content,
  MD5(LOWER(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(COALESCE(content, ''), '^"+|"+$', '', 'g')), '\s+', '', 'g'))) AS content_hash,
  url AS post_url,
  published_at AT TIME ZONE 'Europe/Berlin' AS published_at_berlin
FROM {{ source('s_linkedin', 'ugc_posts') }}
