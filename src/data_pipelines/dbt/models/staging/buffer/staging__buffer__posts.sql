{{ config(
    materialized='view',
    schema='staging',
    alias='stg_buffer__posts'
) }}

SELECT 
  id AS buffer_post_id,
  -- Normalize Buffer text to match LinkedIn native post style:
  --   1. Normalize curly/smart double-quotes → straight double-quotes
  --   2. Strip @handle mentions
  --   3. Strip leading/trailing " from every line (covers wrapped lines, stray
  --      quote-only lines, and trailing unmatched quotes in one pass)
  --   4. Collapse 3+ consecutive newlines → double newline (clean up empty lines
  --      left behind by quote stripping)
  --   5. Remove extra whitespace before closing parentheses
  --   6. Collapse runs of multiple spaces into one
  TRIM(
    REGEXP_REPLACE(
      REGEXP_REPLACE(
        REGEXP_REPLACE(
          REGEXP_REPLACE(
            REGEXP_REPLACE(
              REGEXP_REPLACE(
                text,
                '[\x{201C}\x{201D}]',  -- 1. Curly → straight double-quotes
                '"',
                'g'
              ),
              '@[^\s@]+',              -- 2. Strip @handles
              '',
              'g'
            ),
            '(?m)^"+|"+$',            -- 3. Strip leading/trailing " per line
            '',
            'g'
          ),
          '\n{3,}',                    -- 4. Collapse excess blank lines
          E'\n\n',
          'g'
        ),
        '\s+\)',                        -- 5. Remove spaces before closing parens
        ')',
        'g'
      ),
      '  +',                           -- 6. Collapse 2+ spaces into one
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
