import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import datetime
from http.server import BaseHTTPRequestHandler
from lib.kv_storage import KVStorage
from lib.auth import require_user, user_key

ALLOWED_ACTIONS = {"skip", "save", "restore"}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        user = require_user(self)
        if user is None:
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        job_id = body.get("job_id")
        action = body.get("action")

        if not job_id or action not in ALLOWED_ACTIONS:
            self._json({"error": "job_id and valid action required"}, 400)
            return

        kv   = KVStorage()
        jobs: list = kv.get(user_key(user, "jobs")) or []
        job  = next((j for j in jobs if j["id"] == job_id), None)

        if not job:
            self._json({"error": "Job not found"}, 404)
            return

        if action == "skip":    job["status"] = "rejected"
        elif action == "save":  job["status"] = "approved"
        elif action == "restore": job["status"] = "review"

        kv.set(user_key(user, "jobs"), jobs)

        history: list = kv.get(user_key(user, "history")) or []
        history.insert(0, {
            "job_id":    job_id,
            "action":    action,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        })
        kv.set(user_key(user, "history"), history[:200])

        self._json({"status": "ok", "job_id": job_id, "new_status": job["status"]})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
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
