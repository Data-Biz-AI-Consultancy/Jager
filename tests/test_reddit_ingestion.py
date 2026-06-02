import pytest
from unittest.mock import patch, MagicMock
from app.models import RedditSubredditMonitored
from app.connectors.reddit.reddit_dlt import reddit_source, run_reddit_ingestion

def test_reddit_source_yields_standardized_data():
    mock_reddit_response = {
        "data": {
            "children": [
                {
                    "data": {
                        "name": "t3_mock123",
                        "author": "tester_bob",
                        "title": "Need SaaS to automate CRM",
                        "selftext": "Looking for tools.",
                        "permalink": "/r/saas/comments/mock123/need_saas_to_automate_crm/",
                        "score": 42,
                        "created_utc": 1717332206
                    }
                }
            ]
        }
    }

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_reddit_response
        mock_get.return_value = mock_response

        # Execute source
        source_func = reddit_source(["saas"], subreddit_map={"saas": 1}, user_token="test_token_123")
        items = list(source_func.resources["reddit_posts"])

        assert len(items) == 1
        item = items[0]
        assert item["id"] == "t3_mock123"
        assert item["subreddit_id"] == 1
        assert item["author"] == "tester_bob"
        assert item["title"] == "Need SaaS to automate CRM"
        assert item["content"] == "Looking for tools."
        assert item["score"] == 42
        assert item["processed"] == 0
        assert item["created_at"] is not None

        # Verify headers used the token
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test_token_123"
        assert "oauth.reddit.com" in args[0]

def test_reddit_source_no_token_fallback():
    mock_rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>t3_mockrss123</id>
            <title>Mock RSS Title</title>
            <content type="html">Mock Content</content>
            <author><name>/u/rss_author</name></author>
            <link href="https://www.reddit.com/r/saas/comments/mockrss123/mock/"/>
            <updated>2026-06-02T13:08:55+00:00</updated>
        </entry>
    </feed>
    """

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_rss_xml
        mock_get.return_value = mock_response

        source_func = reddit_source(["saas"], subreddit_map={"saas": 1}, user_token=None)
        items = list(source_func.resources["reddit_posts"])

        assert len(items) == 1
        assert items[0]["id"] == "t3_mockrss123"
        assert items[0]["subreddit_id"] == 1
        assert items[0]["author"] == "rss_author"
        assert items[0]["title"] == "Mock RSS Title"
        assert items[0]["content"] == "Mock Content"

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "Authorization" not in kwargs["headers"]
        assert "new.rss" in args[0]

def test_run_reddit_ingestion_no_sources(db):
    res = run_reddit_ingestion(db)
    assert res["status"] == "success"
    assert "No active subreddits" in res["message"]

def test_run_reddit_ingestion_pipeline_orchestration(db):
    # Setup sources
    source = RedditSubredditMonitored(name="saas")
    db.add(source)
    db.commit()

    with patch("app.connectors.reddit.reddit_dlt.get_dlt_pipeline_and_destination") as mock_get_pipeline:
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline

        res = run_reddit_ingestion(db)
        assert res["status"] == "success"
        mock_pipeline.run.assert_called_once()
