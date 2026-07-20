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
logger = setup_logging("ingest-substack")

def clean_html(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    text_content = soup.get_text()
    return text_content.strip()

def get_active_feeds(engine):
    feeds = []
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, name, feed_url FROM s_substack.feeds_monitored WHERE active = true"))
            for row in result:
                feeds.append(dict(row._mapping))
    except Exception as e:
        logger.warning(f"Failed to query feeds_monitored from database: {e}. Falling back to default list.")
    
    if not feeds:
        feeds = [
            {"id": 1, "name": "SeattleDataGuy", "feed_url": "https://seattledataguy.substack.com/feed"},
            {"id": 2, "name": "Decision", "feed_url": "https://decision.substack.com/feed"},
            {"id": 3, "name": "EngLeadership", "feed_url": "https://newsletter.eng-leadership.com/feed"},
            {"id": 4, "name": "ThrivingInEngineering", "feed_url": "https://thrivinginengineering.substack.com/feed"},
            {"id": 5, "name": "CodeLikeAGirl", "feed_url": "https://codelikeagirl.substack.com/feed"},
            {"id": 6, "name": "Data Biz", "feed_url": "https://jimmypang.substack.com/feed"},
            {"id": 7, "name": "Benn", "feed_url": "https://benn.substack.com/feed"},
            {"id": 8, "name": "nilukakavanagh", "feed_url": "https://nilukakavanagh.substack.com/feed"},
            {"id": 9, "name": "Datapreneur", "feed_url": "https://nickvaliotti.substack.com/feed"}
        ]
    return feeds

def fetch_post_analytics(url, headers):
    comment_count = 0
    child_comment_count = 0
    restacks = 0
    reactions = {}
    reaction_count = 0
    subtitle = ''
    slug = ''
    canonical_url = ''
    audience = ''
    is_published = False
    type_val = ''
    meter_type = ''
    teaser_post_eligible = False
    wordcount = 0
    language = ''
    post_date = None
    updated_at = None
    cover_image = ''
    cover_image_is_square = False
    cover_image_is_explicit = False
    body_html = ''
    truncated_body_text = ''
    section_id = None
    audio_items = []
    podcast_fields = {}
    theme_variables = {}
    comments = []
    inbox_item = {}

    if url and "/p/" in url:
        api_url = url.split('?')[0].replace('/p/', '/api/v1/posts/');
        try:
            time.sleep(0.5)
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                comment_count = data.get("comment_count", 0)
                child_comment_count = data.get("child_comment_count", 0)
                restacks = data.get("restacks", 0)
                reactions = data.get("reactions", {})
                reaction_count = data.get("reaction_count", 0)
                subtitle = data.get("subtitle", "")
                slug = data.get("slug", "")
                canonical_url = data.get("canonical_url", "")
                audience = data.get("audience", "")
                is_published = data.get("is_published", False)
                type_val = data.get("type", "")
                meter_type = data.get("meter_type", "")
                teaser_post_eligible = data.get("teaser_post_eligible", False)
                wordcount = data.get("wordcount", 0)
                language = data.get("language", "")
                post_date = data.get("post_date")
                updated_at = data.get("updated_at")
                cover_image = data.get("cover_image", "")
                cover_image_is_square = data.get("cover_image_is_square", False)
                cover_image_is_explicit = data.get("cover_image_is_explicit", False)
                body_html = data.get("body_html", "")
                truncated_body_text = data.get("truncated_body_text", "")
                section_id = data.get("section_id")
                audio_items = data.get("audio_items", [])
                podcast_fields = data.get("podcastFields", {})
                theme_variables = data.get("themeVariables", {})
                comments = data.get("comments", [])
                inbox_item = data.get("inboxItem", {})
        except Exception as e:
            logger.error(f"Error fetching analytics for {url}: {e}")

    return {
        "comment_count": comment_count,
        "child_comment_count": child_comment_count,
        "restacks": restacks,
        "reactions": reactions,
        "reaction_count": reaction_count,
        "subtitle": subtitle,
        "slug": slug,
        "canonical_url": canonical_url,
        "audience": audience,
        "is_published": is_published,
        "type": type_val,
        "meter_type": meter_type,
        "teaser_post_eligible": teaser_post_eligible,
        "wordcount": wordcount,
        "language": language,
        "post_date": post_date,
        "updated_at": updated_at,
        "cover_image": cover_image,
        "cover_image_is_square": cover_image_is_square,
        "cover_image_is_explicit": cover_image_is_explicit,
        "body_html": body_html,
        "truncated_body_text": truncated_body_text,
        "section_id": section_id,
        "audio_items": audio_items,
        "podcast_fields": podcast_fields,
        "theme_variables": theme_variables,
        "comments": comments,
        "inbox_item": inbox_item
    }

def run_ingestion():
    logger.info("Initializing DB engine")
    engine = get_db_engine()
    feeds = get_active_feeds(engine)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    # Ingestion date range: last 999 days (to match N8N's date range setup)
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=999)
    
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
            "processed": {"data_type": "bigint"},
            "subtitle": {"data_type": "text"},
            "slug": {"data_type": "text"},
            "canonical_url": {"data_type": "text"},
            "audience": {"data_type": "text"},
            "is_published": {"data_type": "boolean"},
            "type": {"data_type": "text"},
            "meter_type": {"data_type": "text"},
            "teaser_post_eligible": {"data_type": "boolean"},
            "wordcount": {"data_type": "bigint"},
            "language": {"data_type": "text"},
            "post_date": {"data_type": "timestamp", "nullable": True},
            "updated_at": {"data_type": "timestamp", "nullable": True},
            "cover_image": {"data_type": "text"},
            "cover_image_is_square": {"data_type": "boolean"},
            "cover_image_is_explicit": {"data_type": "boolean"},
            "body_html": {"data_type": "text"},
            "truncated_body_text": {"data_type": "text"},
            "section_id": {"data_type": "bigint", "nullable": True},
            "reaction_count": {"data_type": "bigint"},
            "reactions": {"data_type": "json"},
            "comment_count": {"data_type": "bigint"},
            "child_comment_count": {"data_type": "bigint"},
            "restacks": {"data_type": "bigint"},
            "audio_items": {"data_type": "json"},
            "podcast_fields": {"data_type": "json"},
            "theme_variables": {"data_type": "json"},
            "comments": {"data_type": "json"},
            "inbox_item": {"data_type": "json"}
        }
    )
    def fetch_substack_posts():
        for feed in feeds:
            feed_id = feed["id"]
            feed_name = feed["name"]
            feed_url = feed["feed_url"]
            
            logger.info(f"Fetching RSS feed from: {feed_name} ({feed_url})")
            try:
                # Use headers tailored to RSS fetching, Jager/1.0
                rss_headers = get_http_headers()
                response = requests.get(feed_url, headers=rss_headers, timeout=10)
                if response.status_code != 200:
                    logger.error(f"Failed to fetch {feed_url}: Status code {response.status_code}")
                    continue
                
                parsed_feed = feedparser.parse(response.text)
                for entry in parsed_feed.entries:
                    published_dt = None
                    if entry.get("published_parsed"):
                        published_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
                    else:
                        published_dt = now
                    
                    if published_dt < start_date:
                        continue
                    
                    content_raw = entry.get("summary") or entry.get("description") or ""
                    if entry.get("content"):
                        content_raw = entry.content[0].value
                    
                    cleaned_content = clean_html(content_raw)
                    if not cleaned_content:
                        cleaned_content = entry.get("title", "")
                    
                    cleaned_content = cleaned_content[:5000]
                    post_url = entry.get("link", "")
                    
                    # Fetch detailed analytics from API
                    analytics = fetch_post_analytics(post_url, headers)
                    
                    post_data = {
                        "id": entry.get("id") or post_url,
                        "feed_id": feed_id,
                        "feed_name": feed_name,
                        "author": entry.get("author") or feed_name,
                        "title": entry.get("title", "Untitled"),
                        "content": cleaned_content,
                        "url": post_url,
                        "published_at": published_dt,
                        "processed": 0,
                        **analytics
                    }
                    yield post_data
            except Exception as ex:
                logger.error(f"Error processing feed {feed_name}: {ex}")

    pipeline = create_postgres_pipeline("substack_oltp_ingestion", "s_substack")
    
    logger.info("Running pipeline")
    load_info = pipeline.run(fetch_substack_posts())
    logger.info(f"Pipeline finished:\n{load_info}")

if __name__ == "__main__":
    run_ingestion()
