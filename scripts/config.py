"""
Job Crawler Configuration
Customize this file to match your background and preferences.
"""

# ─── YOUR PROFILE ────────────────────────────────────────────────────────────

YEARS_OF_EXPERIENCE = 10

# Target job title keywords (case-insensitive, any match triggers inclusion)
TARGET_ROLE_KEYWORDS = [
    "applied ai",
    "applied scientist",
    "llm",
    "large language model",
    "search quality",
    "search engineer",
    "search relevance",
    "agentic ai",
    "agentic",
    "staff engineer",
    "staff ml",
    "staff machine learning",
    "staff software engineer",
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "nlp engineer",
    "generative ai",
    "gen ai",
    "foundation model",
    "rag engineer",
    "retrieval augmented",
    "research engineer",
    "ml platform",
    "ml infrastructure",
    "ai platform",
    "conversational ai",
    "multimodal",
    "inference engineer",
]

# Keywords that disqualify a job (entry-level / irrelevant)
EXCLUDE_KEYWORDS = [
    "intern",
    "internship",
    "co-op",
    "new grad",
    "entry level",
    "entry-level",
    "junior",
    "associate engineer",
    "data analyst",          # not engineering
    "product manager",
    "program manager",
    "account manager",
    "sales",
    "recruiter",
    "hr ",
    "human resources",
    "marketing",
    "finance",
    "legal",
    "customer success",
    "support engineer",
    "devops",                # unless you want these
    "ios engineer",
    "android engineer",
    "mobile engineer",
    "frontend engineer",
    "backend engineer",      # remove if you're open to these
    "full stack",
    "fullstack",
    "qa engineer",
    "quality assurance",
    "security engineer",
    "network engineer",
    "data engineer",         # remove if open
]

# ─── EXPERIENCE LEVEL FILTERS ─────────────────────────────────────────────────

# For general companies: job must NOT require fewer than this many years
MIN_YOE_GENERAL = 7

# For tier-1 AI companies: relax the floor to this
MIN_YOE_TIER1 = 5

# Patterns that indicate the job is below your level (regex, case-insensitive)
BELOW_LEVEL_PATTERNS = [
    r"\b0[-–]\s*[1-3]\s*years?\b",
    r"\b1[-–]\s*[3-5]\s*years?\b",
    r"\b2[-–]\s*[4]\s*years?\b",
    r"\b[0-3]\+\s*years?\b",
    r"\bfresh\s*graduate\b",
    r"\brecent\s*graduate\b",
    r"\bnew\s*grad\b",
    r"\bentry.level\b",
]

# ─── TIER-1 AI / TOP TECH COMPANIES ─────────────────────────────────────────
# Lowercased — matched against company name in job listing

TIER_1_AI_COMPANIES = {
    "openai",
    "anthropic",
    "google",
    "deepmind",
    "google deepmind",
    "google brain",
    "meta",
    "facebook",
    "microsoft",
    "apple",
    "amazon",
    "aws",
    "nvidia",
    "cohere",
    "mistral",
    "mistral ai",
    "hugging face",
    "huggingface",
    "scale ai",
    "scale",
    "databricks",
    "together ai",
    "together.ai",
    "inflection",
    "character.ai",
    "character",
    "stability ai",
    "runway",
    "midjourney",
    "perplexity",
    "perplexity ai",
    "adobe",
    "salesforce",
    "servicenow",
    "palantir",
    "twitter",
    "x.ai",
    "xai",
    "tesla",
    "waymo",
    "deepl",
    "cohere",
    "ai21",
    "ai21 labs",
    "adept",
    "aleph alpha",
    "mosaic",
    "mosaicml",
    "cerebras",
    "groq",
    "sambanova",
    "lightspeed",
    "a16z",
}

# ─── MINIMUM MATCH SCORE TO INCLUDE ──────────────────────────────────────────

MIN_MATCH_SCORE = 85          # 0–100, jobs below this are dropped
MAX_JOBS_IN_EMAIL = 10        # cap jobs sent in the daily digest

# ─── JOB SEARCH QUERIES ──────────────────────────────────────────────────────
# These are the search strings passed to job boards

SEARCH_QUERIES = [
    "Staff Machine Learning Engineer",
    "Staff AI Engineer",
    "Applied AI Engineer",
    "LLM Engineer",
    "Applied Scientist LLM",
    "Search Quality Engineer",
    "Agentic AI Engineer",
    "ML Research Engineer",
    "Generative AI Engineer",
    "NLP Engineer Staff",
    "ML Platform Engineer Staff",
]

# Locations to search (jobspy format) — India cities listed first as priority
SEARCH_LOCATIONS = [
    "Hyderabad, India",
    "Bangalore, India",
    "Pune, India",
    "Mumbai, India",
    "Delhi, India",
    "Remote",
    "United States",
    "London, United Kingdom",
    "Singapore",
    "Dubai, United Arab Emirates",
]

# Locations considered "international" — visa filter is applied to these
# India is intentionally excluded (domestic, no visa needed)
INTERNATIONAL_LOCATIONS = {"london", "united kingdom", "uk", "singapore", "dubai", "uae", "united arab emirates"}

