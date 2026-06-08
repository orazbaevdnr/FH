"""
FL.ru parser — reads the public RSS feed (no auth required).

FL.ru provides RSS at: https://www.fl.ru/rss/all.xml
Each <item> contains title, link, description, pubDate.
Price is usually embedded in the description text.
"""

import re
import time
import datetime
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://www.fl.ru/rss/all.xml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}

# Matches: "500 руб", "1 500 руб", "$200", "от 300"
_PRICE_RE = re.compile(
    r"(?:от\s*)?(\d[\d\s]{1,6})\s*(?:руб(?:лей)?|₽|\$)", re.IGNORECASE
)


def _extract_price(text: str) -> int:
    """Return price in USD (rough conversion 1$ ≈ 90 ₽)."""
    m = _PRICE_RE.search(text or "")
    if not m:
        return 0
    raw = int(re.sub(r"\s", "", m.group(1)))
    # Heuristic: values < 500 are likely already in USD
    if raw <= 500:
        return raw
    return raw // 90


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def parse_fl(max_items: int = 50) -> list[dict]:
    """Fetch and parse FL.ru RSS. Returns list of job dicts with status='pending'."""
    try:
        req = urllib.request.Request(RSS_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        print(f"[FL] RSS fetch error: {e}")
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[FL] XML parse error: {e}")
        return []

    jobs = []
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}

    for item in root.iter("item"):
        if len(jobs) >= max_items:
            break

        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        raw_desc = item.findtext("description") or ""
        description = _strip_html(raw_desc)[:600]
        pub_date = item.findtext("pubDate") or ""

        if not title or not url:
            continue

        # Derive a stable ID from the URL
        job_id = "fl_" + re.sub(r"[^0-9a-zA-Z]", "_", url.split("//")[-1])[:40]

        price = _extract_price(raw_desc) or _extract_price(title)

        # Parse pubDate → ISO timestamp (best-effort)
        try:
            dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            created_at = dt.isoformat()
        except (ValueError, TypeError):
            created_at = datetime.datetime.utcnow().isoformat() + "Z"

        jobs.append({
            "id": job_id,
            "platform": "fl.ru",
            "title": title,
            "description": description,
            "price": price,
            "url": url,
            "status": "pending",
            "score": 0,
            "reason": "",
            "created_at": created_at,
        })

    return jobs
