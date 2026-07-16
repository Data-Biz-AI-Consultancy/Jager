{{ config(
    materialized='view',
    schema='staging',
    alias='stg_buffer__posts'
) }}

SELECT 
  id AS buffer_post_id,
  -- Normalize Buffer text to match LinkedIn native post style:
  --   1. Strip @handle mentions
  --   2. Remove lines containing only double-quote characters
  --   3. Remove extra whitespace before closing parentheses
  --   4. Collapse runs of multiple spaces into one
  TRIM(
    REGEXP_REPLACE(
      REGEXP_REPLACE(
        REGEXP_REPLACE(
          REGEXP_REPLACE(
            text,
            '@[^\s@]+',    -- 1. Strip @handles
            '',
            'g'
          ),
          '(?m)^"+\s*$',  -- 2. Remove stray double-quote-only lines
          '',
          'g'
        ),
        '\s+\)',           -- 3. Remove spaces before closing parentheses
        ')',
        'g'
      ),
      '  +',              -- 4. Collapse 2+ spaces into one
      ' ',
      'g'
    )
  ) AS content,
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
