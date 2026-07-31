{{ config(
    materialized='view',
    schema='staging',
    alias='stg_nager__public_holidays'
) }}

SELECT 
  date AS holiday_date,
  name AS holiday_name,
  country_code AS country_code,
  national_holiday AS is_national_holiday
FROM {{ source('s_nager', 'public_holidays') }}
