SELECT 
  post_id AS post_id,
  COUNT(id) AS likes_count
FROM {{ source('s_linkedin', 'social_action_likes') }}
GROUP BY post_id
