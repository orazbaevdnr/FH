"""
Habr Freelance parser — RSS feed.

RSS: https://freelance.habr.com/tasks.rss
     https://freelance.habr.com/tasks.rss?q=python  (с фильтром)

Каждый <item>:
  <title>   — название задания
  <link>    — ссылка
  <description> — описание (HTML)
  <pubDate> — дата публикации
"""

import re
import time
import datetime
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://freelance.habr.com/tasks.rss"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

_PRICE_RE = re.compile(r"(?:от\s*)?(\d[\d\s]{1,7})\s*(?:руб(?:лей)?|₽|\$|usd)", re.IGNORECASE)


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", text or "")
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_price(text: str) -> int:
    m = _PRICE_RE.search(text or "")
    if not m:
        return 0
    raw = int(re.sub(r"\s", "", m.group(1)))
    # если доллары — оставляем, рубли — конвертируем
    if "$" in text[max(0, m.start()-2):m.end()+4].lower() or "usd" in text[max(0, m.start()-2):m.end()+4].lower():
        return raw
    return raw // 90 if raw > 500 else raw


def parse_habr(max_items: int = 50) -> list:
    try:
        req = urllib.request.Request(RSS_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        print(f"[Habr] fetch error: {e}")
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[Habr] XML error: {e}")
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

        job_id = "habr_" + re.sub(r"[^0-9]", "", url)[-10:]
        if not job_id or job_id == "habr_":
            job_id = "habr_" + str(abs(hash(url)))[:10]

        price = _parse_price(raw_desc) or _parse_price(title)

        try:
            dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            created_at = dt.isoformat()
        except (ValueError, TypeError):
            created_at = datetime.datetime.utcnow().isoformat() + "Z"

        jobs.append({
            "id":          job_id,
            "platform":    "habr",
            "title":       title,
            "description": desc,
            "price":       price,
            "url":         url,
            "status":      "pending",
            "score":       0,
            "reason":      "",
            "created_at":  created_at,
        })

    print(f"[Habr] parsed {len(jobs)} jobs")
    return jobs
