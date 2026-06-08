import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from http.server import BaseHTTPRequestHandler
from lib.kv_storage import KVStorage


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        # Basic validation
        required = {"direction", "skills", "experience", "min_price"}
        missing = required - body.keys()
        if missing:
            self._json({"error": f"Missing fields: {missing}"}, 400)
            return

        profile = {
            "direction": str(body["direction"]),
            "skills": [str(s) for s in body.get("skills", [])],
            "experience": str(body["experience"]),
            "min_price": int(body.get("min_price", 0)),
            "excluded": [s.strip().lower() for s in body.get("excluded", []) if s.strip()],
        }

        kv = KVStorage()
        kv.set("profile", profile)
        self._json({"status": "ok"})

    def do_OPTIONS(self):
        self._cors(200)

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _cors(self, status):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, *_):
        pass
