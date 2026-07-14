SELECT 
  linkedin_post_id AS linkedin_post_id,
  urn AS urn,
  content AS content,
  post_url AS post_url,
  published_at_berlin AS published_at_berlin,
  impressions AS impressions,
  likes AS likes,
  comments AS comments,
  shares AS shares,
  reposts AS reposts,
  clicks AS clicks,
  saves AS saves,
  sends AS sends,
  total_interactions AS total_interactions,
  engagement_rate AS engagement_rate,
  calculated_at_berlin AS calculated_at_berlin
FROM {{ ref('int_linkedin_personal_post_engagement') }}
