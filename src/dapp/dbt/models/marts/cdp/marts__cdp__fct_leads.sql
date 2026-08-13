{{ config(
    materialized='table',
    schema='marts',
    alias='fct_cdp_leads'
) }}

SELECT
  leads.lead_id AS lead_id,
  leads.person_id AS person_id,
  leads.company_id AS company_id,
  leads.full_name AS full_name,
  leads.description AS description,
  leads.message_count AS message_count,
  leads.summary AS summary,
  leads.convo_history AS convo_history,
  leads.intent AS intent,
  leads.signal_strength AS signal_strength,
  leads.opportunity_type AS opportunity_type,
  leads.rate AS rate,
  leads.status AS status,
  leads.source AS source,
  leads.lead_status_id AS lead_status_id,
  leads.lead_status_name AS lead_status_name,
  leads.lead_status_slug AS lead_status_slug,
  leads.lead_stage_slug AS lead_stage_slug,
  leads.lead_stage_name AS lead_stage_name,
  leads.intake_at AS intake_at,
  leads.updated_at AS updated_at
FROM {{ ref('staging__cdp__leads') }} AS leads
