"""
main.py — Job Crawler Orchestrator

Pipeline:
  1. Load resume from env
  2. Crawl all sources
  3. Keyword + experience pre-filter
  4. Claude match scoring (keep ≥ MIN_MATCH_SCORE)
  5. Generate tailored resume + cover letter for top matches
  6. Log to Notion
  7. Send Gmail digest
"""

import os
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Ensure scripts/ is on the path when run from repo root
sys.path.insert(0, str(Path(__file__).parent))

from crawl_jobs    import crawl_all
from score_jobs    import keyword_prefilter, score_all
from generate_docs import generate_all
from notion_tracker import track_jobs
from email_notify  import send_digest
from config        import MAX_JOBS_IN_EMAIL

# ─── LOGGING SETUP ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("output/run.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def load_resume() -> str:
    resume = os.environ.get("RESUME_TEXT", "").strip()
    if not resume:
        raise EnvironmentError(
            "RESUME_TEXT secret is empty. "
            "Add your resume text as a GitHub Actions secret named RESUME_TEXT."
        )
    return resume


def save_results(jobs: list[dict]) -> None:
    os.makedirs("output", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = f"output/results_{date_str}.json"
    with open(out_path, "w") as f:
        # Remove very long fields to keep the JSON readable
        slim = []
        for j in jobs:
            s = {k: v for k, v in j.items() if k not in ("tailored_resume", "cover_letter", "description")}
            slim.append(s)
        json.dump(slim, f, indent=2, default=str)
    logger.info(f"[main] Results saved to {out_path}")


# ─── PIPELINE ────────────────────────────────────────────────────────────────

def run() -> None:
    start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"Job Crawler started at {start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)

    os.makedirs("output", exist_ok=True)

    # 1. Resume
    logger.info("[main] Loading resume…")
    resume = load_resume()
    logger.info(f"[main] Resume loaded ({len(resume)} chars)")

    # 2. Crawl
    logger.info("[main] Crawling job sources…")
    raw_jobs = crawl_all()
    logger.info(f"[main] {len(raw_jobs)} new jobs after deduplication")

    if not raw_jobs:
        logger.info("[main] No new jobs found. Sending empty digest.")
        send_digest([])
        return

    # 3. Keyword + experience pre-filter
    logger.info("[main] Applying keyword + experience filter…")
    filtered = keyword_prefilter(raw_jobs)

    if not filtered:
        logger.info("[main] All jobs filtered out. Sending empty digest.")
        send_digest([])
        return

    # 4. Claude scoring
    logger.info(f"[main] Scoring {len(filtered)} jobs with Claude…")
    top_jobs = score_all(filtered, resume)

    if not top_jobs:
        logger.info("[main] No jobs scored ≥ threshold. Sending empty digest.")
        send_digest([])
        return

    # Cap at MAX_JOBS_IN_EMAIL before generating docs (saves API cost)
    top_jobs = top_jobs[:MAX_JOBS_IN_EMAIL]
    logger.info(f"[main] {len(top_jobs)} top matches selected")

    # 5. Generate tailored resume + cover letter
    logger.info("[main] Generating tailored documents…")
    top_jobs = generate_all(top_jobs, resume)

    # 6. Notion
    logger.info("[main] Logging to Notion…")
    top_jobs = track_jobs(top_jobs)

    # 7. Email
    logger.info("[main] Sending email digest…")
    send_digest(top_jobs)

    # Persist slim results JSON as artifact
    save_results(top_jobs)

    elapsed = (datetime.now() - start).seconds
    logger.info(f"[main] Done in {elapsed}s — {len(top_jobs)} jobs sent.")


if __name__ == "__main__":
    run()
