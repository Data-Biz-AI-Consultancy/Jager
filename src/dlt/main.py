import logging
import subprocess
from fastapi import FastAPI, HTTPException

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data-pipeline-service")

app = FastAPI(title="Jager Data Pipeline Service")

@app.post("/run/ingest_buffer")
def run_ingest_buffer():
    logger.info("Triggered ingest_buffer pipeline execution")
    try:
        # Execute the python script as a subprocess
        result = subprocess.run(
            ["python", "olap/ingest_buffer.py"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Pipeline execution succeeded")
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Pipeline execution failed: {e.stderr}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Pipeline execution failed",
                "exit_code": e.returncode,
                "stdout": e.stdout,
                "stderr": e.stderr
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error during pipeline run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run/ingest_zernio")
def run_ingest_zernio():
    logger.info("Triggered ingest_zernio pipeline execution")
    try:
        # Execute the python script as a subprocess
        result = subprocess.run(
            ["python", "olap/ingest_zernio.py"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Pipeline execution succeeded")
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Pipeline execution failed: {e.stderr}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Pipeline execution failed",
                "exit_code": e.returncode,
                "stdout": e.stdout,
                "stderr": e.stderr
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error during pipeline run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run/ingest_linkedin")
def run_ingest_linkedin():
    logger.info("Triggered ingest_linkedin pipeline execution")
    try:
        # Execute the python script as a subprocess
        result = subprocess.run(
            ["python", "olap/ingest_linkedin.py"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Pipeline execution succeeded")
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Pipeline execution failed: {e.stderr}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Pipeline execution failed",
                "exit_code": e.returncode,
                "stdout": e.stdout,
                "stderr": e.stderr
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error during pipeline run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


