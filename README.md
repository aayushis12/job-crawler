# 🎯 AI Job Crawler

A fully automated daily job crawler that finds senior ML/AI roles, scores them against your resume using an LLM, generates tailored application documents, and delivers a curated digest to your inbox — all for free.

**Runs on GitHub Actions every weekday at 7 AM PST. Zero infrastructure. Zero cost.**

---

## What It Does

1. **Crawls** 10+ job sources: LinkedIn, Indeed, Greenhouse ATS, Lever ATS, Ashby ATS, Workable, RemoteOK, We Work Remotely, Remotive, and Jobicy
2. **Filters** by title keywords, seniority (7+ YOE), and visa sponsorship for international roles
3. **Scores** each job 0–100 against your resume using Groq's free LLM API (batched to stay within free tier limits)
4. **Generates** a tailored resume and cover letter for every match above your threshold
5. **Emails** an HTML digest with the top matches, scores, and application links
6. **Logs** every match to a Notion database for tracking

---

## Architecture

```
GitHub Actions (cron: 7am PST, Mon–Fri)
        │
        ├── crawl_jobs.py
        │     ├── jobspy        → LinkedIn, Indeed (US + Remote + India + International)
        │     ├── Greenhouse    → 40+ AI/tech company boards
        │     ├── Lever         → 10+ company boards
        │     ├── Ashby         → 30+ company boards
        │     ├── Workable      → selected companies
        │     ├── RemoteOK      → ML/AI tags
        │     ├── We Work Remotely → programming feed
        │     ├── Remotive      → software-dev, data categories
        │     ├── Jobicy        → engineering RSS
        │     └── Custom pages  → Automattic, Basecamp/37signals
        │
        ├── score_jobs.py
        │     ├── Stage 1: keyword + YOE pre-filter (free)
        │     └── Stage 2: LLM batch scoring via Groq (5 jobs/call)
        │
        ├── generate_docs.py   → tailored resume + cover letter per match
        ├── notion_tracker.py  → log to Notion database
        └── email_notify.py    → HTML digest via Gmail SMTP
```

---

## Supported Job Sources

| Source | Type | Notes |
|---|---|---|
| LinkedIn | jobspy | US, Remote, India, International |
| Indeed | jobspy | US, Remote |
| Greenhouse | ATS API | 40+ companies |
| Lever | ATS API | 10+ companies |
| Ashby | ATS API | 30+ companies |
| Workable | ATS API | selected companies |
| RemoteOK | JSON API | ML/AI tags |
| We Work Remotely | RSS | programming jobs |
| Remotive | JSON API | software-dev, data |
| Jobicy | RSS | engineering roles |
| Automattic | Custom API | fully remote |
| Basecamp/37signals | Custom JSON | remote-first |

---

## Quick Start (Fork & Run)

### 1. Fork this repo

Click **Fork** → keep it private if you prefer.

### 2. Set up Secrets

Go to **Settings → Secrets and variables → Secrets** and add:

