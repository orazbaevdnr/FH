"""
Work-zilla parser — RSS feed.

Work-zilla.com — популярная российская биржа микрозаданий и фриланса.
RSS: https://work-zilla.com/tasks/rss  (проверено, работает)
"""

import re
import datetime
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://work-zilla.com/tasks/rss"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept":     "application/rss+xml, application/xml, text/xml",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

_PRICE_RE = re.compile(r"(\d[\d\s]{1,8})\s*(?:руб(?:лей)?|₽|rub)", re.IGNORECASE)
_USD_RE   = re.compile(r"\$\s*(\d+)", re.IGNORECASE)


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text or "")
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_price(text: str) -> int:
    m = _USD_RE.search(text or "")
    if m:
        return int(m.group(1))
    m = _PRICE_RE.search(text or "")
    if m:
        rub = int(re.sub(r"\s", "", m.group(1)))
        return max(1, rub // 90)
    return 0


def parse_workzilla(max_items: int = 50) -> list:
    try:
        req = urllib.request.Request(RSS_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        print(f"[Work-zilla] fetch error: {e}")
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[Work-zilla] XML parse error: {e}")
        return []

    jobs = []
    for item in root.iter("item"):
        if len(jobs) >= max_items:
            break

        title    = (item.findtext("title") or "").strip()
        url      = (item.findtext("link")  or "").strip()
        raw_desc = item.findtext("description") or ""
        desc     = _strip_html(raw_desc)[:600]
        pub_date = item.findtext("pubDate") or ""

        if not title or not url:
            continue

        m = re.search(r"/(\d+)(?:[/?#]|$)", url)
        job_id = "wz_" + m.group(1) if m else "wz_" + str(abs(hash(url)))[:10]

        price = _parse_price(desc) or _parse_price(title)

        try:
            dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            created_at = dt.isoformat()
        except (ValueError, TypeError):
            created_at = datetime.datetime.utcnow().isoformat() + "Z"

        jobs.append({
            "id":          job_id,
            "platform":    "workzilla",
            "title":       title,
            "description": desc,
            "price":       price,
            "url":         url,
            "status":      "pending",
            "score":       0,
            "reason":      "",
            "created_at":  created_at,
        })

    print(f"[Work-zilla] parsed {len(jobs)} jobs")
    return jobs
