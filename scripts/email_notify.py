"""
email_notify.py
Sends a styled HTML digest email via Gmail SMTP (App Password).

Required GitHub Secrets:
  GMAIL_USER           — your Gmail address (sender)
  GMAIL_APP_PASSWORD   — 16-char Google App Password
  NOTIFICATION_EMAIL   — destination email (can be the same as GMAIL_USER)
"""

import os
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import EMAIL_SUBJECT, MAX_JOBS_IN_EMAIL

logger = logging.getLogger(__name__)


# ─── SCORE COLOUR ────────────────────────────────────────────────────────────

def _score_color(score: int) -> str:
    if score >= 95: return "#00875A"   # dark green
    if score >= 88: return "#2E7D32"   # green
    if score >= 85: return "#F57C00"   # amber
    return "#C62828"                   # red (shouldn't appear — filtered out)


def _score_badge(score: int) -> str:
    color = _score_color(score)
    return (
        f'<span style="background:{color};color:#fff;padding:3px 10px;'
        f'border-radius:12px;font-weight:bold;font-size:13px;">{score}%</span>'
    )


# ─── JOB CARD HTML ───────────────────────────────────────────────────────────

def _job_card(job: dict, index: int) -> str:
    tier1_badge = (
        '<span style="background:#6200EA;color:#fff;padding:2px 8px;'
        'border-radius:10px;font-size:11px;margin-left:8px;">Tier-1 AI</span>'
        if job.get("is_tier1") else ""
    )
    remote_badge = (
        '<span style="background:#0288D1;color:#fff;padding:2px 8px;'
        'border-radius:10px;font-size:11px;margin-left:8px;">Remote</span>'
        if job.get("is_remote") else ""
    )
    visa_badge = (
        '<span style="background:#00796B;color:#fff;padding:2px 8px;'
        'border-radius:10px;font-size:11px;margin-left:8px;">✈️ Visa Sponsored</span>'
        if job.get("visa_sponsored") else ""
    )

    match_reasons = "".join(
        f'<li style="margin:3px 0;color:#2E7D32;">✅ {r}</li>'
        for r in job.get("match_reasons", [])
    )
    gaps = "".join(
        f'<li style="margin:3px 0;color:#BF360C;">⚠️ {g}</li>'
        for g in job.get("gaps", [])
    )

    cl_preview = job.get("cover_letter", "")

    notion_link = ""
    if job.get("notion_url"):
        notion_link = (
            f'<a href="{job["notion_url"]}" style="margin-left:12px;'
            f'color:#6200EA;text-decoration:none;font-weight:bold;">📓 Open in Notion</a>'
        )

    return f"""
<div style="border:1px solid #E0E0E0;border-radius:10px;padding:20px;margin-bottom:24px;
            background:#FAFAFA;font-family:Arial,sans-serif;">

  <!-- Header -->
  <div style="margin-bottom:12px;">
    <span style="font-size:13px;color:#757575;">#{index} · {job.get('source','').upper()}</span>
    <div style="margin-top:6px;">
      {_score_badge(job.get('score', 0))} {tier1_badge} {remote_badge} {visa_badge}
    </div>
  </div>

  <h2 style="margin:0 0 4px 0;font-size:20px;color:#212121;">{job['title']}</h2>
  <p style="margin:0 0 4px 0;font-size:15px;color:#424242;font-weight:bold;">{job['company']}</p>
  <p style="margin:0 0 12px 0;font-size:13px;color:#757575;">📍 {job['location']} &nbsp;|&nbsp; {job.get('date_posted','')}</p>

  <!-- AI Summary -->
  <div style="background:#E8F5E9;border-left:4px solid #2E7D32;padding:10px 14px;
              border-radius:4px;margin-bottom:12px;">
    <p style="margin:0;font-size:14px;color:#1B5E20;">🎯 {job.get('score_summary','')}</p>
  </div>

  <!-- Match reasons + gaps -->
  <div style="display:flex;gap:24px;margin-bottom:12px;">
    <div style="flex:1;">
      <p style="margin:0 0 6px;font-weight:bold;font-size:13px;color:#212121;">Why it fits:</p>
      <ul style="margin:0;padding-left:18px;font-size:13px;">{match_reasons}</ul>
    </div>
    {"" if not gaps else f'''
    <div style="flex:1;">
      <p style="margin:0 0 6px;font-weight:bold;font-size:13px;color:#212121;">Gaps:</p>
      <ul style="margin:0;padding-left:18px;font-size:13px;">{gaps}</ul>
    </div>'''}
  </div>

  <!-- Cover letter preview -->
  <details style="margin-bottom:12px;">
    <summary style="cursor:pointer;font-weight:bold;font-size:13px;color:#212121;">
      📝 Cover Letter Preview
    </summary>
    <div style="background:#F3F4F6;border-radius:6px;padding:12px;margin-top:8px;
                font-size:13px;color:#374151;white-space:pre-wrap;line-height:1.6;">
{cl_preview}
    </div>
  </details>

  <!-- Action buttons -->
  <div style="margin-top:14px;">
    <a href="{job['url']}" style="background:#1976D2;color:#fff;padding:9px 18px;
       border-radius:6px;text-decoration:none;font-weight:bold;font-size:14px;">
      🚀 Apply Now
    </a>
    {notion_link}
  </div>

</div>
"""


