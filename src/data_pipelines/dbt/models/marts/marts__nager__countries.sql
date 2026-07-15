{{ config(
    materialized='table',
    schema='marts',
    alias='dim_nager__countries'
) }}

SELECT 
  country_code AS country_code,
  common_name AS common_name,
  native_name AS native_name,
  official_name AS official_name,
  region AS region
FROM {{ ref('staging__nager__country_info') }}
