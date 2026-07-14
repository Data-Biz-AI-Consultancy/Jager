SELECT 
  p.id AS buffer_post_id,
  p.text AS content,
  MD5(LOWER(REGEXP_REPLACE(TRIM(COALESCE(p.text, '')), '\s+', '', 'g'))) AS content_hash,
  p.due_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Berlin' AS published_at_berlin,
  COALESCE(p.reactions, 0) AS likes,
  COALESCE(p.comments, 0) AS comments,
  COALESCE(p.shares, 0) AS shares,
  COALESCE(p.reposts, 0) AS reposts,
  COALESCE(p.clicks, 0) AS clicks,
  COALESCE(p.reach, 0) AS reach,
  COALESCE(p.impressions, 0) AS impressions,
  COALESCE(p.views, 0) AS views,
  COALESCE(p.engagement_rate, 0.0000) AS engagement_rate
FROM {{ source('s_buffer', 'posts') }} p
JOIN {{ source('s_buffer', 'channels') }} c ON p.channel_id = c.id
WHERE c.service = 'linkedin'
