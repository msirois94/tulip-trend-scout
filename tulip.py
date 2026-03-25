"""
TULIP — Trend Scout for Pontil
===============================
This script runs daily via GitHub Actions. It:
1. Checks your curated source list for new articles (via RSS feeds)
2. Sends each new article to Claude for relevance scoring
3. Pushes high-scoring entries into your Notion Research Hub
4. Sends a Slack digest summarising what it found

You don't need to understand the code — just follow the setup steps
in the README. If you want to add a new source, scroll down to the
SOURCES section below and copy the pattern.
"""

import os
import json
import hashlib
import time
from datetime import datetime, timedelta

# These libraries get installed automatically by GitHub Actions
# (listed in requirements.txt)
import feedparser
import requests
from bs4 import BeautifulSoup


# ╔══════════════════════════════════════════════════════════════════╗
# ║  SETTINGS — Change these if you want to tweak Tulip's behaviour ║
# ╚══════════════════════════════════════════════════════════════════╝

# How many days back to look for new articles (on each run)
LOOKBACK_DAYS = 14

# Minimum relevance score (1–10) for an article to be pushed to Notion
# Lower = more articles, higher = stricter filtering
RELEVANCE_THRESHOLD = 6

# Which Claude model to use (Haiku is cheapest, Sonnet is smarter)
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Maximum number of articles to process per run (keeps API costs predictable)
MAX_ARTICLES_PER_RUN = 30


# ╔══════════════════════════════════════════════════════════════════╗
# ║  SOURCES — Your curated list of blogs and feeds to monitor       ║
# ║                                                                  ║
# ║  To add a new source:                                            ║
# ║  1. Copy one of the entries below                                ║
# ║  2. Change the name, url, and feed_url                           ║
# ║  3. Set feed_url to None if the site has no RSS feed             ║
# ║  4. Commit the change in GitHub                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

SOURCES = [
    # ── Original Pontil Research Hub sources ──────────────────────
    {
        "name": "The Pragmatic Engineer",
        "url": "https://newsletter.pragmaticengineer.com",
        "feed_url": "https://newsletter.pragmaticengineer.com/feed",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "LangChain Blog",
        "url": "https://blog.langchain.dev",
        "feed_url": "https://blog.langchain.dev/rss/",
        "content_type": "Competitor Update",
    },
    {
        "name": "Composio Blog",
        "url": "https://composio.dev/blog",
        "feed_url": "https://composio.dev/blog/rss.xml",
        "content_type": "Competitor Update",
    },
    {
        "name": "a16z Infrastructure & AI",
        "url": "https://a16z.com/category/infrastructure/",
        "feed_url": "https://a16z.com/category/infrastructure/feed/",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "MCP Official Blog",
        "url": "https://blog.modelcontextprotocol.io",
        "feed_url": "https://blog.modelcontextprotocol.io/feed.xml",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "Workato — The Connector",
        "url": "https://www.workato.com/the-connector",
        "feed_url": "https://www.workato.com/the-connector/feed/",
        "content_type": "Competitor Update",
    },
    {
        "name": "MuleSoft Blog",
        "url": "https://blogs.mulesoft.com",
        "feed_url": "https://blogs.mulesoft.com/feed/",
        "content_type": "Industry Articles & News",
    },

    # ── High-volume AI & infrastructure sources ───────────────────
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/",
        "feed_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "The New Stack",
        "url": "https://thenewstack.io",
        "feed_url": "https://thenewstack.io/feed/",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "InfoQ — AI/ML & Data Engineering",
        "url": "https://www.infoq.com/ai-ml-data-eng/",
        "feed_url": "https://feed.infoq.com/ai-ml-data-eng/",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "Simon Willison's Weblog",
        "url": "https://simonwillison.net",
        "feed_url": "https://simonwillison.net/atom/everything/",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "MIT Technology Review — AI",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/",
        "feed_url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/",
        "feed_url": "https://venturebeat.com/category/ai/feed/",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "The Verge — AI",
        "url": "https://www.theverge.com/ai-artificial-intelligence",
        "feed_url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "content_type": "Industry Articles & News",
    },

    # ── AI vendor blogs (ecosystem moves) ─────────────────────────
    {
        "name": "Anthropic Blog",
        "url": "https://www.anthropic.com/news",
        "feed_url": "https://www.anthropic.com/rss.xml",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog",
        "feed_url": "https://openai.com/blog/rss.xml",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/",
        "feed_url": "https://blog.google/technology/ai/rss/",
        "content_type": "Industry Articles & News",
    },

    # ── API infrastructure & competitor sources ───────────────────
    {
        "name": "Postman Blog",
        "url": "https://blog.postman.com",
        "feed_url": "https://blog.postman.com/feed/",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "Membrane Blog",
        "url": "https://www.membrane.io/blog",
        "feed_url": "https://www.membrane.io/blog/rss.xml",
        "content_type": "Competitor Update",
    },
    {
        "name": "Kong Blog",
        "url": "https://konghq.com/blog",
        "feed_url": "https://konghq.com/blog/feed",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "Zapier Engineering Blog",
        "url": "https://zapier.com/engineering",
        "feed_url": "https://zapier.com/engineering/feeds/latest/",
        "content_type": "Competitor Update",
    },

    # ── Hacker News — filtered by keyword ─────────────────────────
    # Separate feeds because HN RSS treats multi-word queries as AND.
    # Lower point thresholds = more results.
    {
        "name": "Hacker News — AI Agents",
        "url": "https://news.ycombinator.com",
        "feed_url": "https://hnrss.org/newest?q=AI+agent&points=30",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "Hacker News — MCP Protocol",
        "url": "https://news.ycombinator.com",
        "feed_url": "https://hnrss.org/newest?q=MCP+protocol&points=20",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "Hacker News — API Gateway",
        "url": "https://news.ycombinator.com",
        "feed_url": "https://hnrss.org/newest?q=API+gateway&points=20",
        "content_type": "Industry Articles & News",
    },
    {
        "name": "Hacker News — iPaaS Integration",
        "url": "https://news.ycombinator.com",
        "feed_url": "https://hnrss.org/newest?q=iPaaS+integration&points=10",
        "content_type": "Industry Articles & News",
    },
]


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TOPIC TAGS — These match your Notion Research Hub exactly       ║
# ║  Don't change these unless you also update your Notion database  ║
# ╚══════════════════════════════════════════════════════════════════╝

