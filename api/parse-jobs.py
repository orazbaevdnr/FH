import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from http.server import BaseHTTPRequestHandler
from lib.kv_storage import KVStorage
from lib.fl_parser       import parse_fl
from lib.habr_parser     import parse_habr
from lib.kwork_parser    import parse_kwork
from lib.weblancer_parser import parse_weblancer

# Все активные платформы
PARSERS = {
    "fl.ru":      parse_fl,
    "habr":       parse_habr,
    "kwork":      parse_kwork,
    "weblancer":  parse_weblancer,
}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self._run()

    def do_GET(self):   # Vercel cron fires GET
        self._run()

    def _run(self):
        kv = KVStorage()
        existing: list = kv.get("jobs") or []
        existing_ids   = {j["id"] for j in existing}

        new_jobs = []
        results  = {}

        for platform, parser_fn in PARSERS.items():
            try:
                jobs = parser_fn(max_items=40)
                fresh = [j for j in jobs if j["id"] not in existing_ids]
                for j in fresh:
                    existing_ids.add(j["id"])
                new_jobs.extend(fresh)
                results[platform] = {"parsed": len(jobs), "new": len(fresh)}
                print(f"[parse] {platform}: {len(jobs)} total, {len(fresh)} new")
            except Exception as e:
                print(f"[parse] {platform} error: {e}")
                results[platform] = {"error": str(e)}

        if new_jobs:
            kv.set("jobs", existing + new_jobs)

        self._json({
            "new_jobs": len(new_jobs),
            "total":    len(existing) + len(new_jobs),
            "platforms": results,
        })

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()

    def log_message(self, *_):
        pass
