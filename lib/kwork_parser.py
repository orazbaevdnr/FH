"""
Kwork parser — RSS + HTML fallback.

Kwork projects RSS: https://kwork.ru/rss/projects
Each item has title, link, description, price in description text.
"""

import re
import datetime
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://kwork.ru/rss/projects"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "application/rss+xml, text/xml, */*",
}

_PRICE_RE = re.compile(r"(\d[\d\s]{1,7})\s*(?:руб(?:лей)?|₽|\$)", re.IGNORECASE)
_BUDGET_RE = re.compile(r"(?:бюджет|budget|цена|price)[^\d]*(\d[\d\s]{1,7})", re.IGNORECASE)


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text or "")
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_price(text: str) -> int:
    # Try budget/price keyword first for accuracy
    for pattern in [_BUDGET_RE, _PRICE_RE]:
        m = pattern.search(text or "")
        if m:
            raw = int(re.sub(r"\s", "", m.group(1)))
            if raw > 500:
                return raw // 90
            return raw
    return 0


def parse_kwork(max_items: int = 50) -> list:
    try:
        req = urllib.request.Request(RSS_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        print(f"[Kwork] fetch error: {e}")
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[Kwork] XML error: {e}")
        return []

    jobs = []
    for item in root.iter("item"):
        if len(jobs) >= max_items:
            break

        title    = (item.findtext("title") or "").strip()
        url      = (item.findtext("link") or "").strip()
        raw_desc = item.findtext("description") or ""
        desc     = _strip_html(raw_desc)[:600]
        pub_date = item.findtext("pubDate") or ""

        if not title or not url:
            continue

        job_id = "kwork_" + re.sub(r"[^0-9]", "", url)[-10:]
        if not job_id or job_id == "kwork_":
            job_id = "kwork_" + str(abs(hash(url)))[:10]

        price = _parse_price(raw_desc) or _parse_price(title)

        try:
            dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            created_at = dt.isoformat()
        except (ValueError, TypeError):
            created_at = datetime.datetime.utcnow().isoformat() + "Z"

        jobs.append({
            "id":          job_id,
            "platform":    "kwork",
            "title":       title,
            "description": desc,
            "price":       price,
            "url":         url,
            "status":      "pending",
            "score":       0,
            "reason":      "",
            "created_at":  created_at,
        })

    print(f"[Kwork] parsed {len(jobs)} jobs")
    return jobs
