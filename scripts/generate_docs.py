"""
generate_docs.py
For each top-matched job, uses Claude to:
  1. Generate a tailored resume (restructured bullet points / summary)
  2. Generate a personalized cover letter
Both are stored as plain text in the job dict for email / Notion.
"""

import os
import re
import time
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI(
    api_key=os.environ["LLAMA_API_KEY"],
    base_url="https://api.llama.com/v1",
)


# ─── PROMPTS ─────────────────────────────────────────────────────────────────

RESUME_PROMPT = """You are an expert technical resume writer.

## Candidate's Base Resume
{resume}

## Target Job
Title: {title}
Company: {company}
Job Description:
{description}

## Task
Rewrite the candidate's resume to be maximally tailored for this specific role.
- Keep all factual information accurate — do NOT invent experience or skills.
- Reorder bullet points to lead with the most relevant accomplishments.
- Rewrite the professional summary (3–4 sentences) to directly address this role.
- Highlight keywords from the JD that the candidate's background genuinely supports.
- Use strong action verbs and quantified impacts where present.
- Output the full tailored resume as plain text, ready to paste into a document.

Begin output with "PROFESSIONAL SUMMARY" and end with a line "---END---"."""


COVER_LETTER_PROMPT = """You are an expert cover letter writer for senior tech roles.

## Candidate's Resume
{resume}

## Target Job
Title: {title}
Company: {company}
Job Description:
{description}

## Task
Write a compelling, personalized cover letter (3–4 short paragraphs, ~300 words).
- Opening: specific hook about why THIS company and THIS role.
- Body: 2 concrete examples from the candidate's resume that directly address key JD requirements.
- Closing: call to action, enthusiasm, professional sign-off.
- Tone: confident, direct, no clichés like "I am writing to express my interest".
- Do NOT add a date, address block, or "[Your Name]" placeholder — output body text only.

Begin with "Dear Hiring Manager," and end with "Sincerely,\n[Name]"."""


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _call_claude(prompt: str, max_tokens: int = 1800) -> str:
    try:
        message = client.chat.completions.create(
            model="Llama-4-Maverick-17B-128E-Instruct-FP8",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"[generate] Claude error: {e}")
        return f"[Generation failed: {e}]"


def _extract_resume(raw: str) -> str:
    """Strip the ---END--- sentinel if present."""
    if "---END---" in raw:
        raw = raw[:raw.index("---END---")]
    return raw.strip()


# ─── PUBLIC API ──────────────────────────────────────────────────────────────

def generate_tailored_resume(job: dict, resume: str) -> str:
    logger.info(f"[generate] tailored resume for {job['title']} @ {job['company']}")
    prompt = RESUME_PROMPT.format(
        resume=resume[:6000],
        title=job["title"],
        company=job["company"],
        description=job["description"][:4000],
    )
    raw = _call_claude(prompt, max_tokens=2000)
    return _extract_resume(raw)


def generate_cover_letter(job: dict, resume: str) -> str:
    logger.info(f"[generate] cover letter for {job['title']} @ {job['company']}")
    prompt = COVER_LETTER_PROMPT.format(
        resume=resume[:5000],
        title=job["title"],
        company=job["company"],
        description=job["description"][:3500],
    )
    return _call_claude(prompt, max_tokens=700)


def generate_all(jobs: list[dict], resume: str) -> list[dict]:
    """Attach tailored_resume and cover_letter to each job dict."""
    for i, job in enumerate(jobs):
        logger.info(f"[generate] {i+1}/{len(jobs)} — {job['title']} @ {job['company']}")
        job["tailored_resume"] = generate_tailored_resume(job, resume)
        time.sleep(1)
        job["cover_letter"]    = generate_cover_letter(job, resume)
        time.sleep(1)

    return jobs
