{{ config(
    materialized='view',
    schema='staging',
    alias='stg_buffer__posts'
) }}

SELECT 
  id AS buffer_post_id,
  text AS content,
  MD5(LOWER(REGEXP_REPLACE(TRIM(COALESCE(text, '')), '\s+', '', 'g'))) AS content_hash,
  due_at AS due_at,
  reactions AS likes,
  comments AS comments,
  shares AS shares,
  reposts AS reposts,
  clicks AS clicks,
  reach AS reach,
  impressions AS impressions,
  views AS views,
  engagement_rate AS engagement_rate,
  channel_id AS channel_id
FROM {{ source('s_buffer', 'posts') }}