TOPIC_TAGS = [
    "Agent Accessibility",
    "MCP / Protocol Standards",
    "iPaaS & Integration",
    "API Infrastructure",
    "AI Agents (general)",
    "SaaS Vendor Strategy",
    "Customer Pain Evidence",
    "Competitor Intel",
    "Market Stats & Data",
    "Build in Public Inspiration",
]


# ╔══════════════════════════════════════════════════════════════════╗
# ║  INTERNAL CODE — You don't need to touch anything below here     ║
# ╚══════════════════════════════════════════════════════════════════╝

# Load secrets from environment variables (set in GitHub Secrets)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# File to track which articles we've already processed
SEEN_ARTICLES_FILE = "seen_articles.json"

# Fake a normal browser so feeds don't block us
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
}


def load_seen_articles():
    """Load the list of articles we've already processed."""
    if os.path.exists(SEEN_ARTICLES_FILE):
        with open(SEEN_ARTICLES_FILE, "r") as f:
            return json.load(f)
    return {}


def save_seen_articles(seen):
    """Save the list of processed articles so we don't duplicate them."""
    with open(SEEN_ARTICLES_FILE, "w") as f:
        json.dump(seen, f, indent=2)


def make_article_id(url):
    """Create a short unique ID from a URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def get_entry_date(entry):
    """
    Try every common date field to extract a publish date.
    Returns a datetime or None if no date can be determined.
    """
    for attr in ["published_parsed", "updated_parsed", "created_parsed"]:
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime(*parsed[:6])
            except (TypeError, ValueError):
                continue

    for attr in ["published", "updated", "created", "dc_date"]:
        raw = getattr(entry, attr, None)
        if raw:
            for fmt in [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z",
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S %Z",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]:
                try:
                    dt = datetime.strptime(raw[:25].strip(), fmt)
                    return dt.replace(tzinfo=None)
                except (ValueError, TypeError):
                    continue

    return None


def fetch_articles_from_rss(source):
    """
    Check an RSS feed for new articles.
    Now with detailed logging and forgiving date handling.
    """
    articles = []
    feed_url = source.get("feed_url")

    if not feed_url:
        print(f"  No feed URL configured — skipping")
        return articles

    try:
        # Fetch with browser headers (some feeds block default user-agents)
        response = requests.get(feed_url, headers=HEADERS, timeout=15)
        print(f"  HTTP {response.status_code} | {len(response.content)} bytes")

        if response.status_code != 200:
            print(f"  Non-200 status — skipping")
            return articles

        feed = feedparser.parse(response.content)

        if feed.bozo and not feed.entries:
            print(f"  Feed parse error: {feed.bozo_exception}")
            return articles

        total_entries = len(feed.entries)
        print(f"  {total_entries} entries in feed")

        if total_entries == 0:
            return articles

        cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
        accepted = 0
        too_old = 0
        no_date = 0

        for entry in feed.entries[:20]:
            title = entry.get("title", "Untitled")
            url = entry.get("link", "")

            if not url:
                continue

            published = get_entry_date(entry)

            if published:
                if published < cutoff:
                    too_old += 1
                    continue
            else:
                # No date — include it anyway, better safe than sorry
                no_date += 1

            summary = ""
            for field in ["summary", "description", "content"]:
                raw = getattr(entry, field, None)
                if raw:
                    if isinstance(raw, list):
                        raw = raw[0].get("value", "") if raw else ""
                    soup = BeautifulSoup(str(raw), "html.parser")
                    summary = soup.get_text()[:500]
                    if summary:
                        break

            articles.append({
                "title": title,
                "url": url,
                "summary": summary,
                "source_name": source["name"],
                "content_type": source["content_type"],
            })
            accepted += 1

        print(f"  Result: {accepted} accepted, {too_old} too old, {no_date} no date (included)")

    except requests.exceptions.Timeout:
        print(f"  Timed out — skipping")
    except requests.exceptions.ConnectionError as e:
        print(f"  Connection error: {str(e)[:100]}")
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {str(e)[:100]}")

    return articles


def score_with_claude(article):
    """
    Send an article to Claude for relevance scoring.
    """
    prompt = f"""You are a research assistant for Pontil, a B2B SaaS infrastructure company.

