import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from http.server import BaseHTTPRequestHandler
from lib.kv_storage           import KVStorage
from lib.auth                 import require_user, user_key
from lib.fl_parser            import parse_fl
from lib.freelancehunt_parser import parse_freelancehunt
from lib.workzilla_parser     import parse_workzilla
from lib.weblancer_parser     import parse_weblancer

# All parsers — each must gracefully return [] on failure
PARSERS = {
    "fl.ru":         parse_fl,
    "freelancehunt": parse_freelancehunt,
    "workzilla":     parse_workzilla,
    "weblancer":     parse_weblancer,
}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self._run()

    def do_GET(self):   # Vercel cron compatibility
        self._run()

    def _run(self):
        user = require_user(self)
        if user is None:
            return

        kv = KVStorage()
        existing: list = kv.get(user_key(user, "jobs")) or []
        existing_ids   = {j["id"] for j in existing}

        new_jobs = []
        results  = {}

        for platform, parser_fn in PARSERS.items():
            try:
                jobs  = parser_fn(max_items=50)
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
            all_jobs = existing + new_jobs
            if len(all_jobs) > 500:
                all_jobs = all_jobs[-500:]
            kv.set(user_key(user, "jobs"), all_jobs)

        self._json({
            "new_jobs":  len(new_jobs),
            "total":     len(existing) + len(new_jobs),
            "platforms": results,
        })

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def log_message(self, *_):
        pass
