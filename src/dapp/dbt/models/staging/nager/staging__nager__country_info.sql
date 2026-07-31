{{ config(
    materialized='view',
    schema='staging',
    alias='stg_nager__country_info'
) }}

SELECT 
  country_code AS country_code,
  common_name AS common_name,
  native_name AS native_name,
  official_name AS official_name,
  region AS region
FROM {{ source('s_nager', 'country_info') }}
