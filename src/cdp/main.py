import logging
from fastapi import FastAPI, HTTPException
from processors.process_linkedin_connections import process_linkedin_connections
from processors.process_manual_data import process_manual_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cdp-service")

app = FastAPI(title="Jager CDP Service")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "cdp"}


@app.post("/process/linkedin_connections")
def run_process_linkedin_connections():
    logger.info("Triggered CDP LinkedIn connections processing")
    try:
        result = process_linkedin_connections()
        return result
    except Exception as e:
        logger.error(f"Error processing CDP LinkedIn connections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/manual_data")
def run_process_manual_data():
    logger.info("Triggered CDP manual data processing")
    try:
        result = process_manual_data()
        return result
    except Exception as e:
        logger.error(f"Error processing CDP manual data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

