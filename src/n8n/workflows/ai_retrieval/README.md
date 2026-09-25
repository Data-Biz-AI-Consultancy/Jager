# LinkedIn Content Scheduling & Publishing Workflows

This directory contains n8n workflows that automate the scheduling, queueing, and dual-track publishing of generated content to LinkedIn.

For architecture diagrams, table schemas, and channel routing details, see the [n8n Workflow Operations Skill](../../../../.agents/skills/jager-n8n-workflow-ops/SKILL.md).

---

## 📋 Workflows Index

| Workflow | JSON File | Purpose |
|----------|-----------|---------|
| **LinkedIn Scheduler** | [`cge_linkedin_scheduler.json`](cge_linkedin_scheduler.json) | Calculates publishing slots (weekday working hours) and marks posts scheduled |
| **LinkedIn Publisher** | [`cge_linkedin_publisher.json`](cge_linkedin_publisher.json) | Runs every 15m; dispatches due posts via Track A (Individual) or Track B (Data Biz Zernio) |
