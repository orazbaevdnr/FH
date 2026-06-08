import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from http.server import BaseHTTPRequestHandler
from lib.kv_storage import KVStorage


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        kv = KVStorage()
        profile = kv.get("profile")

        if not profile:
            # Signal to frontend: no profile yet
            self._json({"exists": False, "profile": None})
            return

        self._json({"exists": True, "profile": profile})

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass
