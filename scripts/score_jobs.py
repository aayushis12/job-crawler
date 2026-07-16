"""
score_jobs.py
Two-stage scoring pipeline:
  Stage 1: Fast keyword + experience pre-filter (free)
  Stage 2: LLM batch scoring — 5 jobs per API call to stay within Groq free TPD

Jobs must score ≥ MIN_MATCH_SCORE (default 85) to make the digest.
"""

import os
import re
import json
import logging
import time
from typing import Optional

from openai import OpenAI

from config import (
    YEARS_OF_EXPERIENCE,
    EXCLUDE_KEYWORDS,
    BELOW_LEVEL_PATTERNS,
    TIER_1_AI_COMPANIES,
    MIN_YOE_GENERAL,
    MIN_YOE_TIER1,
    MIN_MATCH_SCORE,
    INTERNATIONAL_LOCATIONS,
    VISA_SPONSORSHIP_KEYWORDS,
)

logger = logging.getLogger(__name__)
client = OpenAI(
    api_key=os.environ["LLAMA_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)

BATCH_SIZE = 5   # jobs per API call — keeps token cost low on free tier


# ─── STAGE 1: KEYWORD / EXPERIENCE PRE-FILTER ────────────────────────────────

def _is_excluded_keyword(job: dict) -> bool:
    text = (job["title"] + " " + job["description"]).lower()
    return any(kw in text for kw in EXCLUDE_KEYWORDS)


def _is_too_junior(job: dict) -> bool:
    desc = job["description"].lower()
    for pattern in BELOW_LEVEL_PATTERNS:
        if re.search(pattern, desc, re.IGNORECASE):
            return True
    return False


def _is_tier1(job: dict) -> bool:
    company = job["company"].lower()
    return any(t1 in company for t1 in TIER_1_AI_COMPANIES)


def _is_international(job: dict) -> bool:
    location = job.get("location", "").lower()
    return any(intl in location for intl in INTERNATIONAL_LOCATIONS)


def _sponsors_visa(job: dict) -> bool:
    text = (job.get("description", "") + " " + job.get("title", "")).lower()
    return any(kw in text for kw in VISA_SPONSORSHIP_KEYWORDS)


def _required_yoe(job: dict) -> Optional[int]:
    desc = job["description"]
    patterns = [
        r"(\d+)\+\s*years?",
        r"(\d+)[-–]\d+\s*years?",
        r"minimum\s+(\d+)\s*years?",
        r"at\s+least\s+(\d+)\s*years?",
    ]
    values = []
    for p in patterns:
        for m in re.finditer(p, desc, re.IGNORECASE):
            values.append(int(m.group(1)))
    return min(values) if values else None


def keyword_prefilter(jobs: list[dict]) -> list[dict]:
    kept = []
    for job in jobs:
        if _is_excluded_keyword(job):
            continue
        if _is_too_junior(job):
            continue
        if _is_international(job) and not _sponsors_visa(job):
            continue

        tier1 = _is_tier1(job)
        min_yoe = MIN_YOE_TIER1 if tier1 else MIN_YOE_GENERAL
        required = _required_yoe(job)

        if required is not None and required < min_yoe:
            continue

        job["is_tier1"] = tier1
        job["visa_sponsored"] = _is_international(job) and _sponsors_visa(job)
        kept.append(job)

    logger.info(f"[prefilter] {len(jobs)} → {len(kept)} jobs after keyword/experience filter")
    return kept


# ─── STAGE 2: BATCH LLM SCORING ──────────────────────────────────────────────

BATCH_PROMPT = """You are a technical recruiter scoring job fit for a senior ML/AI engineer.

## Candidate Summary (10 YOE, focus: LLM, Applied AI, Search, Agentic AI)
{resume_summary}

## Jobs to Score
{jobs_block}

## Instructions
Score each job 0-100:
- 90-100: near-perfect match (title, seniority, domain, stack all align)
- 80-89:  strong match (most requirements fit, 1-2 minor gaps)
- 70-79:  moderate match (relevant domain, some meaningful gaps)
- <70:    weak or mismatched

Return ONLY a valid JSON array with exactly {n} objects, in order, no prose:
[
  {{"job_id": 0, "score": <int>, "match_reasons": ["<r1>", "<r2>"], "gaps": ["<g1>"], "seniority_fit": "<over/under/good>", "summary": "<one sentence>"}},
  ...
]"""


def _score_batch(jobs: list[dict], resume: str) -> list[dict]:
    """Score a batch of jobs in a single API call. Returns list of result dicts."""
    resume_summary = resume[:2000]   # first 2k chars covers summary + recent experience

    jobs_block = "\n\n".join(
        f"[Job {i}]\nTitle: {j['title']}\nCompany: {j['company']}\n"
        f"Location: {j['location']}\nDescription: {j['description'][:1000]}"
        for i, j in enumerate(jobs)
    )

    prompt = BATCH_PROMPT.format(
        resume_summary=resume_summary,
        jobs_block=jobs_block,
        n=len(jobs),
    )

    try:
        msg = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=256 * len(jobs),   # ~256 tokens per job result
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        results = json.loads(raw)
        if not isinstance(results, list):
            raise ValueError("Response is not a JSON array")
        return results

    except Exception as e:
        logger.warning(f"[score] Batch error: {e}")
        return [
            {"job_id": i, "score": 0, "match_reasons": [], "gaps": [],
             "seniority_fit": "unknown", "summary": f"Batch error: {e}"}
            for i in range(len(jobs))
        ]


def score_all(jobs: list[dict], resume: str) -> list[dict]:
    scored = []
    total  = len(jobs)
    batches = [jobs[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

    logger.info(f"[score] Scoring {total} jobs in {len(batches)} batches of ≤{BATCH_SIZE}")

    for b_idx, batch in enumerate(batches):
        logger.info(f"[score] Batch {b_idx+1}/{len(batches)} ({len(batch)} jobs)...")
        results = _score_batch(batch, resume)

        for job, result in zip(batch, results):
            job["score"]         = result.get("score", 0)
            job["match_reasons"] = result.get("match_reasons", [])
            job["gaps"]          = result.get("gaps", [])
            job["seniority_fit"] = result.get("seniority_fit", "")
            job["score_summary"] = result.get("summary", "")

            status = "✓ KEPT" if job["score"] >= MIN_MATCH_SCORE else f"✗ DROPPED (< {MIN_MATCH_SCORE})"
            logger.info(f"  score={job['score']} {status} — {job['title']} @ {job['company']}")

            if job["score"] >= MIN_MATCH_SCORE:
                scored.append(job)

        time.sleep(1)   # brief pause between batches

    scored.sort(key=lambda j: j["score"], reverse=True)
    logger.info(f"[score] {len(scored)} jobs passed ≥{MIN_MATCH_SCORE} threshold")
    return scored
