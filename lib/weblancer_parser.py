"""
Weblancer.net parser — RSS feed.

RSS: https://www.weblancer.net/jobs/feed/rss/
Один из крупнейших русскоязычных фриланс сайтов.
Контент: название, описание, цена, ссылка.
"""

import re
import datetime
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://www.weblancer.net/jobs/feed/rss/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

_PRICE_RE   = re.compile(r"(\d[\d\s]{1,7})\s*(?:руб(?:лей)?|₽|\$|usd|грн)", re.IGNORECASE)
_BUDGET_TAG = re.compile(r"<budget[^>]*>(.*?)</budget>", re.IGNORECASE | re.DOTALL)


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text or "")
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_price(text: str, raw_xml: str = "") -> int:
    # Try <budget> tag first (Weblancer includes it)
    m = _BUDGET_TAG.search(raw_xml)
    if m:
        raw_val = re.sub(r"[^\d]", "", m.group(1))
        if raw_val.isdigit():
            val = int(raw_val)
            return val // 90 if val > 500 else val

    m = _PRICE_RE.search(text or "")
    if m:
        raw = int(re.sub(r"\s", "", m.group(1)))
        # Гривны → рубли → доллары (грубо)
        if "грн" in text[m.end():m.end()+5].lower():
            raw = raw * 4 // 90
        elif raw > 500:
            raw = raw // 90
        return raw
    return 0


def parse_weblancer(max_items: int = 50) -> list:
    try:
        req = urllib.request.Request(RSS_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml_bytes = resp.read()
    except Exception as e:
        print(f"[Weblancer] fetch error: {e}")
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[Weblancer] XML error: {e}")
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

        job_id = "wl_" + re.sub(r"[^0-9]", "", url)[-10:]
        if not job_id or job_id == "wl_":
            job_id = "wl_" + str(abs(hash(url)))[:10]

        price = _parse_price(desc, raw_desc)

        try:
            dt = datetime.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            created_at = dt.isoformat()
        except (ValueError, TypeError):
            created_at = datetime.datetime.utcnow().isoformat() + "Z"

        jobs.append({
            "id":          job_id,
            "platform":    "weblancer",
            "title":       title,
            "description": desc,
            "price":       price,
            "url":         url,
            "status":      "pending",
            "score":       0,
            "reason":      "",
            "created_at":  created_at,
        })

    print(f"[Weblancer] parsed {len(jobs)} jobs")
    return jobs
