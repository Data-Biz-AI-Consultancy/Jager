WITH personal_posts_joined AS (
  SELECT 
    p.post_id AS urn,
    regexp_replace(p.post_id, '^.*:', '') AS linkedin_post_id,
    p.content AS content,
    p.post_url AS post_url,
    p.published_at_berlin AS published_at_berlin,
    COALESCE(l.likes_count, 0) AS likes_count,
    COALESCE(c.comments_count, 0) AS comments_count
  FROM {{ ref('stg_linkedin__ugc_posts') }} p
  LEFT JOIN {{ ref('stg_linkedin__social_action_likes') }} l ON p.post_id = l.post_id
  LEFT JOIN {{ ref('stg_linkedin__social_action_comments') }} c ON p.post_id = c.post_id
),
-- Pick the single closest Buffer post per LinkedIn post (within 5 min)
linkedin_enriched AS (
  SELECT DISTINCT ON (p.linkedin_post_id)
    p.linkedin_post_id::TEXT AS linkedin_post_id,
    p.urn::TEXT AS urn,
    p.content,
    p.post_url,
    p.published_at_berlin,
    p.likes_count,
    p.comments_count,
    COALESCE(b.impressions, 0) AS impressions,
    COALESCE(b.likes, 0)    AS buf_likes,
    COALESCE(b.comments, 0) AS buf_comments,
    COALESCE(b.shares, 0)   AS buf_shares,
    COALESCE(b.reposts, 0)  AS buf_reposts,
    COALESCE(b.clicks, 0)   AS buf_clicks
  FROM personal_posts_joined p
  LEFT JOIN {{ ref('stg_buffer__linkedin_posts') }} b
    ON ABS(epoch(p.published_at_berlin) - epoch(b.published_at_berlin)) < 300
  ORDER BY p.linkedin_post_id, ABS(epoch(p.published_at_berlin) - epoch(b.published_at_berlin)) ASC
),
-- Buffer posts with no LinkedIn match within 5 min (keep them for completeness)
buffer_unmatched AS (
  SELECT b.*
  FROM {{ ref('stg_buffer__linkedin_posts') }} b
  WHERE NOT EXISTS (
    SELECT 1 FROM personal_posts_joined p
    WHERE ABS(epoch(p.published_at_berlin) - epoch(b.published_at_berlin)) < 300
  )
)
SELECT
  e.linkedin_post_id AS linkedin_post_id,
  e.urn AS urn,
  e.content AS content,
  e.post_url AS post_url,
  e.published_at_berlin AS published_at_berlin,
  e.impressions AS impressions,
  GREATEST(e.likes_count, e.buf_likes) AS likes,
  GREATEST(e.comments_count, e.buf_comments) AS comments,
  e.buf_shares AS shares,
  e.buf_reposts AS reposts,
  e.buf_clicks AS clicks,
  0 AS saves,
  0 AS sends,
  (GREATEST(e.likes_count, e.buf_likes) + GREATEST(e.comments_count, e.buf_comments) + e.buf_shares + e.buf_reposts + e.buf_clicks) AS total_interactions,
  CASE WHEN e.impressions > 0 THEN
    ROUND(CAST(GREATEST(e.likes_count, e.buf_likes) + GREATEST(e.comments_count, e.buf_comments) + e.buf_shares + e.buf_reposts + e.buf_clicks AS NUMERIC) / e.impressions, 4)
    ELSE 0.0000
  END AS engagement_rate,
  NOW() AT TIME ZONE 'Europe/Berlin' AS calculated_at_berlin
FROM linkedin_enriched e

UNION ALL

SELECT
  bm.buffer_post_id::TEXT AS linkedin_post_id,
  NULL::TEXT AS urn,
  bm.content AS content,
  NULL::TEXT AS post_url,
  bm.published_at_berlin AS published_at_berlin,
  bm.impressions AS impressions,
  bm.likes AS likes,
  bm.comments AS comments,
  bm.shares AS shares,
  bm.reposts AS reposts,
  bm.clicks AS clicks,
  0 AS saves,
  0 AS sends,
  (bm.likes + bm.comments + bm.shares + bm.reposts + bm.clicks) AS total_interactions,
  CASE WHEN bm.impressions > 0 THEN
    ROUND(CAST(bm.likes + bm.comments + bm.shares + bm.reposts + bm.clicks AS NUMERIC) / bm.impressions, 4)
    ELSE 0.0000
  END AS engagement_rate,
  NOW() AT TIME ZONE 'Europe/Berlin' AS calculated_at_berlin
FROM buffer_unmatched bm