Pontil builds a Generated API Gateway that makes SaaS platforms fully operable by AI agents.
The core problem: SaaS platforms expose only 2–5% of capability via public APIs. AI agents need 100%.
Pontil scans UIs, private APIs, and legacy services to generate a secure API layer — closing the gap.

Score this article's relevance to Pontil (1–10) and extract key information.

Article title: {article['title']}
Source: {article['source_name']}
URL: {article['url']}
Summary: {article['summary'][:400]}

Respond with ONLY valid JSON (no markdown, no backticks, no explanation) in this exact format:
{{
  "relevance_score": 7,
  "topic_tags": ["Agent Accessibility", "API Infrastructure"],
  "key_quote_or_stat": "One sentence — the single most useful fact, quote, or statistic from this article.",
  "why_relevant": "One sentence — what this means for Pontil's positioning, content, or sales outreach.",
  "suggested_title": "A clean, short title for the Research Hub entry."
}}

Topic tags must be chosen from this list only:
{json.dumps(TOPIC_TAGS)}

Pick the top 2–3 most relevant tags. Be selective — don't tag everything."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )

        if response.status_code != 200:
            print(f"  Claude API error {response.status_code}: {response.text[:200]}")
            return None

        data = response.json()
        text = data["content"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        return result

    except json.JSONDecodeError as e:
        print(f"  Could not parse Claude's response as JSON: {e}")
        return None
    except Exception as e:
        print(f"  Error calling Claude API: {e}")
        return None


def push_to_notion(article, scoring):
    """
    Create a new entry in the Notion Research Hub database.
    """
    tags = [{"name": tag} for tag in scoring.get("topic_tags", [])]

    properties = {
        "Title": {
            "title": [{"text": {"content": scoring.get("suggested_title", article["title"])}}]
        },
        "URL": {"url": article["url"]},
        "Content Type": {"select": {"name": article["content_type"]}},
        "Topic Tag": {"multi_select": tags},
        "Who Added": {"rich_text": [{"text": {"content": "Tulip (auto)"}}]},
        "Date Added": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
        "Newsletter Ready": {"checkbox": False},
        "Key Quote / Stat": {
            "rich_text": [{"text": {"content": scoring.get("key_quote_or_stat", "")[:2000]}}]
        },
        "Why It's Relevant": {
            "rich_text": [{"text": {"content": scoring.get("why_relevant", "")[:2000]}}]
        },
    }

    try:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers={
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            },
            json={
                "parent": {"database_id": NOTION_DATABASE_ID},
                "properties": properties,
            },
            timeout=30,
        )

        if response.status_code == 200:
            return True
        else:
            print(f"  Notion error {response.status_code}: {response.text[:300]}")
            return False

    except Exception as e:
        print(f"  Error pushing to Notion: {e}")
        return False


