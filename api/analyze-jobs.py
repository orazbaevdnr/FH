import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from http.server import BaseHTTPRequestHandler
from lib.kv_storage import KVStorage
from lib.groq_client import GroqClient


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        kv = KVStorage()
        profile = kv.get("profile")
        if not profile:
            self._json({"error": "No profile found"}, 400)
            return

        jobs: list = kv.get("jobs") or []
        pending = [j for j in jobs if j.get("status") == "pending"]

        if not pending:
            self._json({"analyzed": 0, "message": "No pending jobs"})
            return

        groq = GroqClient()
        analyzed = 0
        errors = 0

        for job in pending:
            try:
                result = groq.analyze_job(job, profile)
                job["status"] = result["decision"]
                job["score"] = result["score"]
                job["reason"] = result["reason"]
                analyzed += 1
            except Exception as e:
                print(f"[analyze] {job['id']}: {e}")
                # Don't block: mark as review so user sees it
                job["status"] = "review"
                job["score"] = 5
                job["reason"] = "Не удалось проанализировать автоматически"
                errors += 1

        kv.set("jobs", jobs)
        self._json({"analyzed": analyzed, "errors": errors})

    # Vercel cron fires GET
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
