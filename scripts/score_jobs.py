"""
score_jobs.py
Two-stage scoring pipeline:
  Stage 1: Fast keyword + experience pre-filter (free)
  Stage 2: Claude 0-100 match scoring (API call per surviving job)

Jobs must score ≥ MIN_MATCH_SCORE (default 85) to make the digest.
"""

import os
import re
import json
import logging
import time
from typing import Optional

import anthropic

from config import (
    YEARS_OF_EXPERIENCE,
    EXCLUDE_KEYWORDS,
    BELOW_LEVEL_PATTERNS,
    TIER_1_AI_COMPANIES,
    MIN_YOE_GENERAL,
    MIN_YOE_TIER1,
    MIN_MATCH_SCORE,
)

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ─── STAGE 1: KEYWORD / EXPERIENCE PRE-FILTER ────────────────────────────────

def _is_excluded_keyword(job: dict) -> bool:
    text = (job["title"] + " " + job["description"]).lower()
    return any(kw in text for kw in EXCLUDE_KEYWORDS)


def _is_too_junior(job: dict) -> bool:
    """Returns True if the JD explicitly asks for too few years of experience."""
    desc = job["description"].lower()
    for pattern in BELOW_LEVEL_PATTERNS:
        if re.search(pattern, desc, re.IGNORECASE):
            return True
    return False


def _is_tier1(job: dict) -> bool:
    company = job["company"].lower()
    return any(t1 in company for t1 in TIER_1_AI_COMPANIES)


def _required_yoe(job: dict) -> Optional[int]:
    """Try to parse the minimum years of experience stated in the JD."""
    desc = job["description"]
    # patterns like "7+ years", "8-10 years", "minimum 6 years"
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
            logger.debug(f"[prefilter] EXCLUDE keyword: {job['title']} @ {job['company']}")
            continue

        if _is_too_junior(job):
            logger.debug(f"[prefilter] EXCLUDE too junior: {job['title']} @ {job['company']}")
            continue

        tier1 = _is_tier1(job)
        min_yoe = MIN_YOE_TIER1 if tier1 else MIN_YOE_GENERAL
        required = _required_yoe(job)

        if required is not None and required < min_yoe:
            logger.debug(
                f"[prefilter] EXCLUDE yoe<{min_yoe}: {job['title']} @ {job['company']} "
                f"(requires {required}y, tier1={tier1})"
            )
            continue

        job["is_tier1"] = tier1
        kept.append(job)

    logger.info(f"[prefilter] {len(jobs)} → {len(kept)} jobs after keyword/experience filter")
    return kept


# ─── STAGE 2: CLAUDE MATCH SCORING ───────────────────────────────────────────

SCORING_PROMPT = """You are a technical recruiter helping a candidate evaluate job fit.

## Candidate Resume
{resume}

## Job Posting
Title: {title}
Company: {company}
Location: {location}
Description:
{description}

## Task
Score how well this job matches the candidate on a scale of 0–100, where:
- 90–100: Near-perfect match (title, seniority, stack, domain all align)
- 80–89:  Strong match (most requirements fit, 1-2 minor gaps)
- 70–79:  Moderate match (relevant domain but some meaningful gaps)
- <70:    Weak or mismatched

Return ONLY valid JSON in exactly this format (no prose, no markdown):
{{
  "score": <integer 0-100>,
  "match_reasons": ["<reason 1>", "<reason 2>", "<reason 3>"],
  "gaps": ["<gap 1>", "<gap 2>"],
  "seniority_fit": "<over/under/good fit>",
  "summary": "<one sentence>"
}}"""


def score_with_claude(job: dict, resume: str) -> dict:
    prompt = SCORING_PROMPT.format(
        resume=resume[:6000],          # guard against huge resumes
        title=job["title"],
        company=job["company"],
        location=job["location"],
        description=job["description"][:4000],
    )

    try:
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()

        # Strip any accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"[score] JSON parse error for {job['title']} @ {job['company']}: {e}")
        return {"score": 0, "match_reasons": [], "gaps": [], "seniority_fit": "unknown", "summary": "Parse error"}
    except Exception as e:
        logger.warning(f"[score] Claude error for {job['title']} @ {job['company']}: {e}")
        return {"score": 0, "match_reasons": [], "gaps": [], "seniority_fit": "unknown", "summary": str(e)}


def score_all(jobs: list[dict], resume: str) -> list[dict]:
    scored = []

    for i, job in enumerate(jobs):
        logger.info(f"[score] {i+1}/{len(jobs)} — {job['title']} @ {job['company']}")
        result = score_with_claude(job, resume)

        job["score"]         = result.get("score", 0)
        job["match_reasons"] = result.get("match_reasons", [])
        job["gaps"]          = result.get("gaps", [])
        job["seniority_fit"] = result.get("seniority_fit", "")
        job["score_summary"] = result.get("summary", "")

        if job["score"] >= MIN_MATCH_SCORE:
            scored.append(job)
            logger.info(f"  ✓ score={job['score']} — KEPT")
        else:
            logger.info(f"  ✗ score={job['score']} — DROPPED (< {MIN_MATCH_SCORE})")

        time.sleep(0.5)    # light rate-limit buffer

    scored.sort(key=lambda j: j["score"], reverse=True)
    logger.info(f"[score] {len(scored)} jobs passed ≥{MIN_MATCH_SCORE} threshold")
    return scored
