"""
Freelancehunt parser — RSS feed (CIS freelance platform).

RSS: https://freelancehunt.com/projects.rss
50 самых свежих проектов, UTF-8, обновляется каждую минуту.
Много заказов из РФ, Украины, Беларуси.
"""

import re
import datetime
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://freelancehunt.com/projects.rss"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "application/rss+xml, text/xml",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

# Цена в USD или RUB (Freelancehunt часто пишет в USD)
_USD_RE = re.compile(r"(\d+)\s*(?:USD|\$)", re.IGNORECASE)
_RUB_RE = re.compile(r"(\d[\d\s]{1,7})\s*(?:RUB|руб|₽)", re.IGNORECASE)


def _parse_price(text: str) -> int:
    m = _USD_RE.search(text or "")
    if m:
        return int(m.group(1))
    m = _RUB_RE.search(text or "")
    if m:
        raw = int(re.sub(r"\s", "", m.group(1)))
        return raw // 90 if raw > 500 else raw
    return 0


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text or "")
    return re.sub(r"<[^>]+>", "", text).strip()


def parse_freelancehunt(max_items: int = 50) -> list:
    try:
        req = urllib.request.Request(RSS_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            # Pass raw bytes to ET — it reads encoding from XML declaration
            xml_bytes = resp.read()
    except Exception as e:
        print(f"[Freelancehunt] fetch error: {e}")
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[Freelancehunt] XML error: {e}")
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

        # ID from URL: /project/slug/12345
        m = re.search(r"/(\d+)(?:\?|$|\.html)", url)
        job_id = "fh_" + m.group(1) if m else "fh_" + str(abs(hash(url)))[:10]

        # Price often in title: "Название - 50USD"
        price = _parse_price(title) or _parse_price(desc)

        try:
            dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            created_at = dt.isoformat()
        except (ValueError, TypeError):
            created_at = datetime.datetime.utcnow().isoformat() + "Z"

        # Clean UTM params from URL
        clean_url = url.split("?")[0] if "?" in url else url

        jobs.append({
            "id":          job_id,
            "platform":    "freelancehunt",
            "title":       title,
            "description": desc,
            "price":       price,
            "url":         clean_url,
            "status":      "pending",
            "score":       0,
            "reason":      "",
            "created_at":  created_at,
        })

    print(f"[Freelancehunt] parsed {len(jobs)} jobs")
    return jobs
