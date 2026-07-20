{{ config(
    materialized='table',
    schema='marts',
    alias='sum_content_marketing_daily_performance'
) }}

WITH company_posts AS (
    SELECT
        CAST(published_at_berlin AS DATE) AS published_date_berlin,
        'company' AS account_type,
        impressions,
        likes,
        comments,
        shares,
        clicks,
        total_interactions,
        engagement_rate
    FROM {{ ref('marts__linkedin__company_page_post_engagement') }}
    WHERE published_at_berlin IS NOT NULL
),

personal_posts AS (
    SELECT
        CAST(published_at_berlin AS DATE) AS published_date_berlin,
        'personal' AS account_type,
        impressions,
        likes,
        comments,
        shares,
        clicks,
        total_interactions,
        engagement_rate
    FROM {{ ref('marts__linkedin__personal_account_post_engagement') }}
    WHERE published_at_berlin IS NOT NULL
),

all_posts AS (
    SELECT * FROM company_posts
    UNION ALL
    SELECT * FROM personal_posts
)

SELECT
    published_date_berlin,
    account_type,
    COUNT(*)                                                                AS posts_published,
    SUM(impressions)                                                        AS total_impressions,
    SUM(likes) + SUM(comments) + SUM(shares)                                AS total_interactions,
    SUM(likes)                                                              AS total_likes,
    SUM(comments)                                                           AS total_comments,
    SUM(shares)                                                             AS total_shares,
    SUM(clicks)                                                             AS total_clicks,
    NOW() AT TIME ZONE 'Europe/Berlin'                                      AS calculated_at_berlin
FROM all_posts
GROUP BY published_date_berlin, account_type
ORDER BY published_date_berlin DESC, account_type
