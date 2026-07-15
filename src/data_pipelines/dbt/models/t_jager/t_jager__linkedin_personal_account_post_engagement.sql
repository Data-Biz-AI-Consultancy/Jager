{{ config(
    materialized='table',
    schema='t_jager',
    alias='fct_linkedin_personal_account_post_engagement'
) }}

SELECT * FROM {{ ref('marts__linkedin__personal_account_post_engagement') }}
