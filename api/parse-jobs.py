import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from http.server import BaseHTTPRequestHandler
from lib.kv_storage import KVStorage
from lib.fl_parser import parse_fl


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        kv = KVStorage()
        existing: list = kv.get("jobs") or []
        existing_ids = {j["id"] for j in existing}

        fresh = parse_fl(max_items=60)
        new_jobs = [j for j in fresh if j["id"] not in existing_ids]

        if new_jobs:
            kv.set("jobs", existing + new_jobs)

        self._json({"new_jobs": len(new_jobs), "total": len(existing) + len(new_jobs)})

    # Vercel cron calls GET; support both
    def do_GET(self):
        self.do_POST()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass
