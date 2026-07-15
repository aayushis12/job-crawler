"""
crawl_jobs.py
Fetches jobs from:
  1. python-jobspy  → LinkedIn, Indeed, Glassdoor, ZipRecruiter
  2. Greenhouse ATS → direct public API
  3. Lever ATS      → direct public API
  4. RemoteOK       → public JSON API
  5. We Work Remotely → RSS feed
"""

import os
import re
import time
import hashlib
import logging
import feedparser
import requests
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
    logging.warning("python-jobspy not installed; skipping LinkedIn/Indeed/Glassdoor")

from config import (
    SEARCH_QUERIES,
    SEARCH_LOCATIONS,
    RESULTS_PER_QUERY,
    REMOTE_ONLY,
    GREENHOUSE_COMPANIES,
    LEVER_COMPANIES,
    REMOTEOK_TAGS,
    WWR_RSS_URL,
    TARGET_ROLE_KEYWORDS,
)

logger = logging.getLogger(__name__)

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _job_id(title: str, company: str, url: str = "") -> str:
    """Stable unique ID for deduplication."""
    key = f"{title.lower().strip()}|{company.lower().strip()}|{url}"
    return hashlib.md5(key.encode()).hexdigest()


def _clean(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _normalize_job(
    title: str,
    company: str,
    location: str,
    url: str,
    description: str,
    source: str,
    date_posted: Optional[str] = None,
    job_type: str = "Full-time",
    is_remote: bool = False,
) -> dict:
    return {
        "id":           _job_id(title, company, url),
        "title":        _clean(title),
        "company":      _clean(company),
        "location":     _clean(location),
        "url":          url.strip() if url else "",
        "description":  _clean(description),
        "source":       source,
        "date_posted":  date_posted or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "job_type":     job_type,
        "is_remote":    is_remote or "remote" in _clean(location).lower(),
    }


def _title_matches(title: str) -> bool:
    """Quick check: does the job title contain any target keyword?"""
    t = title.lower()
    return any(kw in t for kw in TARGET_ROLE_KEYWORDS)


# ─── SOURCE 1: jobspy (LinkedIn / Indeed / Glassdoor / ZipRecruiter) ─────────

def crawl_jobspy() -> list[dict]:
    if not JOBSPY_AVAILABLE:
        return []

    results = []
    sites = ["linkedin", "indeed", "glassdoor", "zip_recruiter"]

    for query in SEARCH_QUERIES:
        for location in SEARCH_LOCATIONS:
            try:
                logger.info(f"[jobspy] query='{query}' location='{location}'")
                df = scrape_jobs(
                    site_name=sites,
                    search_term=query,
                    location=location if location != "Remote" else None,
                    is_remote=True if location == "Remote" or REMOTE_ONLY else None,
                    results_wanted=RESULTS_PER_QUERY,
                    hours_old=26,          # slightly over 24h to avoid edge-case misses
                    country_indeed="USA",
                    linkedin_fetch_description=True,
                )

                for _, row in df.iterrows():
                    title = str(row.get("title", ""))
                    if not _title_matches(title):
                        continue
                    results.append(_normalize_job(
                        title=title,
                        company=str(row.get("company", "")),
                        location=str(row.get("location", "")),
                        url=str(row.get("job_url", "")),
                        description=str(row.get("description", "")),
                        source=str(row.get("site", "jobspy")),
                        date_posted=str(row.get("date_posted", "")),
                        job_type=str(row.get("job_type", "Full-time")),
                        is_remote=bool(row.get("is_remote", False)),
                    ))

                time.sleep(3)   # be polite between queries

            except Exception as e:
                logger.warning(f"[jobspy] Failed for '{query}' / '{location}': {e}")

    logger.info(f"[jobspy] {len(results)} jobs collected")
    return results


# ─── SOURCE 2: Greenhouse ATS ────────────────────────────────────────────────

def crawl_greenhouse() -> list[dict]:
    results = []
    base = "https://boards.greenhouse.io/api/v1/boards/{slug}/jobs"

    for slug in GREENHOUSE_COMPANIES:
        try:
            url = base.format(slug=slug)
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"[greenhouse] {slug}: HTTP {resp.status_code}")
                continue

            jobs = resp.json().get("jobs", [])
            for job in jobs:
                title = job.get("title", "")
                if not _title_matches(title):
                    continue

                # Fetch full description
                desc = ""
                detail_url = f"https://boards.greenhouse.io/api/v1/boards/{slug}/jobs/{job.get('id')}"
                try:
                    detail = requests.get(detail_url, timeout=10).json()
                    desc = re.sub(r"<[^>]+>", " ", detail.get("content", ""))
                except Exception:
                    pass

                location = job.get("location", {}).get("name", "")
                apply_url = job.get("absolute_url", f"https://boards.greenhouse.io/{slug}/jobs/{job.get('id')}")

                results.append(_normalize_job(
                    title=title,
                    company=slug.replace("-", " ").title(),
                    location=location,
                    url=apply_url,
                    description=desc,
                    source="greenhouse",
                ))
                time.sleep(0.3)

        except Exception as e:
            logger.warning(f"[greenhouse] {slug}: {e}")

    logger.info(f"[greenhouse] {len(results)} jobs collected")
    return results


# ─── SOURCE 3: Lever ATS ─────────────────────────────────────────────────────

def crawl_lever() -> list[dict]:
    results = []
    base = "https://api.lever.co/v0/postings/{slug}?mode=json"

    for slug in LEVER_COMPANIES:
        try:
            url = base.format(slug=slug)
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"[lever] {slug}: HTTP {resp.status_code}")
                continue

            jobs = resp.json()
            for job in jobs:
                title = job.get("text", "")
                if not _title_matches(title):
                    continue

                desc_parts = job.get("descriptionBody", {})
                desc = " ".join(
                    re.sub(r"<[^>]+>", " ", v)
                    for v in (desc_parts.values() if isinstance(desc_parts, dict) else [])
                )
                location = job.get("categories", {}).get("location", "")
                apply_url = job.get("hostedUrl", "")

                results.append(_normalize_job(
                    title=title,
                    company=slug.replace("-", " ").title(),
                    location=location,
                    url=apply_url,
                    description=desc,
                    source="lever",
                ))

        except Exception as e:
            logger.warning(f"[lever] {slug}: {e}")

    logger.info(f"[lever] {len(results)} jobs collected")
    return results


# ─── SOURCE 4: RemoteOK ───────────────────────────────────────────────────────

def crawl_remoteok() -> list[dict]:
    results = []
    headers = {"User-Agent": "JobCrawler/1.0 (personal automation)"}

    for tag in REMOTEOK_TAGS:
        try:
            url = f"https://remoteok.com/api?tag={tag}"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue

            jobs = resp.json()
            # First element is a metadata dict, skip it
            for job in jobs[1:]:
                if not isinstance(job, dict):
                    continue
                title = job.get("position", "")
                if not _title_matches(title):
                    continue

                results.append(_normalize_job(
                    title=title,
                    company=job.get("company", ""),
                    location="Remote",
                    url=job.get("url", f"https://remoteok.com/remote-jobs/{job.get('id')}"),
                    description=re.sub(r"<[^>]+>", " ", job.get("description", "")),
                    source="remoteok",
                    is_remote=True,
                ))

            time.sleep(1)

        except Exception as e:
            logger.warning(f"[remoteok] tag={tag}: {e}")

    logger.info(f"[remoteok] {len(results)} jobs collected")
    return results


# ─── SOURCE 5: We Work Remotely (RSS) ────────────────────────────────────────

def crawl_weworkremotely() -> list[dict]:
    results = []
    try:
        feed = feedparser.parse(WWR_RSS_URL)
        for entry in feed.entries:
            title = entry.get("title", "")
            # WWR title format: "Company: Job Title"
            if ":" in title:
                company, job_title = title.split(":", 1)
            else:
                company, job_title = "", title

            if not _title_matches(job_title):
                continue

            desc = re.sub(r"<[^>]+>", " ", entry.get("summary", ""))
            url = entry.get("link", "")
            date = entry.get("published", "")

            results.append(_normalize_job(
                title=job_title.strip(),
                company=company.strip(),
                location="Remote",
                url=url,
                description=desc,
                source="weworkremotely",
                date_posted=date,
                is_remote=True,
            ))

    except Exception as e:
        logger.warning(f"[weworkremotely] {e}")

    logger.info(f"[weworkremotely] {len(results)} jobs collected")
    return results


# ─── DEDUPLICATION ───────────────────────────────────────────────────────────

def deduplicate(jobs: list[dict], seen_ids_file: str = None) -> list[dict]:
    """Remove jobs seen in previous runs and jobs duplicated within this batch."""
    from pathlib import Path
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    if seen_ids_file is None:
        seen_ids_file = output_dir / "seen_ids.txt"

    # Load previously seen IDs
    seen = set()
    if os.path.exists(seen_ids_file):
        with open(seen_ids_file) as f:
            seen = set(line.strip() for line in f if line.strip())

    fresh = []
    batch_ids = set()
    for job in jobs:
        jid = job["id"]
        if jid not in seen and jid not in batch_ids:
            fresh.append(job)
            batch_ids.add(jid)

    # Persist new IDs
    with open(seen_ids_file, "a") as f:
        for jid in batch_ids:
            f.write(jid + "\n")

    logger.info(f"[dedup] {len(jobs)} raw → {len(fresh)} new jobs")
    return fresh


# ─── MAIN ENTRY POINT ────────────────────────────────────────────────────────

def crawl_all() -> list[dict]:
    all_jobs = []
    all_jobs.extend(crawl_jobspy())
    all_jobs.extend(crawl_greenhouse())
    all_jobs.extend(crawl_lever())
    all_jobs.extend(crawl_remoteok())
    all_jobs.extend(crawl_weworkremotely())

    logger.info(f"[crawl] total raw jobs: {len(all_jobs)}")
    return deduplicate(all_jobs)
