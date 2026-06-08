import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from http.server import BaseHTTPRequestHandler
from lib.kv_storage import KVStorage
from lib.groq_client import GroqClient
from lib.auth import require_user, user_key

MAX_PER_CALL  = 5     # Vercel Hobby: 10s timeout — 5 × ~1.5s = ~7.5s, safe
DELAY_BETWEEN = 1.8   # Groq free: 30 req/min → need ~2s between calls


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        user = require_user(self)
        if user is None:
            return

        kv = KVStorage()
        profile = kv.get(user_key(user, "profile"))
        if not profile:
            self._json({"error": "No profile found"}, 400)
            return

        jobs: list = kv.get(user_key(user, "jobs")) or []
        pending    = [j for j in jobs if j.get("status") == "pending"]

        if not pending:
            self._json({"analyzed": 0, "remaining": 0, "has_more": False, "message": "No pending jobs"})
            return

        batch    = pending[:MAX_PER_CALL]
        groq     = GroqClient()
        analyzed = 0
        errors   = 0
        job_map  = {j["id"]: j for j in jobs}

        for i, job in enumerate(batch):
            try:
                result = groq.analyze_job(job, profile)
                job_map[job["id"]]["status"] = result["decision"]
                job_map[job["id"]]["score"]  = result["score"]
                job_map[job["id"]]["reason"] = result["reason"]
                analyzed += 1
                print(f"[analyze] {job['id']} → {result['decision']} ({result['score']}/10)")
            except Exception as e:
                print(f"[analyze] {job['id']} error: {e}")
                errors += 1

            # Save after every job — survive Vercel timeout
            kv.set(user_key(user, "jobs"), list(job_map.values()))

            if i < len(batch) - 1:
                time.sleep(DELAY_BETWEEN)

        remaining = len(pending) - analyzed
        self._json({
            "analyzed":  analyzed,
            "errors":    errors,
            "remaining": max(0, remaining),
            "has_more":  remaining > 0,
        })

    def do_GET(self):
        self.do_POST()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
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
