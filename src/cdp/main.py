import logging
from fastapi import FastAPI, HTTPException
try:
    from processors.process_linkedin_connections import process_linkedin_connections
except ImportError:
    from src.cdp.processors.process_linkedin_connections import process_linkedin_connections

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
