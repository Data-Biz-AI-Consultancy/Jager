{{ config(
    materialized='table',
    schema='marts',
    alias='dim_nager__public_holidays'
) }}

SELECT 
  holiday_date AS holiday_date,
  holiday_name AS holiday_name,
  country_code AS country_code,
  is_national_holiday AS is_national_holiday
FROM {{ ref('staging__nager__public_holidays') }}
