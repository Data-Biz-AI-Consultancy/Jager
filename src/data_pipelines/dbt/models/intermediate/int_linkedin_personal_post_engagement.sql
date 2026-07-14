{{ config(
    materialized='view',
    schema='intermediate',
    alias='int_linkedin_personal_post_engagement'
) }}

WITH personal_posts_joined AS (
  SELECT 
    ugc_posts.post_id AS urn,
    regexp_replace(ugc_posts.post_id, '^.*:', '') AS linkedin_post_id,
    ugc_posts.content AS content,
    ugc_posts.post_url AS post_url,
    ugc_posts.published_at_berlin AS published_at_berlin,
    COALESCE(likes.likes_count, 0) AS likes_count,
    COALESCE(comments.comments_count, 0) AS comments_count
  FROM {{ ref('staging__linkedin__ugc_posts') }} ugc_posts
  LEFT JOIN {{ ref('staging__linkedin__social_action_likes') }} likes ON ugc_posts.post_id = likes.post_id
  LEFT JOIN {{ ref('staging__linkedin__social_action_comments') }} comments ON ugc_posts.post_id = comments.post_id
),
-- Pick the single closest Buffer post per LinkedIn post (within 5 min)
linkedin_enriched AS (
  SELECT DISTINCT ON (personal_posts.linkedin_post_id)
    personal_posts.linkedin_post_id::TEXT AS linkedin_post_id,
    personal_posts.urn::TEXT AS urn,
    personal_posts.content,
    personal_posts.post_url,
    personal_posts.published_at_berlin,
    personal_posts.likes_count,
    personal_posts.comments_count,
    COALESCE(buffer_posts.impressions, 0) AS impressions,
    COALESCE(buffer_posts.likes, 0)    AS buf_likes,
    COALESCE(buffer_posts.comments, 0) AS buf_comments,
    COALESCE(buffer_posts.shares, 0)   AS buf_shares,
    COALESCE(buffer_posts.reposts, 0)  AS buf_reposts,
    COALESCE(buffer_posts.clicks, 0)   AS buf_clicks
  FROM personal_posts_joined personal_posts
  LEFT JOIN {{ ref('int_buffer__linkedin_posts') }} buffer_posts
    ON ABS(epoch(personal_posts.published_at_berlin) - epoch(buffer_posts.published_at_berlin)) < 300
  ORDER BY personal_posts.linkedin_post_id, ABS(epoch(personal_posts.published_at_berlin) - epoch(buffer_posts.published_at_berlin)) ASC
),
-- Buffer posts with no LinkedIn match within 5 min (keep them for completeness)
buffer_unmatched AS (
  SELECT buffer_posts.*
  FROM {{ ref('int_buffer__linkedin_posts') }} buffer_posts
  WHERE NOT EXISTS (
    SELECT 1 FROM personal_posts_joined personal_posts
    WHERE ABS(epoch(personal_posts.published_at_berlin) - epoch(buffer_posts.published_at_berlin)) < 300
  )
)
SELECT
  linkedin_enriched.linkedin_post_id AS linkedin_post_id,
  linkedin_enriched.urn AS urn,
  linkedin_enriched.content AS content,
  linkedin_enriched.post_url AS post_url,
  linkedin_enriched.published_at_berlin AS published_at_berlin,
  linkedin_enriched.impressions AS impressions,
  GREATEST(linkedin_enriched.likes_count, linkedin_enriched.buf_likes) AS likes,
  GREATEST(linkedin_enriched.comments_count, linkedin_enriched.buf_comments) AS comments,
  linkedin_enriched.buf_shares AS shares,
  linkedin_enriched.buf_reposts AS reposts,
  linkedin_enriched.buf_clicks AS clicks,
  0 AS saves,
  0 AS sends,
  (GREATEST(linkedin_enriched.likes_count, linkedin_enriched.buf_likes) + GREATEST(linkedin_enriched.comments_count, linkedin_enriched.buf_comments) + linkedin_enriched.buf_shares + linkedin_enriched.buf_reposts + linkedin_enriched.buf_clicks) AS total_interactions,
  CASE WHEN linkedin_enriched.impressions > 0 THEN
    ROUND(CAST(GREATEST(linkedin_enriched.likes_count, linkedin_enriched.buf_likes) + GREATEST(linkedin_enriched.comments_count, linkedin_enriched.buf_comments) + linkedin_enriched.buf_shares + linkedin_enriched.buf_reposts + linkedin_enriched.buf_clicks AS NUMERIC) / linkedin_enriched.impressions, 4)
    ELSE 0.0000
  END AS engagement_rate,
  NOW() AT TIME ZONE 'Europe/Berlin' AS calculated_at_berlin
FROM linkedin_enriched

UNION ALL

SELECT
  buffer_unmatched.buffer_post_id::TEXT AS linkedin_post_id,
  NULL::TEXT AS urn,
  buffer_unmatched.content AS content,
  NULL::TEXT AS post_url,
  buffer_unmatched.published_at_berlin AS published_at_berlin,
  buffer_unmatched.impressions AS impressions,
  buffer_unmatched.likes AS likes,
  buffer_unmatched.comments AS comments,
  buffer_unmatched.shares AS shares,
  buffer_unmatched.reposts AS reposts,
  buffer_unmatched.clicks AS clicks,
  0 AS saves,
  0 AS sends,
  (buffer_unmatched.likes + buffer_unmatched.comments + buffer_unmatched.shares + buffer_unmatched.reposts + buffer_unmatched.clicks) AS total_interactions,
  CASE WHEN buffer_unmatched.impressions > 0 THEN
    ROUND(CAST(buffer_unmatched.likes + buffer_unmatched.comments + buffer_unmatched.shares + buffer_unmatched.reposts + buffer_unmatched.clicks AS NUMERIC) / buffer_unmatched.impressions, 4)
    ELSE 0.0000
  END AS engagement_rate,
  NOW() AT TIME ZONE 'Europe/Berlin' AS calculated_at_berlin
FROM buffer_unmatched