| Secret | Description |
|---|---|
| `RESUME_TEXT` | Your full resume as plain text |
| `LLAMA_API_KEY` | Groq API key — free at [console.groq.com](https://console.groq.com) |
| `GMAIL_USER` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail App Password — [generate here](https://myaccount.google.com/apppasswords) |
| `NOTIFICATION_EMAIL` | Email address to receive the daily digest |
| `NOTION_API_KEY` | *(optional)* Notion integration token |
| `NOTION_DATABASE_ID` | *(optional)* Notion database ID |

### 3. Set up Variables (optional overrides)

Go to **Settings → Secrets and variables → Variables** to customize without editing code:

| Variable | Example value | Description |
|---|---|---|
| `SEARCH_QUERIES` | `Staff ML Engineer,LLM Engineer,Applied AI Engineer` | Comma-separated search terms |
| `SEARCH_LOCATIONS` | `Remote,United States,Bangalore India` | Comma-separated locations |

Leave blank to use the defaults in `config.py`.

### 4. Run it

Go to **Actions → Daily Job Crawler → Run workflow** to trigger manually, or wait for the 7 AM PST weekday schedule.

---

## Configuration

Edit `scripts/config.py` to customize:

```python
YEARS_OF_EXPERIENCE = 10      # your experience level
MIN_MATCH_SCORE     = 85      # minimum LLM score to appear in email (0-100)
MAX_JOBS_IN_EMAIL   = 10      # cap on daily digest size
MIN_YOE_GENERAL     = 7       # filter out jobs requiring fewer YOE (general companies)
MIN_YOE_TIER1       = 5       # relaxed floor for top AI labs

# Add/remove target role keywords (case-insensitive)
TARGET_ROLE_KEYWORDS = ["llm", "applied ai", "agentic", ...]

# Add companies to each ATS crawler
GREENHOUSE_COMPANIES = ["anthropic", "openai", "databricks", ...]
LEVER_COMPANIES      = ["mistral", "duckduckgo", ...]
ASHBY_COMPANIES      = ["perplexity", "cognition", ...]
```

---

## Notion Setup (optional)

Create a Notion database with these exact property names:

| Property | Type |
|---|---|
| `Job Title` | Title |
| `Company` | Text |
| `Location` | Text |
| `Match Score` | Number |
| `Application URL` | URL |
| `Status` | Select (`New`, `Applied`, `Interview`, `Offer`, `Rejected`) |
| `Date Found` | Date |
| `Source` | Select |
| `Type` | Select |
| `Tier-1 Company` | Checkbox |

[Create a Notion integration](https://www.notion.so/my-integrations), connect it to your database, then add the token and database ID as secrets.

---

## Token Usage (Groq Free Tier)

The free tier gives **500k tokens/day** on `llama-3.1-8b-instant`.

Typical daily run:
- ~100 jobs pass keyword filter
- Scored in batches of 5 → ~20 API calls
- ~2k tokens per batch → ~40k tokens for scoring
- ~5k tokens for document generation
- **Total: ~45–50k tokens/day** — well within the 500k free limit

---

## Gmail App Password

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security) and enable 2-Step Verification
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create a new app password → name it anything (e.g. "Job Crawler")
4. Copy the 16-character password → add as the `GMAIL_APP_PASSWORD` secret

---

## Project Structure

```
job-crawler/
├── .github/
│   └── workflows/
│       └── job_crawler.yml   # schedule, secrets, variables
├── scripts/
│   ├── config.py             # all tunable parameters
│   ├── crawl_jobs.py         # all job source crawlers
│   ├── score_jobs.py         # keyword filter + LLM batch scoring
│   ├── generate_docs.py      # tailored resume + cover letter
│   ├── notion_tracker.py     # Notion logging
│   ├── email_notify.py       # HTML email digest
│   └── main.py               # pipeline orchestrator
├── output/                   # run artifacts (gitignored)
├── requirements.txt
└── README.md
```

---

## Contributing

PRs welcome! Ideas:

- Add more ATS integrations (Rippling, Workday, SmartRecruiters)
- Slack / Discord / Telegram notification support
- Resume parsing from PDF instead of plain text
- Parallel jobspy calls to cut crawl time
- Company culture scoring (Glassdoor ratings, etc.)

---

## How It Works — Technical Deep Dive

### The Problem

Job searching at a senior level is noisy. Most platforms surface hundreds of irrelevant postings — contract roles, entry-level positions, companies you'd never work for. Manual searching is repetitive and exhausting.

### Why GitHub Actions?

Free compute, zero infrastructure, built-in cron scheduling, secret management, and artifact storage. Public repos get unlimited Actions minutes; the whole pipeline runs comfortably within the 120-minute timeout.

### Why ATS APIs Directly?

LinkedIn blocks cloud IPs at scale, and scrapers are fragile. But most companies post jobs through ATS platforms (Greenhouse, Lever, Ashby) that expose **public JSON APIs** with no authentication. A single call to `boards-api.greenhouse.io/v1/boards/anthropic/jobs` returns every open role at Anthropic — fast, reliable, and geographically complete (India, US, Remote all in one response).

### Why Batch LLM Scoring?

Groq's free tier gives 500k tokens/day, but naively scoring 100 jobs one-by-one burns through it fast (each call re-sends your full resume). Batching 5 jobs per API call sends the resume once for five descriptions, reducing token usage by ~60%.

### The Scoring Prompt

Each batch prompt sends a 2,000-char resume summary and up to 5 job descriptions (1,000 chars each), asking the model for a 0–100 score, match reasons, gaps, and a one-line summary in a JSON array. The structured output makes parsing deterministic.

---

## License

MIT
