# Former `tests/dapp`

Pipeline and ML unit tests that imported `src/dapp` are obsolete in Jager — that tree was moved to the **DAPP** repository.

Run DAPP tests from the DAPP checkout:

```bash
cd ../DAPP && uv run pytest -q
```

Workflow JSON contract checks (e.g. Notion URL shapes) may remain here if they only assert n8n files under `src/n8n/workflows/`.
