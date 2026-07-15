{{ config(
    materialized='table',
    schema='t_jager',
    alias='fct_linkedin_company_page_post_engagement'
) }}

SELECT * FROM {{ ref('marts__linkedin__company_page_post_engagement') }}
