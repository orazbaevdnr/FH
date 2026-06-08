import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from http.server import BaseHTTPRequestHandler
from lib.kv_storage import KVStorage
from lib.groq_client import GroqClient

# Vercel Hobby: 10s max execution time
# Groq free: 30 req/min → need ~2s between requests
# Process max 5 jobs per call; frontend calls multiple times if needed
MAX_PER_CALL  = 5
DELAY_BETWEEN = 1.8   # seconds between Groq calls (stay under 30/min)


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
            self._json({"analyzed": 0, "remaining": 0, "message": "No pending jobs"})
            return

        # Only process a small batch to stay within Vercel timeout
        batch = pending[:MAX_PER_CALL]
        groq  = GroqClient()
        analyzed = 0
        errors   = 0

        # Build lookup for fast update
        job_map = {j["id"]: j for j in jobs}

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
                # Don't mark as reviewed — keep as pending so next call retries
                errors += 1

            # Save progress after EACH job so timeout doesn't lose work
            updated_jobs = list(job_map.values())
            kv.set("jobs", updated_jobs)

            # Rate-limit: sleep between requests (skip after last)
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