# ─── FULL EMAIL HTML ─────────────────────────────────────────────────────────

def _build_html(jobs: list[dict], date_str: str) -> str:
    cards = "".join(_job_card(j, i + 1) for i, j in enumerate(jobs))
    total = len(jobs)

    return f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#F5F5F5;font-family:Arial,sans-serif;">

<div style="max-width:700px;margin:32px auto;background:#fff;border-radius:12px;
            box-shadow:0 2px 10px rgba(0,0,0,.08);overflow:hidden;">

  <!-- Top banner -->
  <div style="background:linear-gradient(135deg,#1976D2,#6200EA);padding:28px 32px;color:#fff;">
    <h1 style="margin:0;font-size:26px;">🎯 Daily Job Matches</h1>
    <p style="margin:6px 0 0;opacity:.85;font-size:15px;">
      {date_str} &nbsp;·&nbsp; {total} match{"es" if total!=1 else ""} above 85%
    </p>
  </div>

  <!-- Body -->
  <div style="padding:28px 32px;">
    {cards if jobs else
      '<p style="color:#757575;text-align:center;padding:40px 0;">No strong matches found today.</p>'}
  </div>

  <!-- Footer -->
  <div style="background:#F5F5F5;padding:16px 32px;border-top:1px solid #E0E0E0;
              font-size:12px;color:#9E9E9E;text-align:center;">
    Generated by your GitHub Actions job crawler &nbsp;·&nbsp;
    <a href="https://github.com" style="color:#1976D2;">View workflow</a>
  </div>

</div>
</body>
</html>
"""


# ─── SEND EMAIL ──────────────────────────────────────────────────────────────

def send_digest(jobs: list[dict]) -> None:
    jobs = jobs[:MAX_JOBS_IN_EMAIL]
    date_str = datetime.now().strftime("%B %d, %Y")
    subject  = EMAIL_SUBJECT.format(date=date_str)

    gmail_user  = os.environ["GMAIL_USER"]
    gmail_pass  = os.environ["GMAIL_APP_PASSWORD"]
    to_email    = os.environ.get("NOTIFICATION_EMAIL", gmail_user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_user
    msg["To"]      = to_email

    # Plain-text fallback
    plain_lines = []
    for i, j in enumerate(jobs):
        plain_lines.append(
            f"{i+1}. [{j.get('score')}%] {j['title']} @ {j['company']} — {j['url']}"
        )
    plain = f"Job Matches — {date_str}\n\n" + "\n".join(plain_lines)
    msg.attach(MIMEText(plain, "plain"))

    # HTML
    html = _build_html(jobs, date_str)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, to_email, msg.as_string())
        logger.info(f"[email] Digest sent to {to_email} ({len(jobs)} jobs)")
    except Exception as e:
        logger.error(f"[email] Failed to send: {e}")
        raise
