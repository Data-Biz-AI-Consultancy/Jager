# AGENTS.md

## Vibe Coding Instructions & Core Rules

### 1. Documentation & Skill Integrity (Mandatory)
- **All documentation and skill runbooks (`SKILL.md`) must always be kept up to date per code change.**
- Whenever modifying, adding, or removing features, dbt models, pipelines, schemas, configurations, workflows, ML models, or operational workflows:
  - Inspect relevant documentation under root and colocated `README.md` files (e.g., [Root README](README.md), [Scripts](scripts/README.md), [n8n Workflows](src/n8n/workflows/data_ingestion/README.md), [Tests](tests/README.md)).
  - Inspect and update all matching **`.agents/skills/<skill_name>/SKILL.md`** files (e.g. updating `jager-dbt-model` when dbt models/layers evolve, `jager-add-pipeline` when dlt pipelines change, `jager-database-ops` when database schemas shift, `jager-n8n-workflow-ops` when workflow tracks/agents change, `jager-ml-pipeline` when ML use cases evolve, `jager-cdb-integration` when cross-service APIs change).
  - In project markdown files, always use relative paths for file links (e.g., `[Scripts](scripts/README.md)`), never absolute `file:///` URIs.
  - Synchronize code, documentation, and skill definitions within the same change/PR.

### 2. CI & Code Quality Verification (Mandatory)
- **Always run and pass all automated tests before finalizing any change.**
- **Python Verification**:
  - Run `uv run pytest tests/` (or target specific service suites: `uv run pytest tests/dapp/`).
  - Pin all dependencies to exact versions in `requirements.txt` / `pyproject.toml` (e.g., `dbt-core==1.11.13`).
  - Ensure all files end with **exactly one single newline**.
- Never commit or complete a turn with unformatted code, unused imports, or failing test suites.

### 3. File Length & Modularity Limits (Mandatory)
- **Code files must not exceed 400–500 lines.**
- Whenever a file approaches or exceeds this threshold, proactively refactor and decompose into smaller, focused modules, domain utilities, or subcomponents.

### 4. Secrets & Local Environment Discipline (Mandatory)
- The `.env` file at the workspace root is **strictly for local development only** and must never be committed or deployed to production.
- In production, environment variables are injected at runtime via the host or secrets manager.
- Never hardcode sensitive credentials as fallback defaults in code or workflows.

---

## 🧭 Repository Skills Index (`.agents/skills/`)

Operational procedures, runbooks, and deep architectural specs are codified as progressive skills:

- **[jager-dbt-model](.agents/skills/jager-dbt-model/SKILL.md)**: Layer conventions (`staging`, `intermediate`, `marts`, `t_jager`), YAML documentation, MotherDuck SSO-free execution, timezone rules.
- **[jager-add-pipeline](.agents/skills/jager-add-pipeline/SKILL.md)**: dlt ingestion pipelines (OLAP, OLTP, Reverse ETL), FastAPI endpoints in dapp, n8n triggers, manual ingestion.
- **[jager-database-ops](.agents/skills/jager-database-ops/SKILL.md)**: Parallel database cloning (`clone-db.js`), schema migrations (`migrate-db.js`), MotherDuck XLSX uploads, table naming conventions.
- **[jager-n8n-workflow-ops](.agents/skills/jager-n8n-workflow-ops/SKILL.md)**: n8n workflow organization, dual-track LinkedIn publishing (individual vs Zernio), AI persona prompts (`{{VARIABLE_NAME}}`, Unicode emojis).
- **[jager-ml-pipeline](.agents/skills/jager-ml-pipeline/SKILL.md)**: 1 use case 1 subfolder rule, MotherDuck feature extraction, FastAPI inference endpoints, and ML unit tests.
- **[jager-release-and-deployment](.agents/skills/jager-release-and-deployment/SKILL.md)**: Tri-repo release flow (Jager, CDB, Jager-Deployment), GitOps self-hosted runner, port mapping, and production secrets.
- **[jager-cdb-integration](.agents/skills/jager-cdb-integration/SKILL.md)**: Architectural boundaries, REST API communication (`X-API-Key`), MotherDuck OLAP sync (`ingest_cdb.py`), and port mappings.
