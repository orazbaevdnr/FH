import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from lib.kv_storage import KVStorage


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        kv = KVStorage()
        all_jobs: list = kv.get("jobs") or []

        qs = parse_qs(urlparse(self.path).query)
        status_filter = qs.get("status", [None])[0]

        # Sort newest first (before filter so stats are accurate)
        all_jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)

        jobs = all_jobs
        if status_filter:
            jobs = [j for j in all_jobs if j.get("status") == status_filter]

        # Compute stats over ALL jobs
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stats = {"total": 0, "approved": 0, "review": 0,
                 "rejected": 0, "pending": 0, "today": 0}

        for j in all_jobs:
            s = j.get("status", "pending")
            stats["total"] += 1
            if s in stats:
                stats[s] += 1
            # Count jobs created today (ISO date prefix match)
            created = j.get("created_at", "")
            if created.startswith(today_str):
                stats["today"] += 1

        self._json({"jobs": jobs, "stats": stats})

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass
