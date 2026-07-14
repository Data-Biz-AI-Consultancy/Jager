{{ config(
    materialized='view',
    schema='intermediate',
    alias='int_linkedin_post_engagement'
) }}

SELECT 
  posts.post_id AS post_id,
  posts.content AS content,
  posts.post_url AS post_url,
  posts.published_at_berlin AS published_at_berlin,
  analytics.impressions AS impressions,
  analytics.likes AS likes,
  analytics.comments AS comments,
  analytics.shares AS shares,
  analytics.clicks AS clicks,
  analytics.saves AS saves,
  analytics.sends AS sends,
  (analytics.likes + analytics.comments + analytics.shares + analytics.clicks + analytics.saves + analytics.sends) AS total_interactions,
  CASE 
    WHEN analytics.impressions > 0 THEN 
      ROUND(CAST(analytics.likes + analytics.comments + analytics.shares + analytics.clicks + analytics.saves + analytics.sends AS NUMERIC) / analytics.impressions, 4)
    ELSE 0.0000 
  END AS engagement_rate,
  NOW() AT TIME ZONE 'Europe/Berlin' AS calculated_at_berlin
FROM {{ ref('staging__zernio__linkedin_posts') }} posts
LEFT JOIN {{ ref('staging__zernio__linkedin_post_analytics') }} analytics ON posts.post_id = analytics.post_id
