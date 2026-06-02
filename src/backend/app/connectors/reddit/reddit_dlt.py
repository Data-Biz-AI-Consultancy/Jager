import os
import logging
import requests
from datetime import datetime, timezone
import dlt
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Source, Setting

logger = logging.getLogger(__name__)

def get_dlt_pipeline_and_destination():
    db_url = os.getenv("DATABASE_URL", "postgresql://jager:jager@localhost:5432/jager")
    if db_url.startswith("postgresql"):
        if db_url.startswith("postgresql+psycopg2://"):
            db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")
        os.environ["DESTINATION__POSTGRES__CREDENTIALS"] = db_url
        return dlt.pipeline(
            pipeline_name="reddit_pipeline",
            destination="postgres",
            dataset_name="public",
        )
    else:
        # SQLite
        os.environ["DESTINATION__SQLITE__CREDENTIALS"] = db_url
        return dlt.pipeline(
            pipeline_name="reddit_pipeline",
            destination="sqlite",
            dataset_name="public",
        )

@dlt.source
def reddit_source(subreddits, user_token=None):
    @dlt.resource(name="raw_messages", write_disposition="merge", primary_key="id")
    def fetch_submissions():
        if user_token:
            headers = {
                "User-Agent": "Jager/1.0 (by /u/jager_developer)",
                "Authorization": f"Bearer {user_token}"
            }
            base_url = "https://oauth.reddit.com"
            for subreddit in subreddits:
                url = f"{base_url}/r/{subreddit}/new.json"
                try:
                    response = requests.get(url, headers=headers, params={"limit": 25}, timeout=10)
                    if response.status_code != 200:
                        logger.error(f"Failed to fetch from subreddit {subreddit} via API: status code {response.status_code}")
                        continue
                    
                    data = response.json()
                    children = data.get("data", {}).get("children", [])
                    for child in children:
                        post = child.get("data", {})
                        post_id = post.get("name")
                        if not post_id:
                            continue
                            
                        created_utc = post.get("created_utc")
                        created_dt = None
                        if created_utc:
                            created_dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                        
                        yield {
                            "id": f"reddit:{post_id}",
                            "platform": "reddit",
                            "source_id": f"reddit:{subreddit}",
                            "author": post.get("author"),
                            "title": post.get("title"),
                            "content": post.get("selftext") or post.get("title") or "",
                            "url": f"https://reddit.com{post.get('permalink')}" if post.get('permalink') else None,
                            "score": int(post.get("score", 0)),
                            "created_at": created_dt,
                            "processed": 0
                        }
                except Exception as e:
                    logger.error(f"Error fetching from subreddit {subreddit} via JSON API: {e}")
        else:
            # Public RSS Fallback
            import xml.etree.ElementTree as ET
            import re
            
            headers = {
                "User-Agent": "Jager/1.0 (by /u/jager_developer)"
            }
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            
            for subreddit in subreddits:
                url = f"https://www.reddit.com/r/{subreddit}/new.rss"
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code != 200:
                        logger.error(f"Failed to fetch RSS from subreddit {subreddit}: status code {response.status_code}")
                        continue
                    
                    root = ET.fromstring(response.text)
                    for entry in root.findall("atom:entry", ns):
                        post_id = entry.findtext("atom:id", default="", namespaces=ns)
                        if not post_id:
                            continue
                            
                        author_el = entry.find("atom:author", ns)
                        author = "unknown"
                        if author_el is not None:
                            author = author_el.findtext("atom:name", default="unknown", namespaces=ns)
                            if author.startswith("/u/"):
                                author = author[3:]
                                
                        title = entry.findtext("atom:title", default="", namespaces=ns)
                        content_html = entry.findtext("atom:content", default="", namespaces=ns)
                        # Strip HTML tags
                        content = re.sub(r'<.*?>|&[a-zA-Z0-9#]+;', '', content_html).strip()
                        if not content:
                            content = title
                            
                        link_el = entry.find("atom:link", ns)
                        url_str = link_el.attrib.get("href") if link_el is not None else None
                        
                        updated_str = entry.findtext("atom:updated", default="", namespaces=ns)
                        created_dt = None
                        if updated_str:
                            try:
                                created_dt = datetime.fromisoformat(updated_str)
                            except Exception:
                                pass
                                
                        yield {
                            "id": f"reddit:{post_id}",
                            "platform": "reddit",
                            "source_id": f"reddit:{subreddit}",
                            "author": author,
                            "title": title,
                            "content": content,
                            "url": url_str,
                            "score": 0,
                            "created_at": created_dt,
                            "processed": 0
                        }
                except Exception as e:
                    logger.error(f"Error fetching from subreddit {subreddit} via RSS: {e}")
                
    return fetch_submissions

def run_reddit_ingestion(db: Session = None):
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        reddit_sources = db.query(Source).filter(
            Source.platform == "reddit", 
            Source.active == True
        ).all()
        
        subreddits = [src.target for src in reddit_sources]
        if not subreddits:
            logger.info("No active Reddit subreddits configured to monitor.")
            return {"status": "success", "message": "No active subreddits configured"}
            
        setting = db.query(Setting).filter(Setting.key == "reddit_user_token").first()
        user_token = setting.value if (setting and setting.value.strip()) else None
        
        pipeline = get_dlt_pipeline_and_destination()
        info = pipeline.run(reddit_source(subreddits, user_token))
        logger.info(f"dlt pipeline loaded successfully: {info}")
        return {"status": "success", "info": str(info)}
    except Exception as e:
        logger.error(f"Failed to run Reddit ingestion pipeline: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if own_session:
            db.close()
