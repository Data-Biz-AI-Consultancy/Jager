{{ config(
    materialized='view',
    schema='staging',
    alias='stg_linkedin__ugc_posts'
) }}

WITH cleaned_source AS (
  SELECT 
    id AS post_id,
    -- Normalize LinkedIn text to align content 100%:
    --   1. Normalize curly/smart double-quotes → straight double-quotes
    --   2. Strip @ symbol from handles but keep the names (e.g., @Microsoft -> Microsoft)
    --   3. Strip leading/trailing " from every line (covers wrapped lines, stray
    --      quote-only lines, and trailing unmatched quotes in one pass)
    --   4. Collapse 3+ consecutive newlines → double newline
    --   5. Remove extra whitespace before closing parentheses
    --   6. Collapse runs of multiple spaces into one
    TRIM(
      REGEXP_REPLACE(
        REGEXP_REPLACE(
          REGEXP_REPLACE(
            REGEXP_REPLACE(
              REGEXP_REPLACE(
                REGEXP_REPLACE(
                  REGEXP_REPLACE(
                    REGEXP_REPLACE(
                      content,
                      '\r\n',                  -- Normalize CRLF to LF
                      '\n',
                      'g'
                    ),
                    'Seattle\s+Data\s+Guy\s*[\(/]?\s*Benjamin\s+Rogojan\s*\)?', -- Normalize specific attribution
                    'Seattle Data Guy (Benjamin Rogojan)',
                    'g'
                  ),
                  '[\x{201C}\x{201D}]',      -- 1. Curly → straight double-quotes
                  '"',
                  'g'
                ),
                '@([^\s@]+)',                -- 2. Strip @ symbol but keep name
                '\1',
                'g'
              ),
              '(?m)^"+|"+$',                -- 3. Strip leading/trailing " per line
              '',
              'g'
            ),
            '\n{3,}',                        -- 4. Collapse excess blank lines to exactly one blank line (\n\n)
            E'\n\n',
            'g'
          ),
          '\s+\)',                            -- 5. Remove spaces before closing parens
          ')',
          'g'
        ),
        '  +',                               -- 6. Collapse 2+ spaces into one
        ' ',
        'g'
      )
    ) AS content,
    url AS post_url,
    published_at AT TIME ZONE 'Europe/Berlin' AS published_at_berlin
  FROM {{ source('s_linkedin', 'ugc_posts') }}
)

SELECT
  post_id,
  content,
  MD5(LOWER(REGEXP_REPLACE(COALESCE(content, ''), '\s+', '', 'g'))) AS content_hash,
  post_url,
  published_at_berlin
FROM cleaned_source
