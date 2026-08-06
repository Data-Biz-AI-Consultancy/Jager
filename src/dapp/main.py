import os
import sys
import time
import logging
import subprocess
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("dapp-service")

app = FastAPI(title="Jager Data App (DAPP) Service")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    path = request.url.path
    method = request.method
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"--> [HTTP INBOUND] {method} {path} from {client_host}")
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"<-- [HTTP OUTBOUND] {method} {path} - Status: {response.status_code} - Duration: {process_time:.3f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"<-- [HTTP ERROR] {method} {path} - Exception: {str(e)} - Duration: {process_time:.3f}s")
        raise e


# Include ML routes from ml module
ml_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "ml"))
if os.path.exists(ml_dir) and ml_dir not in sys.path:
    sys.path.insert(0, ml_dir)

try:
    from ml.main import app as ml_app
    app.include_router(ml_app.router)
    logger.info("Successfully mounted ML routes into DAPP service")
except Exception as e:
    try:
        from main import app as ml_app
        app.include_router(ml_app.router)
        logger.info("Successfully mounted ML routes from main into DAPP service")
    except Exception as err:
        logger.warning(f"Could not mount ML router: {err}")


def run_pipeline_command(cmd: list, pipeline_name: str):
    logger.info(f"===> [DAPP EXECUTION START] Triggering pipeline: '{pipeline_name}' | Command: {' '.join(cmd)}")
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        duration = time.time() - start_time
        logger.info(f"===> [DAPP EXECUTION SUCCESS] Pipeline '{pipeline_name}' completed in {duration:.2f}s")

        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    logger.info(f"  [{pipeline_name} STDOUT] {line}")
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                if line.strip():
                    logger.info(f"  [{pipeline_name} STDERR] {line}")

        return {
            "status": "success",
            "pipeline": pipeline_name,
            "duration_seconds": round(duration, 2),
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        logger.error(f"===> [DAPP EXECUTION FAILURE] Pipeline '{pipeline_name}' failed with exit code {e.returncode} after {duration:.2f}s")

        if e.stdout:
            for line in e.stdout.strip().split("\n"):
                if line.strip():
                    logger.error(f"  [{pipeline_name} STDOUT] {line}")
        if e.stderr:
            for line in e.stderr.strip().split("\n"):
                if line.strip():
                    logger.error(f"  [{pipeline_name} STDERR] {line}")

        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Pipeline '{pipeline_name}' execution failed",
                "exit_code": e.returncode,
                "duration_seconds": round(duration, 2),
                "stdout": e.stdout,
                "stderr": e.stderr
            }
        )
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"===> [DAPP UNEXPECTED ERROR] Pipeline '{pipeline_name}': {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run/ingest_buffer")
def run_ingest_buffer():
    return run_pipeline_command(["python", "olap/ingest_buffer.py"], "ingest_buffer")


@app.post("/run/ingest_zernio")
def run_ingest_zernio():
    return run_pipeline_command(["python", "olap/ingest_zernio.py"], "ingest_zernio")


@app.post("/run/ingest_linkedin")
def run_ingest_linkedin():
    return run_pipeline_command(["python", "olap/ingest_linkedin.py"], "ingest_linkedin")


@app.post("/run/ingest_substack")
def run_ingest_substack():
    return run_pipeline_command(["python", "olap/ingest_substack.py"], "ingest_substack")


@app.post("/run/ingest_nager")
def run_ingest_nager():
    return run_pipeline_command(["python", "olap/ingest_nager.py"], "ingest_nager")


@app.post("/run/dbt_transform")
def run_dbt_transform():
    return run_pipeline_command(["dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"], "dbt_transform")


@app.post("/run/reverse_etl")
def run_reverse_etl():
    return run_pipeline_command(["python", "olap/reverse_etl.py"], "reverse_etl")


@app.post("/run/oltp/ingest_wordpress")
def run_oltp_ingest_wordpress():
    return run_pipeline_command(["python", "oltp/ingest_wordpress.py"], "ingest_wordpress")


@app.post("/run/oltp/ingest_yahoo_finance")
def run_oltp_ingest_yahoo_finance():
    return run_pipeline_command(["python", "oltp/ingest_yahoo_finance.py"], "ingest_yahoo_finance")


@app.post("/run/oltp/ingest_eurostat_fx")
def run_oltp_ingest_eurostat_fx():
    return run_pipeline_command(["python", "oltp/ingest_eurostat_fx.py"], "ingest_eurostat_fx")


@app.post("/run/oltp/ingest_notion_manual")
def run_oltp_ingest_notion_manual():
    return run_pipeline_command(["python", "oltp/ingest_notion_manual.py"], "ingest_notion_manual")


@app.post("/run/oltp/ingest_notion")
def run_oltp_ingest_notion(database_id: str | None = None, full_ingestion: bool = False, lookback_days: int | None = 7):
    cmd = ["python", "oltp/ingest_notion.py"]
    if database_id:
        cmd.append(database_id)
    if full_ingestion:
        cmd.append("--full")
    if lookback_days is not None:
        cmd.append(f"--lookback-days={lookback_days}")
    return run_pipeline_command(cmd, "ingest_notion")