# Keywords that indicate visa sponsorship is available (case-insensitive)
VISA_SPONSORSHIP_KEYWORDS = [
    "visa sponsorship",
    "sponsor visa",
    "visa sponsor",
    "we sponsor",
    "will sponsor",
    "sponsorship provided",
    "relocation assistance",
    "relocation support",
    "global mobility",
    "work authorization",
    "work permit",
    "immigration support",
    "employment pass",       # Singapore EP
    "ep sponsorship",        # Singapore
    "s pass",                # Singapore
    "skilled worker visa",   # UK
    "tier 2",                # UK legacy
    "uae visa",              # Dubai
    "residency visa",        # Dubai
    "open to relocation",
    "relocation package",
]

RESULTS_PER_QUERY = 30        # per site per query (jobspy)
REMOTE_ONLY = False           # True = only remote jobs across all searches

# ─── GREENHOUSE ATS COMPANIES ────────────────────────────────────────────────
# Slug = company identifier in boards.greenhouse.io/api/v1/boards/<slug>/jobs

GREENHOUSE_COMPANIES = [
    # ── AI / ML focused ──
    "anthropic",
    "openai",
    "cohere",
    "scaleai",
    "huggingface",
    "databricks",
    "togetherai",
    "runwayml",
    "perplexityai",
    "cerebras",
    "groq",
    "snorkelai",
    "wandb",
    "modal",
    "lambdalabs",
    "allenai",
    "nvidia",
    "salesforce",
    "adobe",
    "servicenow",
    # ── Good culture / remote-first ──
    "gitlab",            # fully remote, strong eng culture
    "zapier",            # remote-first, async culture
    "buffer",            # transparent, remote-first
    "stripe",            # strong eng culture
    "shopify",           # remote-first since 2020
    "cloudflare",        # strong infra/ML roles
    "hashicorp",         # remote-first, strong culture
    "mongodb",           # good remote culture
    "elastic",           # distributed by design
    "confluent",         # remote-friendly
    "grafana",           # open source culture
    "getsentry",         # Sentry — open source, good culture
    "dbtlabs",           # dbt Labs — remote-first data company
    "netlify",           # remote-first
    "posthog",           # fully remote, open source
    "browserstack",      # remote-friendly
    "figma",
    "notion",
    "miro",
    "airtable",
    "retool",
    "vercel",
]

# ─── LEVER ATS COMPANIES ──────────────────────────────────────────────────────

LEVER_COMPANIES = [
    "mistral",
    "character",
    "stability",
    "sambanova",
    "anyscale",
    "duckduckgo",        # privacy-first, remote-first
    "remote",            # Remote.com — fully distributed
    "deel",              # remote work platform
    "loom",
    "linear",
    "replit",
]

# ─── ASHBY ATS COMPANIES ──────────────────────────────────────────────────────

ASHBY_COMPANIES = [
    # ── AI / infra ──
    "perplexity",
    "modal",
    "glean",
    "imbue",
    "descript",
    "hex",
    "lancedb",
    "weaviate",
    "chroma",
    "vectara",
    "contextual",
    "arcee",
    "predibase",
    "tenstorrent",
    "etched",
    "cognition",
    "poolside",
    "aisera",
    "moveworks",
    "typeface",
    "writer",
    "sierra",
    "speak",
    # ── Good culture / remote-first ──
    "supabase",          # open source, remote-first
    "planetscale",       # MySQL-compatible, remote-first
    "fly",               # Fly.io — strong eng culture
    "turso",             # remote-first DB company
    "neon",              # serverless Postgres
    "railway",           # developer platform
    "resend",            # email infra, good culture
    "cal",               # Cal.com — open source
    "ghost",             # open source publishing
    "sanity",            # headless CMS, remote-first
]

# ─── CUSTOM CAREER PAGE COMPANIES ────────────────────────────────────────────
# Companies that don't use standard ATS — scraped directly

CUSTOM_CAREERS = [
    {
        "name": "Automattic",
        "url": "https://automattic.com/wp-json/wpcom/v2/jobs/",
        "type": "automattic",
    },
    {
        "name": "Basecamp / 37signals",
        "url": "https://37signals.com/jobs.json",
        "type": "json_list",
        "title_key": "title",
        "url_key": "url",
    },
]

# ─── WORKABLE ATS COMPANIES ───────────────────────────────────────────────────
# Slug = subdomain in {slug}.workable.com

WORKABLE_COMPANIES = [
    "openai",
    "huggingface",
    "cohere",
    "clarifai",
    "speechify",
    "synthesia",
    "jasper",
    "copy-ai",
    "tome",
    "dust",
    "fixie",
]

# ─── REMOTE JOB BOARDS ───────────────────────────────────────────────────────

REMOTEOK_TAGS = ["machine-learning", "ai", "llm", "nlp", "search"]
WWR_RSS_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
REMOTIVE_CATEGORIES = ["software-dev", "data"]
JOBICY_RSS_URL = "https://jobicy.com/?feed=job_feed&job_categories=engineering&job_types=full-time&search_keywords=machine+learning"

# ─── NOTION ───────────────────────────────────────────────────────────────────
# These match the property names in your Notion database (configure to match yours)

NOTION_PROPS = {
    "title":        "Job Title",
    "company":      "Company",
    "location":     "Location",
    "score":        "Match Score",
    "url":          "Application URL",
    "status":       "Status",
    "date_found":   "Date Found",
    "source":       "Source",
    "job_type":     "Type",
    "tier1":        "Tier-1 Company",
}

NOTION_DEFAULT_STATUS = "New"

# ─── EMAIL ───────────────────────────────────────────────────────────────────

EMAIL_SUBJECT = "🎯 Daily Job Matches – {date}"
