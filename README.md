# 🎯 Automated Job Crawler

Runs every weekday at **7:00 AM PST** via GitHub Actions.

**Pipeline:**
```
7:00 AM → Crawl 100+ job sources → Keyword + experience filter
        → Claude match scoring → Keep ≥85% matches
        → Generate tailored resume + cover letter (Claude)
        → Log to Notion → Email digest to you
```

**Sources:** LinkedIn · Indeed · Glassdoor · ZipRecruiter · Greenhouse ATS · Lever ATS · RemoteOK · We Work Remotely

**Experience filter:** 7+ YOE required (5+ for Tier-1 AI companies like OpenAI, Anthropic, Google, Meta, etc.)

---

## Setup (one-time, ~15 minutes)

### 1. Create a private GitHub repo

Go to github.com → New repository → set it **private** → push this entire folder to it.

```bash
git init
git add .
git commit -m "initial"
git remote add origin https://github.com/YOUR_USERNAME/job-crawler.git
git push -u origin main
```

### 2. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

Add each of these:

| Secret name | Value |
|---|---|
| `RESUME_TEXT` | Your full resume as plain text (copy-paste from Word/Google Docs) |
| `ANTHROPIC_API_KEY` | From console.anthropic.com → API Keys |
| `GMAIL_USER` | Your Gmail address (e.g. `you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | 16-char App Password — see step 3 |
| `NOTIFICATION_EMAIL` | Where to receive the digest (can be same as GMAIL_USER) |
| `NOTION_API_KEY` | From notion.so/my-integrations — see step 4 |
| `NOTION_DATABASE_ID` | From your Notion database URL — see step 4 |

### 3. Get a Gmail App Password

> Required because Google blocks plain-password SMTP. Takes 2 minutes.

1. Go to **myaccount.google.com/security**
2. Turn on **2-Step Verification** (if not already on)
3. Search "App passwords" in the search bar
4. Create a new app password → name it "Job Crawler"
5. Copy the 16-character password → paste as `GMAIL_APP_PASSWORD` secret

### 4. Set up Notion

#### 4a. Create a Notion Integration
1. Go to **notion.so/my-integrations** → New integration
2. Name it "Job Crawler", choose your workspace
3. Copy the **Internal Integration Token** → paste as `NOTION_API_KEY`

#### 4b. Create the Notion Database

Create a new **full-page database** in Notion with these properties:

| Property name | Type |
|---|---|
| Job Title | Title |
| Company | Text |
| Location | Text |
| Match Score | Number |
| Application URL | URL |
| Status | Select (options: New, Reviewing, Applied, Rejected, Interviewing, Offer) |
| Date Found | Date |
| Source | Select |
| Type | Select |
| Tier-1 Company | Checkbox |

#### 4c. Connect your integration to the database
1. Open your database in Notion
2. Click **•••** (top right) → **Connections** → add "Job Crawler"
3. Copy the database ID from the URL:
   `notion.so/YOUR_WORKSPACE/**DATABASE_ID_HERE**?v=...`
4. Paste as `NOTION_DATABASE_ID` secret

### 5. Customize your search (optional)

Edit `scripts/config.py` to tune:
- `SEARCH_QUERIES` — job titles to search
- `TARGET_ROLE_KEYWORDS` — keywords to match in titles
- `EXCLUDE_KEYWORDS` — roles to skip
- `GREENHOUSE_COMPANIES` / `LEVER_COMPANIES` — add/remove ATS companies
- `MIN_MATCH_SCORE` — raise to 90 for stricter filtering
- `TIER_1_AI_COMPANIES` — add companies where 5+ YOE is acceptable

### 6. Test it

Trigger a manual run:
- Go to your repo → **Actions** tab → **Daily Job Crawler** → **Run workflow** → **Run workflow**

Check the run logs and look for the email + Notion entries.

---

## Running locally (for testing)

```bash
# Create a .env file (never commit this)
cat > .env << 'EOF'
RESUME_TEXT="..."
ANTHROPIC_API_KEY=sk-ant-...
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
NOTIFICATION_EMAIL=you@gmail.com
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
EOF

cd scripts
pip install -r ../requirements.txt
python -c "from dotenv import load_dotenv; load_dotenv('../.env')" && python main.py
```

---

## Cost estimate

Per run (weekday):
- ~30 Claude scoring calls @ ~800 tokens each ≈ 24K tokens input
- ~10 resume + cover letter generations @ ~2K tokens each ≈ 20K tokens output
- **Total: ~$0.15–0.40/day** at Claude Opus pricing (adjust model in `score_jobs.py` to `claude-haiku-4-5` for ~10× cheaper scoring)

---

## Troubleshooting

**No jobs found:** LinkedIn sometimes blocks GitHub Actions IPs. The Greenhouse/Lever/RemoteOK sources will still work. Consider using a residential proxy or SerpAPI for LinkedIn.

**Gmail "Authentication failed":** Make sure you used an App Password, not your regular password. Also check that 2FA is enabled on the account.

**Notion "object_not_found":** Double-check that the integration is connected to your database (step 4c).

**Cron not firing:** GitHub Actions cron can be delayed 15–30 min during peak times. Use `workflow_dispatch` to trigger manually.
