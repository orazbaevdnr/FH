"""
Returns public auth config to the frontend.
GOOGLE_CLIENT_ID is public (not a secret) — safe to expose.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._json({
            "google_client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "auth_enabled": bool(os.environ.get("GOOGLE_CLIENT_ID", "")),
        })

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass
