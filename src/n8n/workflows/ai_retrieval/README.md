# LinkedIn Content Retrieval & Publishing Workflows

This directory contains the n8n workflows that automate the scheduling, queueing, and publishing of generated content to LinkedIn.

---

## Architecture Overview

The system operates on two distinct channels, each with a different API path:

1. **Individual Channel (`individual`)**
   * **API Path:** Direct native LinkedIn REST API (`https://api.linkedin.com/rest/posts`).
   * **Authentication:** Native LinkedIn OAuth2.
   * **Target:** Individual user profile feed.

2. **Data Biz Channel (`databiz`)**
   * **API Path:** Zernio Post API (`https://zernio.com/api/v1/posts`).
   * **Authentication:** Custom HTTP Header token (`Zernio API Credential`).
   * **Target:** Data Biz LinkedIn Organization/Company page.

---

## Database Context

All posts are managed in the PostgreSQL table:
* `t_content_generation.linkedin_posts`

Key fields queried and updated by the workflows:
* `channel` (`'individual'` or `'databiz'`)
* `content` (Post body text)
* `is_approved` (Flags if a post is approved by a human)
* `is_scheduled` (Flags if a post has been assigned a slot)
* `is_published` (Flags if the post is live on LinkedIn)
* `scheduled_at` (The publication timestamp)

---

## 1. LinkedIn Scheduler (`cge_linkedin_scheduler.json`)

**Trigger:** Runs on a cron or manual invocation.

### Operation
1. **Fetch Queue:** Queries `t_content_generation.linkedin_posts` to find the latest scheduled post for both `individual` and `databiz` channels to determine the baseline timestamp for new slots.
2. **Fetch Unscheduled Posts:** Queries for approved, unscheduled, and unpublished posts:
   ```sql
   WHERE is_approved = TRUE AND is_scheduled = FALSE AND is_published = FALSE
   ```
3. **Calculate Slots (JS Code):** 
   * Calculates independent slots per channel.
   * Places posts in designated time windows (e.g., weekday working hours).
   * Automatically skips weekends.
4. **Update DB:** Updates the posts with `is_scheduled = TRUE` and the assigned `scheduled_at` timestamp.

---

## 2. LinkedIn Publisher (`cge_linkedin_publisher.json`)

**Trigger:** Runs every 15 minutes.

```
Schedule Trigger ──> Fetch Due Posts ──┬──> Get Member URN ──> Prepare Individual Post ──> Publish to LinkedIn ──> Update DB (Individual) ──┬──> Notify Slack
                                        └──> Fetch Zernio Accounts ──> Resolve Account ID ──> Post to Zernio ──> Update DB (Data Biz) ──┘
```

### Operation
1. **Fetch Due Posts (Postgres Node):**
   Queries the database for scheduled posts whose `scheduled_at` timestamp is in the past:
   ```sql
   WHERE is_approved = TRUE AND is_scheduled = TRUE AND is_published = FALSE AND scheduled_at <= NOW()
   ```
   It performs a `UNION ALL` to pull at most 1 due post per channel.
2. **Parallel Track Architecture:**
   The workflow splits into two parallel tracks. Each track uses a Code node to filter out its relevant post from the database result. If no post is due for a track, it returns an empty array, which cleanly terminates that branch without triggering downstream nodes.

#### Track A: Individual Posts (Native)
* **Get Member URN:** Calls `GET /v2/userinfo` to fetch the logged-in user's profile ID (`sub`).
* **Prepare Individual Post (JS Code):** Resolves the due `individual` post and maps it.
* **Publish to LinkedIn:** Sends a `POST` request to `https://api.linkedin.com/rest/posts` to publish the commentary.
* **Update DB (Individual):** Marks the post status as `published` and stores the LinkedIn-returned `x-restli-id` as `external_post_id`.
* **Slack Alert:** Triggers the Slack node with publication info.

#### Track B: Data Biz Posts (Zernio)
* **Fetch Zernio Accounts:** Queries `GET https://zernio.com/api/v1/accounts` to fetch all profiles connected to the Zernio instance.
* **Resolve Account ID (JS Code):** 
  * Resolves the due `databiz` post.
  * Filters Zernio accounts to find the LinkedIn Organization/Company account.
  * Dynamically extracts its `accountId`.
* **Post to Zernio:** Sends a `POST` request to `https://zernio.com/api/v1/posts` containing the `content` and the target `accountId`.
* **Update DB (Data Biz):** Marks the post status as `published` and stores the Zernio `postId` as `external_post_id`.
* **Slack Alert:** Triggers the Slack node with publication info.
