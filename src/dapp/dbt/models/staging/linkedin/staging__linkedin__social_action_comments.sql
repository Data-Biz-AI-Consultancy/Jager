{{ config(
    materialized='view',
    schema='staging',
    alias='stg_linkedin__social_action_comments'
) }}

SELECT 
  post_id AS post_id,
  COUNT(id) AS comments_count
FROM {{ source('s_linkedin', 'social_action_comments') }}
GROUP BY post_id
