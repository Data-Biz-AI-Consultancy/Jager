{{ config(
    materialized='view',
    schema='intermediate',
    alias='int_linkedin_post_engagement'
) }}

SELECT 
  p.post_id AS post_id,
  p.content AS content,
  p.post_url AS post_url,
  p.published_at_berlin AS published_at_berlin,
  a.impressions AS impressions,
  a.likes AS likes,
  a.comments AS comments,
  a.shares AS shares,
  a.clicks AS clicks,
  a.saves AS saves,
  a.sends AS sends,
  (a.likes + a.comments + a.shares + a.clicks + a.saves + a.sends) AS total_interactions,
  CASE 
    WHEN a.impressions > 0 THEN 
      ROUND(CAST(a.likes + a.comments + a.shares + a.clicks + a.saves + a.sends AS NUMERIC) / a.impressions, 4)
    ELSE 0.0000 
  END AS engagement_rate,
  NOW() AT TIME ZONE 'Europe/Berlin' AS calculated_at_berlin
FROM {{ ref('staging__zernio__linkedin_posts') }} p
LEFT JOIN {{ ref('staging__zernio__linkedin_post_analytics') }} a ON p.post_id = a.post_id

