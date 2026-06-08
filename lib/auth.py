"""
Google Identity Services auth helper.

Flow:
  1. Frontend loads Google GSI script, user clicks "Sign in with Google"
  2. Google returns a signed JWT (id_token) to the JS callback
  3. Frontend stores it in localStorage as fh_token
  4. Every API request sends  Authorization: Bearer <id_token>
  5. Backend calls verify_token() → user dict or None

The id_token is a standard JWT signed by Google.
We verify it via Google's tokeninfo endpoint (fast, no crypto libs needed).
Result is cached in Upstash KV for 55 min to avoid calling Google every request.

If GOOGLE_CLIENT_ID is not set in env → dev/demo mode → return a fake user.
"""

import os
import json
import hashlib
import time
import urllib.request
import urllib.error
import urllib.parse

TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo?id_token="
CACHE_TTL     = 55 * 60   # 55 minutes in seconds


def _kv():
    """Lazy import to avoid circular dependency."""
    from lib.kv_storage import KVStorage
    return KVStorage()


def verify_token(id_token: str) -> dict | None:
    """
    Verify Google id_token and return user dict or None.
    User dict: {sub, email, name, picture}
    """
    if not id_token or not id_token.strip():
        return None

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")

    # Dev/demo mode — no GOOGLE_CLIENT_ID configured
    if not client_id:
        return {
            "sub":     "demo_user",
            "email":   "demo@freelancehunter.local",
            "name":    "Demo User",
            "picture": "",
        }

    # Check KV cache first (avoid calling Google on every API request)
    token_hash = hashlib.sha256(id_token.encode()).hexdigest()[:20]
    cache_key  = f"gauth:{token_hash}"

    try:
        kv = _kv()
        cached = kv.get(cache_key)
        if cached and isinstance(cached, dict):
            # Check our embedded expiry
            if cached.get("_exp", 0) > time.time():
                return {k: v for k, v in cached.items() if not k.startswith("_")}
    except Exception:
        pass  # Cache miss is fine, just verify fresh

    # Call Google tokeninfo
    try:
        url = TOKENINFO_URL + urllib.parse.quote(id_token, safe="")
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        # 400 = invalid token
        print(f"[auth] tokeninfo HTTP {e.code}")
        return None
    except Exception as e:
        print(f"[auth] tokeninfo error: {e}")
        return None

    # Validate audience (aud must match our client_id)
    aud = data.get("aud", "")
    if client_id and aud != client_id:
        print(f"[auth] audience mismatch: {aud!r} != {client_id!r}")
        return None

    user = {
        "sub":     data.get("sub", ""),
        "email":   data.get("email", ""),
        "name":    data.get("name", ""),
        "picture": data.get("picture", ""),
    }

    # Cache with expiry timestamp
    try:
        kv = _kv()
        kv.set(cache_key, {**user, "_exp": time.time() + CACHE_TTL})
    except Exception:
        pass

    return user


def get_user(headers: object) -> dict | None:
    """Extract Bearer token from headers and verify it."""
    auth = headers.get("Authorization", "") or headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return verify_token(auth[7:].strip())
    return None


def require_user(handler) -> dict | None:
    """
    Get user from request headers.
    On failure, sends 401 JSON response and returns None.
    Caller should return immediately if None.
    """
    user = get_user(handler.headers)
    if user is None:
        body = json.dumps({"error": "Unauthorized — sign in with Google"}).encode()
        handler.send_response(401)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        handler.end_headers()
        handler.wfile.write(body)
    return user


def user_key(user: dict, base: str) -> str:
    """Build a per-user KV key, e.g. user_key(user, 'jobs') → 'jobs:abc123'"""
    return f"{base}:{user['sub']}"
