"""
Upstash Redis REST API wrapper with local JSON fallback for development.

Production env vars (set in Vercel dashboard or via CLI):
  KV_REST_API_URL   = https://xxx.upstash.io
  KV_REST_API_TOKEN = your-token

Local dev: falls back to data/local_db.json automatically.

Upstash REST API reference:
  GET  /get/{key}        → {"result": "value"}
  POST /pipeline         → [{"result": "OK"}]
  POST /del/{key}        → {"result": 1}
"""

import os
import json
import urllib.request
import urllib.error

_LOCAL_DB = os.path.join(os.path.dirname(__file__), "..", "data", "local_db.json")


class KVStorage:
    def __init__(self):
        self.url   = os.environ.get("KV_REST_API_URL", "").rstrip("/")
        self.token = os.environ.get("KV_REST_API_TOKEN", "")
        self._local = not (self.url and self.token)

    # ── local helpers ──────────────────────────────────────────────────────
    def _read_local(self) -> dict:
        try:
            with open(_LOCAL_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_local(self, db: dict):
        os.makedirs(os.path.dirname(_LOCAL_DB), exist_ok=True)
        with open(_LOCAL_DB, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

    # ── Upstash REST helpers ───────────────────────────────────────────────
    def _req(self, method: str, path: str, body=None):
        url  = f"{self.url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req  = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type":  "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())

    # ── public API ─────────────────────────────────────────────────────────
    def get(self, key: str):
        if self._local:
            return self._read_local().get(key)
        try:
            # GET /get/{key} → {"result": "json-string" | null}
            data = self._req("GET", f"/get/{key}")
            raw  = data.get("result")
            if raw is None:
                return None
            # Upstash stores strings; we JSON-encode complex values on write
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw
            return raw
        except Exception as e:
            print(f"[KV] get({key}) error: {e}")
            return None

    def set(self, key: str, value) -> bool:
        serialized = json.dumps(value, ensure_ascii=False)
        if self._local:
            db = self._read_local()
            db[key] = value
            self._write_local(db)
            return True
        try:
            # POST /pipeline with Redis command array
            result = self._req("POST", "/pipeline", [["SET", key, serialized]])
            # result is a list: [{"result": "OK"}]
            if isinstance(result, list):
                return result[0].get("result") == "OK"
            return result.get("result") == "OK"
        except Exception as e:
            print(f"[KV] set({key}) error: {e}")
            return False

    def delete(self, key: str) -> bool:
        if self._local:
            db = self._read_local()
            db.pop(key, None)
            self._write_local(db)
            return True
        try:
            self._req("POST", f"/del/{key}")
            return True
        except Exception as e:
            print(f"[KV] delete({key}) error: {e}")
            return False
