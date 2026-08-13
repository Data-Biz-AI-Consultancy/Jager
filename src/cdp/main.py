import logging
from fastapi import FastAPI, HTTPException
from processors.process_linkedin_connections import process_linkedin_connections
from processors.process_manual_data import process_manual_data
from processors.process_linkedin_messages import process_linkedin_messages
from processors.process_notion_meeting_notes import process_notion_meeting_notes
from processors.evaluate_segments import evaluate_segments

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


@app.post("/process/linkedin_messages")
def run_process_linkedin_messages():
    logger.info("Triggered CDP LinkedIn messages processing")
    try:
        result = process_linkedin_messages()
        return result
    except Exception as e:
        logger.error(f"Error processing CDP LinkedIn messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/notion_meeting_notes")
def run_process_notion_meeting_notes():
    logger.info("Triggered CDP Notion meeting notes processing")
    try:
        result = process_notion_meeting_notes()
        return result
    except Exception as e:
        logger.error(f"Error processing CDP Notion meeting notes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/evaluate_segments")
def run_evaluate_segments():
    logger.info("Triggered CDP segment evaluation processing")
    try:
        result = evaluate_segments()
        return result
    except Exception as e:
        logger.error(f"Error evaluating CDP segments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




