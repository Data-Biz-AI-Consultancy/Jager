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


@app.post("/run/ingest_substack")
def run_ingest_substack():
    logger.info("Triggered ingest_substack pipeline execution")
    try:
        # Execute the python script as a subprocess
        result = subprocess.run(
            ["python", "olap/ingest_substack.py"],
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


@app.post("/run/ingest_nager")
def run_ingest_nager():
    logger.info("Triggered ingest_nager pipeline execution")
    try:
        # Execute the python script as a subprocess
        result = subprocess.run(
            ["python", "olap/ingest_nager.py"],
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




@app.post("/run/dbt_transform")
def run_dbt_transform():
    logger.info("Triggered dbt pipeline execution")
    try:
        # Execute the dbt build command as a subprocess
        result = subprocess.run(
            ["dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("dbt execution succeeded")
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"dbt execution failed: {e.stderr}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "dbt execution failed",
                "exit_code": e.returncode,
                "stdout": e.stdout,
                "stderr": e.stderr
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error during dbt run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run/reverse_etl")
def run_reverse_etl():
    logger.info("Triggered reverse_etl pipeline execution")
    try:
        # Execute the python script as a subprocess
        result = subprocess.run(
            ["python", "olap/reverse_etl.py"],
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


@app.post("/run/oltp/ingest_wordpress")
def run_oltp_ingest_wordpress():
    logger.info("Triggered oltp/ingest_wordpress pipeline execution")
    try:
        # Execute the python script as a subprocess
        result = subprocess.run(
            ["python", "oltp/ingest_wordpress.py"],
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


@app.post("/run/oltp/ingest_yahoo_finance")
def run_oltp_ingest_yahoo_finance():
    logger.info("Triggered oltp/ingest_yahoo_finance pipeline execution")
    try:
        # Execute the python script as a subprocess
        result = subprocess.run(
            ["python", "oltp/ingest_yahoo_finance.py"],
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


@app.post("/run/oltp/ingest_eurostat_fx")
def run_oltp_ingest_eurostat_fx():
    logger.info("Triggered oltp/ingest_eurostat_fx pipeline execution")
    try:
        # Execute the python script as a subprocess
        result = subprocess.run(
            ["python", "oltp/ingest_eurostat_fx.py"],
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




