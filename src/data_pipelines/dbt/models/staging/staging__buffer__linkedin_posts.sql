{{ config(
    materialized='view',
    schema='staging',
    alias='stg_buffer__linkedin_posts'
) }}

SELECT 
  posts.id AS buffer_post_id,
  posts.text AS content,
  MD5(LOWER(REGEXP_REPLACE(TRIM(COALESCE(posts.text, '')), '\s+', '', 'g'))) AS content_hash,
  posts.due_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Berlin' AS published_at_berlin,
  COALESCE(posts.reactions, 0) AS likes,
  COALESCE(posts.comments, 0) AS comments,
  COALESCE(posts.shares, 0) AS shares,
  COALESCE(posts.reposts, 0) AS reposts,
  COALESCE(posts.clicks, 0) AS clicks,
  COALESCE(posts.reach, 0) AS reach,
  COALESCE(posts.impressions, 0) AS impressions,
  COALESCE(posts.views, 0) AS views,
  COALESCE(posts.engagement_rate, 0.0000) AS engagement_rate
FROM {{ source('s_buffer', 'posts') }} posts
JOIN {{ source('s_buffer', 'channels') }} channels ON posts.channel_id = channels.id
WHERE channels.service = 'linkedin'

