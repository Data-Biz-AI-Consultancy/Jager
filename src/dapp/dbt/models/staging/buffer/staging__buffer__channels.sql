{{ config(
    materialized='view',
    schema='staging',
    alias='stg_buffer__channels'
) }}

SELECT 
  id AS channel_id,
  name AS channel_name,
  service AS service,
  organization_id AS organization_id,
  active AS active,
  created_at AS created_at,
  updated_at AS updated_at
FROM {{ source('s_buffer', 'channels') }}
