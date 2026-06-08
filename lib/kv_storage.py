"""
Vercel KV wrapper with local JSON fallback for development.

In production (Vercel):
  KV_REST_API_URL and KV_REST_API_TOKEN are set automatically
  after running `vercel kv create <db-name>`.

In development:
  Falls back to data/local_db.json so you can test without Redis.
"""

import os
import json
import urllib.request
import urllib.error

_LOCAL_DB = os.path.join(os.path.dirname(__file__), "..", "data", "local_db.json")


class KVStorage:
    def __init__(self):
        self.url = os.environ.get("KV_REST_API_URL", "").rstrip("/")
        self.token = os.environ.get("KV_REST_API_TOKEN", "")
        self._is_local = not (self.url and self.token)

    # ── local helpers ──────────────────────────────────────────────────────────

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

    # ── Vercel KV helpers ──────────────────────────────────────────────────────

    def _kv_request(self, path: str, method: str = "GET", body=None):
        url = f"{self.url}/{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read()).get("result")

    # ── public API ─────────────────────────────────────────────────────────────

    def get(self, key: str):
        if self._is_local:
            return self._read_local().get(key)
        try:
            val = self._kv_request(f"get/{key}")
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except json.JSONDecodeError:
                    return val
            return val
        except Exception as e:
            print(f"[KV] get({key}) error: {e}")
            return None

    def set(self, key: str, value) -> bool:
        if self._is_local:
            db = self._read_local()
            db[key] = value
            self._write_local(db)
            return True
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            self._kv_request("", method="POST", body=["SET", key, serialized])
            return True
        except Exception as e:
            print(f"[KV] set({key}) error: {e}")
            return False

    def delete(self, key: str) -> bool:
        if self._is_local:
            db = self._read_local()
            db.pop(key, None)
            self._write_local(db)
            return True
        try:
            self._kv_request(f"del/{key}", method="POST")
            return True
        except Exception as e:
            print(f"[KV] delete({key}) error: {e}")
            return False
