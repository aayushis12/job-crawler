"""
notion_tracker.py
Logs each matched job to a Notion database.

Required GitHub Secrets:
  NOTION_API_KEY      — Integration token (secret_...)
  NOTION_DATABASE_ID  — ID of the target database

Database properties expected (names configurable in config.py → NOTION_PROPS):
  Job Title        Title
  Company          Rich text
  Location         Rich text
  Match Score      Number
  Application URL  URL
  Status           Select  (options: New, Reviewing, Applied, Rejected, Interviewing, Offer)
  Date Found       Date
  Source           Select
  Type             Select  (Full-time, Contract, etc.)
  Tier-1 Company   Checkbox
"""

import os
import logging
from datetime import datetime, timezone

from notion_client import Client, APIErrorCode, APIResponseError

from config import NOTION_PROPS, NOTION_DEFAULT_STATUS

logger = logging.getLogger(__name__)


def _get_client() -> Client:
    return Client(auth=os.environ["NOTION_API_KEY"])


def _get_db_id() -> str:
    return os.environ["NOTION_DATABASE_ID"]


# ─── CHECK FOR EXISTING ENTRY ─────────────────────────────────────────────────

def _already_tracked(client: Client, db_id: str, job: dict) -> bool:
    """Return True if a page with the same title + company already exists."""
    try:
        resp = client.databases.query(
            **{
                "database_id": db_id,
                "filter": {
                    "and": [
                        {
                            "property": NOTION_PROPS["title"],
                            "title": {"equals": job["title"]},
                        },
                        {
                            "property": NOTION_PROPS["company"],
                            "rich_text": {"equals": job["company"]},
                        },
                    ]
                },
            }
        )
        return len(resp.get("results", [])) > 0
    except Exception as e:
        logger.warning(f"[notion] duplicate-check error: {e}")
        return False


# ─── BUILD PAGE PROPERTIES ───────────────────────────────────────────────────

def _build_properties(job: dict) -> dict:
    p = NOTION_PROPS
    return {
        p["title"]: {
            "title": [{"text": {"content": job["title"]}}]
        },
        p["company"]: {
            "rich_text": [{"text": {"content": job["company"]}}]
        },
        p["location"]: {
            "rich_text": [{"text": {"content": job["location"]}}]
        },
        p["score"]: {
            "number": job.get("score", 0)
        },
        p["url"]: {
            "url": job["url"] or None
        },
        p["status"]: {
            "select": {"name": NOTION_DEFAULT_STATUS}
        },
        p["date_found"]: {
            "date": {"start": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
        },
        p["source"]: {
            "select": {"name": job.get("source", "unknown")}
        },
        p["job_type"]: {
            "select": {"name": job.get("job_type", "Full-time")}
        },
        p["tier1"]: {
            "checkbox": bool(job.get("is_tier1", False))
        },
    }


# ─── BUILD PAGE CONTENT (CHILDREN BLOCKS) ────────────────────────────────────

def _text_block(heading: str, content: str) -> list[dict]:
    """Return a heading + paragraph block list."""
    blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": heading}}]
            },
        }
    ]
    # Notion block text is capped at 2000 chars per block
    chunks = [content[i:i+1999] for i in range(0, len(content), 1999)]
    for chunk in chunks:
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            },
        })
    return blocks


def _build_children(job: dict) -> list[dict]:
    children = []

    # Score summary callout
    summary = job.get("score_summary", "")
    if summary:
        children.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"Score {job.get('score')}% — {summary}"}}],
                "icon": {"emoji": "🎯"},
            },
        })

    # Match reasons
    reasons = job.get("match_reasons", [])
    if reasons:
        children.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": "✅ Match Reasons"}}]},
        })
        for r in reasons:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": r}}]
                },
            })

    # Gaps
    gaps = job.get("gaps", [])
    if gaps:
        children.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": "⚠️ Gaps"}}]},
        })
        for g in gaps:
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": g}}]
                },
            })

    # Cover letter
    cl = job.get("cover_letter", "")
    if cl:
        children.extend(_text_block("📝 Cover Letter", cl))

    # Tailored resume
    tr = job.get("tailored_resume", "")
    if tr:
        children.extend(_text_block("📄 Tailored Resume", tr))

    # Original job description
    desc = job.get("description", "")
    if desc:
        children.extend(_text_block("🔍 Job Description", desc[:3000]))

    return children


# ─── CREATE PAGE ──────────────────────────────────────────────────────────────

def _create_page(client: Client, db_id: str, job: dict) -> str:
    """Create a Notion page and return its URL."""
    page = client.pages.create(
        parent={"database_id": db_id},
        properties=_build_properties(job),
        children=_build_children(job),
    )
    return page.get("url", "")


# ─── PUBLIC API ──────────────────────────────────────────────────────────────

def track_jobs(jobs: list[dict]) -> list[dict]:
    """
    Add each job to Notion, skipping duplicates.
    Attaches 'notion_url' to each job dict.
    """
    client = _get_client()
    db_id  = _get_db_id()
    tracked = 0

    for job in jobs:
        try:
            if _already_tracked(client, db_id, job):
                logger.info(f"[notion] SKIP (exists): {job['title']} @ {job['company']}")
                job["notion_url"] = ""
                continue

            url = _create_page(client, db_id, job)
            job["notion_url"] = url
            tracked += 1
            logger.info(f"[notion] ADDED: {job['title']} @ {job['company']} → {url}")

        except APIResponseError as e:
            logger.error(f"[notion] API error for {job['title']}: {e}")
            job["notion_url"] = ""
        except Exception as e:
            logger.error(f"[notion] Unexpected error: {e}")
            job["notion_url"] = ""

    logger.info(f"[notion] {tracked}/{len(jobs)} jobs added to Notion")
    return jobs
