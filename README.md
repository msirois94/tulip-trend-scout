# tulip-trend-scout
Trend Scout for Pontil
# Tulip — Trend Scout for Pontil

Tulip monitors your curated source list daily and pushes relevant articles into your Notion Research Hub — scored, tagged, and formatted — so Matty doesn't have to hunt for content manually.

**Cost:** ~$2–3/month on the Claude API. Everything else is free.

---

## What you'll need before starting

You need three accounts. All are free to create.

| Account | Where to sign up | What it's for |
|---------|-----------------|---------------|
| GitHub | [github.com](https://github.com) | Hosts the code and runs it daily |
| Claude API | [console.anthropic.com](https://console.anthropic.com) | Scores articles for relevance |
| Notion integration | [notion.so/my-integrations](https://www.notion.so/my-integrations) | Writes entries into your Research Hub |

---

## Step-by-step setup

### 1. Get your Claude API key

1. Go to [console.anthropic.com](https://console.anthropic.com) and create an account (or log in)
2. You'll get **$5 in free credits** — no card required
3. Click **"API Keys"** in the left sidebar
4. Click **"Create Key"**, name it "Tulip", and click **Create**
5. **Copy the key immediately** — you won't be able to see it again. It starts with `sk-ant-...`
6. Paste it somewhere safe temporarily (e.g. a private note). You'll need it in Step 4.

### 2. Get your Notion integration token and database ID

**Create the integration:**

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Name it **"Tulip Trend Scout"**
4. Leave the defaults and click **Submit**
5. Copy the **"Internal Integration Secret"** — it starts with `ntn_...`
6. Paste it somewhere safe temporarily

**Connect it to your Research Hub:**

1. Open your **Pontil Research Hub** database in Notion
2. Click the **three dots** menu (top right corner of the page)
3. Click **"Connections"** (or "Connect to")
4. Search for **"Tulip Trend Scout"** and click it to add the connection
5. Click **"Confirm"** when prompted

**Get your database ID:**

1. Open your Research Hub database in a **web browser** (not the desktop app)
2. Look at the URL — it will look like:
   `https://www.notion.so/your-workspace/abc123def456?v=...`
3. The database ID is the **long string of letters and numbers** between the last `/` and the `?`
4. Copy it and paste it somewhere safe temporarily

> **Example:** If your URL is `https://www.notion.so/pontil/8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d?v=123`
> then your database ID is `8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d`

### 3. Create the GitHub repository

1. Log into [github.com](https://github.com)
2. Click the **green "New" button** (top left) or go to [github.com/new](https://github.com/new)
3. Name the repository: **`tulip-trend-scout`**
4. Set it to **Private** (your API keys are in secrets, but no need to make the repo public)
5. Tick **"Add a README file"**
6. Click **"Create repository"**

### 4. Add your secret keys

1. In your new repo, click the **"Settings"** tab (along the top)
2. In the left sidebar, click **"Secrets and variables"** → **"Actions"**
3. Click **"New repository secret"** and add each of these one at a time:

| Name (type exactly) | Value (paste from earlier) |
|---------------------|---------------------------|
| `ANTHROPIC_API_KEY` | Your Claude API key (`sk-ant-...`) |
| `NOTION_TOKEN` | Your Notion integration secret (`ntn_...`) |
| `NOTION_DATABASE_ID` | The long ID string from your Notion URL |

After adding each one, click **"Add secret"**. The value will be hidden — that's normal.

### 5. Add the project files

You need to create **three files** in your repository. For each file:

1. Go to your repo's main page (click the repo name at the top)
2. Click **"Add file"** → **"Create new file"**
3. Type the **exact filename** in the name box at the top
4. Paste the file contents into the big editor area
5. Click the green **"Commit changes"** button at the bottom
6. In the popup, just click **"Commit changes"** again

**Create these three files in this order:**

#### File 1: `requirements.txt`
- Filename: `requirements.txt`
- Contents: Copy from the `requirements.txt` file provided

#### File 2: `tulip.py`
- Filename: `tulip.py`
- Contents: Copy from the `tulip.py` file provided

#### File 3: `.github/workflows/tulip-schedule.yml`
- Filename: `.github/workflows/tulip-schedule.yml`
- When you type `.github/workflows/tulip-schedule.yml`, GitHub will automatically create the folders — just type the whole path into the filename box
- Contents: Copy from the workflow file provided

### 6. Do a test run

1. Click the **"Actions"** tab in your repo
2. On the left, click **"Tulip Trend Scout"**
3. On the right, click **"Run workflow"** → **"Run workflow"** (the green button)
4. Wait 1–2 minutes. Click on the running workflow to watch it.
5. A **green tick** means it worked. Check your Notion Research Hub — new entries should appear with "Tulip (auto)" in the "Who Added" field.
6. A **red cross** means something went wrong. Click on the failed step to see the error. The most common issues are:
   - Wrong API key → re-check your secrets in Step 4
   - Notion permissions → make sure you connected the integration in Step 2
   - Wrong database ID → double-check the ID from your URL

### 7. You're done!

Tulip will now run automatically every day at **7:00 AM AEST**. You don't need to do anything — just check your Notion Research Hub periodically.

New entries will appear with:
- **"Tulip (auto)"** in the Who Added field
- **Newsletter Ready** unchecked (so Matty still has editorial control)
- **Key Quote / Stat** and **Why It's Relevant** pre-filled
- **Topic Tags** auto-assigned from the Pontil tag list

---

## How to check if it's running

1. Go to your repo on GitHub
2. Click the **"Actions"** tab
3. You'll see a list of daily runs. Green tick = success. Red cross = something broke.

---

## How to add a new source

1. Go to your repo on GitHub
2. Click on **`tulip.py`**
3. Click the **pencil icon** (top right of the file) to edit
4. Scroll down to the **SOURCES** section
5. Copy one of the existing source blocks and paste it below the last one
6. Change the `name`, `url`, `feed_url`, and `content_type`
7. Click **"Commit changes"**

If you don't know the RSS feed URL for a site, try adding `/feed`, `/rss`, or `/feed.xml` to the blog URL. If none work, set `feed_url` to `None` (and that source will be skipped until you find the feed).

---

## How to change settings

Edit `tulip.py` on GitHub (pencil icon) and look at the **SETTINGS** section at the top:

- **LOOKBACK_DAYS** — How far back to check for articles (default: 3 days)
- **RELEVANCE_THRESHOLD** — Minimum score to push to Notion (default: 6 out of 10). Lower = more articles, higher = stricter.
- **CLAUDE_MODEL** — Which Claude model to use. `claude-haiku-4-5-20251001` is cheapest. Change to `claude-sonnet-4-6` for smarter scoring (costs ~3x more but still under $10/month).

---

## Troubleshooting

**"No new articles found"** — This is normal if Tulip has already processed recent articles. It only picks up genuinely new posts.

**Red cross on a workflow run** — Click into it to see which step failed. Usually it's a secret that's missing or mistyped. Re-check Step 4.

**Articles appearing in Notion with wrong tags** — You can tweak the scoring by editing the prompt inside `tulip.py` (the `score_with_claude` function). But for most cases the defaults work well.

**Want to run it manually** — Go to Actions tab → Tulip Trend Scout → Run workflow. Useful for testing after you make changes.
