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

    mock_comment_response = [
        {},
        {
            "data": {
                "children": [
                    {
                        "data": {
                            "name": "t1_mockcomment123",
                            "author": "comment_author",
                            "body": "This is a comment",
                            "score": 5,
                            "created_utc": 1717332210
                        }
                    }
                ]
            }
        }
    ]

    with patch("requests.get") as mock_get:
        def side_effect(url, *args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if "comments" in url or ".json" in url and not url.endswith("new.json"):
                mock_resp.json.return_value = mock_comment_response
            else:
                mock_resp.json.return_value = mock_reddit_response
            return mock_resp
        
        mock_get.side_effect = side_effect

        # Execute source
        source_func = reddit_source(["saas"], subreddit_map={"saas": 1}, user_token="test_token_123")
        
        posts_res = source_func.resources["reddit_posts"]
        comments_res = source_func.resources["reddit_comments"]
        
        posts = list(posts_res)
        assert len(posts) == 1
        assert posts[0]["id"] == "t3_mock123"

        # Pipe posts to comments transformer
        comments = list(posts_res | comments_res)
        assert len(comments) == 1
        assert comments[0]["id"] == "t1_mockcomment123"
        assert comments[0]["post_id"] == "t3_mock123"
        assert comments[0]["author"] == "comment_author"
        assert comments[0]["content"] == "This is a comment"

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

    mock_comments_rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <id>t3_mockrss123</id>
            <title>Mock RSS Title</title>
            <content type="html">Mock Content</content>
            <author><name>/u/rss_author</name></author>
            <updated>2026-06-02T13:08:55+00:00</updated>
        </entry>
        <entry>
            <id>t1_mockcomment123</id>
            <title>Comment by comment_author</title>
            <content type="html">&lt;!-- SC_OFF --&gt;&lt;div class="md"&gt;&lt;p&gt;This is a comment&lt;/p&gt;&lt;/div&gt;&lt;!-- SC_ON --&gt;</content>
            <author><name>/u/comment_author</name></author>
            <updated>2026-06-02T13:08:55+00:00</updated>
        </entry>
    </feed>
    """

    with patch("requests.get") as mock_get:
        def side_effect(url, *args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if "comments" in url:
                mock_resp.content = mock_comments_rss_xml.encode("utf-8")
                mock_resp.text = mock_comments_rss_xml
            else:
                mock_resp.text = mock_rss_xml
                mock_resp.content = mock_rss_xml.encode("utf-8")
            return mock_resp
            
        mock_get.side_effect = side_effect

        source_func = reddit_source(["saas"], subreddit_map={"saas": 1}, user_token=None)
        posts_res = source_func.resources["reddit_posts"]
        comments_res = source_func.resources["reddit_comments"]

        posts = list(posts_res)
        assert len(posts) == 1
        assert posts[0]["id"] == "t3_mockrss123"

        comments = list(posts_res | comments_res)
        assert len(comments) == 1
        assert comments[0]["id"] == "t1_mockcomment123"

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