def send_slack_digest(pushed_articles, skipped_count):
    """
    Send a formatted digest to Slack.
    Only sends if there are articles to report.
    """
    if not SLACK_WEBHOOK_URL:
        print("  Slack webhook not configured — skipping")
        return

    if not pushed_articles and skipped_count == 0:
        print("  No new articles — skipping Slack notification")
        return

    today = datetime.now().strftime("%-d %B %Y")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🌷 Latest Trend Updates — {today}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{len(pushed_articles)} new article{'s' if len(pushed_articles) != 1 else ''}* added to the Research Hub"
                        + (f" · {skipped_count} below threshold" if skipped_count > 0 else ""),
            },
        },
        {"type": "divider"},
    ]

    for item in pushed_articles:
        article = item["article"]
        scoring = item["scoring"]
        score = scoring.get("relevance_score", 0)
        tags = ", ".join(scoring.get("topic_tags", []))
        title = scoring.get("suggested_title", article["title"])
        key_stat = scoring.get("key_quote_or_stat", "")
        why = scoring.get("why_relevant", "")

        if score >= 9:
            score_emoji = "🔥"
        elif score >= 7:
            score_emoji = "✅"
        else:
            score_emoji = "📄"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{score_emoji} *<{article['url']}|{title}>*\n"
                    f"Score: *{score}/10* · {tags}\n"
                    f"_{key_stat}_\n"
                    f"→ {why}"
                ),
            },
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": "Tulip the Trend Scout · Weekly review every Monday 7am AEST · All entries added to Notion · React with 👍 to flag for Matty",
        }],
    })

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks}, timeout=15)
        if response.status_code == 200:
            print("  Slack digest sent ✓")
        else:
            print(f"  Slack error {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"  Slack error: {e}")


def main():
    print("=" * 60)
    print(f"TULIP TREND SCOUT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Lookback: {LOOKBACK_DAYS} days | Threshold: {RELEVANCE_THRESHOLD}/10")
    print(f"Sources: {len(SOURCES)} | Max per run: {MAX_ARTICLES_PER_RUN}")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        return
    if not NOTION_TOKEN:
        print("ERROR: NOTION_TOKEN not set.")
        return
    if not NOTION_DATABASE_ID:
        print("ERROR: NOTION_DATABASE_ID not set.")
        return

    seen = load_seen_articles()
    print(f"Previously seen: {len(seen)} articles")

    new_count = 0
    pushed_count = 0
    skipped_count = 0
    error_count = 0
    pushed_articles = []

    for source in SOURCES:
        print(f"\n{'─' * 50}")
        print(f"Source: {source['name']}")
        articles = fetch_articles_from_rss(source)

        for article in articles:
            if new_count >= MAX_ARTICLES_PER_RUN:
                print(f"\n  Hit limit ({MAX_ARTICLES_PER_RUN}) — stopping")
                break

            article_id = make_article_id(article["url"])
            if article_id in seen:
                continue

            new_count += 1
            print(f"  NEW: {article['title'][:70]}...")

            scoring = score_with_claude(article)
            if scoring is None:
                error_count += 1
                continue

            score = scoring.get("relevance_score", 0)
            print(f"  Score: {score}/10 | Tags: {', '.join(scoring.get('topic_tags', []))}")

            seen[article_id] = {
                "title": article["title"],
                "url": article["url"],
                "score": score,
                "date": datetime.now().strftime("%Y-%m-%d"),
            }

            if score >= RELEVANCE_THRESHOLD:
                success = push_to_notion(article, scoring)
                if success:
                    pushed_count += 1
                    pushed_articles.append({"article": article, "scoring": scoring})
                    print(f"  -> Notion ✓")
                else:
                    error_count += 1
                    print(f"  -> Notion ✗")
            else:
                skipped_count += 1
                print(f"  -> Below threshold, skipped")

            time.sleep(1)

        if new_count >= MAX_ARTICLES_PER_RUN:
            break

    save_seen_articles(seen)

    print(f"\n{'─' * 50}")
    print(f"Sending Slack digest...")
    send_slack_digest(pushed_articles, skipped_count)

    print(f"\n{'=' * 60}")
    print(f"DONE — {new_count} new articles from {len(SOURCES)} sources")
    print(f"  ✓ {pushed_count} pushed to Notion")
    print(f"  ○ {skipped_count} below threshold")
    print(f"  ✗ {error_count} errors")
    print(f"  Total tracked: {len(seen)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
