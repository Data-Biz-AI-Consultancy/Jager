{{ config(
    materialized='view',
    schema='staging'
) }}

SELECT 
  post_id AS post_id,
  COALESCE(impressions, 0) AS impressions,
  COALESCE(likes, 0) AS likes,
  COALESCE(comments, 0) AS comments,
  COALESCE(shares, 0) AS shares,
  COALESCE(clicks, 0) AS clicks,
  COALESCE(saves, 0) AS saves,
  COALESCE(sends, 0) AS sends,
  fetched_at AT TIME ZONE 'Europe/Berlin' AS fetched_at_berlin
FROM {{ source('s_zernio', 'linkedin_post_analytics') }}
