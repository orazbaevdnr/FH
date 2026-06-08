import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from lib.kv_storage import KVStorage
from lib.auth import require_user, user_key


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        user = require_user(self)
        if user is None:
            return

        kv = KVStorage()
        all_jobs: list = kv.get(user_key(user, "jobs")) or []

        qs = parse_qs(urlparse(self.path).query)
        status_filter = qs.get("status", [None])[0]

        all_jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)

        jobs = all_jobs
        if status_filter:
            jobs = [j for j in all_jobs if j.get("status") == status_filter]

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stats = {"total": 0, "approved": 0, "review": 0,
                 "rejected": 0, "pending": 0, "today": 0}

        for j in all_jobs:
            s = j.get("status", "pending")
            stats["total"] += 1
            if s in stats:
                stats[s] += 1
            if j.get("created_at", "").startswith(today_str):
                stats["today"] += 1

        self._json({"jobs": jobs, "stats": stats, "user": user})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass
