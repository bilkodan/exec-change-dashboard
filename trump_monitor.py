"""
Monitors Trump's Truth Social feed for US investment mentions in public companies.
Sends Gmail email alerts when a match is found.
Run as a standalone background process (alongside monitor.py on Railway).
"""

import feedparser
import html
import logging
import os
import re
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import Db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [trump] %(message)s")
log = logging.getLogger(__name__)

TRUTH_SOCIAL_RSS = "https://truthsocial.com/@realDonaldTrump.rss"
POLL_INTERVAL = 300  # 5 minutes

INVESTMENT_RE = re.compile(
    r"\b(?:invest(?:ment|ing|ed|s)?|deal|commit(?:ment|ted)?|manufactur(?:ing|e|ed)|"
    r"factor(?:y|ies)|facilit(?:y|ies)|plant|build(?:ing)?|headquarter(?:s|ing)?|"
    r"billion|million|trillion|partnership|acqui(?:re|sition)|bring(?:ing)?\s+jobs|"
    r"relocat(?:e|ing|ion)|reshore|onshore|domestic\s+production)\b",
    re.IGNORECASE,
)

TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b")

WELL_KNOWN_COMPANIES = {
    "Apple", "Microsoft", "Google", "Alphabet", "Amazon", "Meta", "Tesla",
    "Nvidia", "Intel", "AMD", "Qualcomm", "TSMC", "Samsung", "Ford",
    "General Motors", "GM", "Boeing", "Lockheed", "Raytheon", "ExxonMobil",
    "Chevron", "JPMorgan", "Goldman Sachs", "Morgan Stanley", "Walmart",
    "Target", "Home Depot", "Costco", "Disney", "Netflix", "Uber", "Lyft",
    "Airbnb", "Palantir", "SoftBank", "Toyota", "Honda", "Hyundai",
    "Volkswagen", "BMW", "Mercedes", "Shell", "BP", "US Steel",
    "United States Steel", "Nucor", "Alcoa", "Stellantis", "Rivian",
    "Lucid", "Oracle", "Salesforce", "Cisco", "IBM", "Dell",
    "AT&T", "Verizon", "T-Mobile", "Comcast", "FedEx", "UPS",
    "Caterpillar", "Deere", "United Airlines", "Delta", "Southwest",
    "American Airlines", "Pfizer", "Moderna", "Johnson & Johnson",
    "AstraZeneca", "Abbott", "Merck", "Eli Lilly", "Bristol-Myers",
    "Eaton", "Honeywell", "3M", "GE", "Emerson", "Carrier", "Otis",
    "X", "Twitter", "OpenAI", "Anthropic",
}

# Build a single regex for company name matching (case-insensitive)
_COMPANY_RE = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in sorted(WELL_KNOWN_COMPANIES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def _strip_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    return html.unescape(text).strip()


def extract_companies(text: str) -> list[str]:
    found = []
    for m in TICKER_RE.finditer(text):
        found.append(f"${m.group(1)}")
    for m in _COMPANY_RE.finditer(text):
        found.append(m.group(1))
    # deduplicate preserving order
    seen: set[str] = set()
    result = []
    for item in found:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def send_email_alert(post_url: str, post_text: str, companies: list[str], published: str) -> None:
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")
    alert_email = os.environ.get("ALERT_EMAIL")

    if not all([gmail_user, gmail_pass, alert_email]):
        log.warning("Skipping email — GMAIL_USER, GMAIL_APP_PASSWORD, or ALERT_EMAIL not set")
        return

    company_str = ", ".join(companies) if companies else "public company"
    subject = f"Trump Investment Alert: {company_str}"

    body_html = f"""
<h2 style="color:#c53030">🇺🇸 Trump Investment Mention Detected</h2>
<p><strong>Published:</strong> {html.escape(published)}</p>
<p><strong>Companies / Tickers:</strong> {html.escape(company_str)}</p>
<hr>
<blockquote style="border-left:4px solid #e53e3e;padding-left:12px;color:#333;font-size:14px">
  {html.escape(post_text)}
</blockquote>
<p><a href="{post_url}">View original post on Truth Social</a></p>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = alert_email
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, alert_email, msg.as_string())
        log.info(f"Email sent → {alert_email} | {subject}")
    except Exception as exc:
        log.error(f"Email send failed: {exc}")


def process_feed() -> None:
    feed = feedparser.parse(TRUTH_SOCIAL_RSS)

    if feed.bozo:
        log.warning(f"RSS parse warning: {feed.bozo_exception}")

    for entry in feed.entries:
        post_id = entry.get("id") or entry.get("link", "")
        if not post_id:
            continue

        if Db.trump_post_seen(post_id):
            continue

        raw = entry.get("summary") or ""
        if not raw and entry.get("content"):
            raw = entry["content"][0].get("value", "")

        text = _strip_html(raw)
        published = entry.get("published", str(datetime.utcnow()))
        post_url = entry.get("link", "")

        if INVESTMENT_RE.search(text):
            companies = extract_companies(text)
            log.info(f"Investment mention → companies={companies} text={text[:120]!r}")

            Db.insert_trump_alert({
                "id": post_id,
                "text": text,
                "post_url": post_url,
                "published": published,
                "companies": ", ".join(companies),
                "alerted_at": str(datetime.utcnow()),
            })
            send_email_alert(post_url, text, companies, published)
        else:
            Db.mark_trump_seen(post_id)


def run() -> None:
    Db.init_db()
    Db.init_trump_alerts()
    log.info("Trump investment monitor started — polling every 5 minutes")

    while True:
        try:
            process_feed()
        except Exception as exc:
            log.error(f"Feed processing error: {exc}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
