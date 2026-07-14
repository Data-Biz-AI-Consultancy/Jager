{{ config(
    materialized='view',
    schema='intermediate',
    alias='int_buffer__linkedin_posts'
) }}

SELECT 
  posts.buffer_post_id AS buffer_post_id,
  posts.content AS content,
  posts.content_hash AS content_hash,
  posts.due_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Berlin' AS published_at_berlin,
  COALESCE(posts.likes, 0) AS likes,
  COALESCE(posts.comments, 0) AS comments,
  COALESCE(posts.shares, 0) AS shares,
  COALESCE(posts.reposts, 0) AS reposts,
  COALESCE(posts.clicks, 0) AS clicks,
  COALESCE(posts.reach, 0) AS reach,
  COALESCE(posts.impressions, 0) AS impressions,
  COALESCE(posts.views, 0) AS views,
  COALESCE(posts.engagement_rate, 0.0000) AS engagement_rate
FROM {{ ref('staging__buffer__posts') }} posts
JOIN {{ ref('staging__buffer__channels') }} channels ON posts.channel_id = channels.channel_id
WHERE channels.service = 'linkedin'
