{{ config(
    materialized='table',
    schema='t_jager',
    alias='timeslot_recommendations'
) }}

SELECT * FROM ds_prediction.timeslot_recommendations
