import os
import sys
import time
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import dlt
from sqlalchemy import text

# Add parent directory to sys.path to resolve 'olap' or 'oltp' imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import setup_logging, get_db_engine, get_http_headers, create_postgres_pipeline

# Set up logging
logger = setup_logging("ingest-wordpress")

def clean_html(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    # Retrieve text and replace common entities
    text_content = soup.get_text()
    return text_content.strip()

def get_active_feeds(engine):
    feeds = []
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, name, feed_url FROM s_wordpress.feeds_monitored WHERE active = true"))
            for row in result:
                feeds.append(dict(row._mapping))
    except Exception as e:
        logger.warning(f"Failed to query feeds_monitored from database: {e}. Falling back to default list.")
    
    if not feeds:
        # Fallback default seed matching migrate-db.js
        feeds = [{
            "id": 1,
            "name": "Towards Data Science",
            "feed_url": "https://towardsdatascience.com/feed"
        }]
    return feeds

def run_ingestion():
    logger.info("Initializing DB engine")
    engine = get_db_engine()
    feeds = get_active_feeds(engine)
    
    headers = get_http_headers()
    
    # Ingestion date range: last 30 days
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=30)
    
    @dlt.resource(
        name="posts",
        write_disposition="merge",
        primary_key="id",
        columns={
            "id": {"data_type": "text"},
            "feed_id": {"data_type": "bigint", "nullable": True},
            "feed_name": {"data_type": "text"},
            "author": {"data_type": "text"},
            "title": {"data_type": "text"},
            "content": {"data_type": "text"},
            "url": {"data_type": "text"},
            "published_at": {"data_type": "timestamp"},
            "processed": {"data_type": "bigint"}
        }
    )
    def fetch_wordpress_posts():
        for feed in feeds:
            feed_id = feed["id"]
            feed_name = feed["name"]
            feed_url = feed["feed_url"]
            
            logger.info(f"Fetching RSS feed from: {feed_name} ({feed_url})")
            try:
                response = requests.get(feed_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    logger.error(f"Failed to fetch {feed_url}: Status code {response.status_code}")
                    continue
                
                parsed_feed = feedparser.parse(response.text)
                for entry in parsed_feed.entries:
                    # Parse published timestamp
                    published_dt = None
                    if entry.get("published_parsed"):
                        published_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
                    else:
                        published_dt = now
                    
                    # Filter: only last 30 days
                    if published_dt < start_date:
                        continue
                    
                    # Extract & clean content
                    content_raw = entry.get("summary") or entry.get("description") or ""
                    if entry.get("content"):
                        content_raw = entry.content[0].value
                    
                    cleaned_content = clean_html(content_raw)
                    if not cleaned_content:
                        cleaned_content = entry.get("title", "")
                    
                    # Truncate content to 5000 chars to match N8N logic
                    cleaned_content = cleaned_content[:5000]
                    
                    yield {
                        "id": entry.get("id") or entry.get("link"),
                        "feed_id": feed_id,
                        "feed_name": feed_name,
                        "author": entry.get("author") or feed_name,
                        "title": entry.get("title", "Untitled"),
                        "content": cleaned_content,
                        "url": entry.get("link", ""),
                        "published_at": published_dt,
                        "processed": 0
                    }
            except Exception as ex:
                logger.error(f"Error processing feed {feed_name}: {ex}")

    pipeline = create_postgres_pipeline("wordpress_oltp_ingestion", "s_wordpress")
    
    logger.info("Running pipeline")
    load_info = pipeline.run(fetch_wordpress_posts())
    logger.info(f"Pipeline finished:\n{load_info}")

if __name__ == "__main__":
    run_ingestion()
