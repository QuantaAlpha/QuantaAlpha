"""Optional OAuth token provider for OpenAI Codex (ChatGPT subscription).

Reads tokens from a local JSON file and refreshes them automatically
via the standard OAuth refresh_token grant. The token file can be
populated by any tool that implements the OpenAI Codex OAuth flow
(e.g. Codex CLI, OpenClaw CLI, or the standalone login script).

Supports two file formats:

Codex CLI format (~/.codex/auth.json):
{
  "auth_mode": "chatgpt",
  "tokens": {
    "access_token": "<bearer>",
    "refresh_token": "<refresh_token>",
    "account_id": "<chatgpt_account_id>"
  }
}

Flat format (~/.codex_oauth_tokens.json):
{
  "access": "<bearer_token>",
  "refresh": "<refresh_token>",
  "expires": 1742000000000,
  "account_id": "<chatgpt_account_id>"
}
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

TOKEN_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
DEFAULT_TOKEN_PATH = Path.home() / ".codex" / "auth.json"
EXPIRY_BUFFER_MS = 60_000  # refresh 60s before actual expiry


class CodexAuthProvider:
    """Provides a valid OAuth bearer token for chatgpt.com/backend-api.

    Caches the token in memory and re-reads the file when expired.
    If the access token is expired but a refresh token is available,
    performs an automatic refresh and writes the new tokens back.
    """

    def __init__(self, token_path: str = "") -> None:
        self._path = Path(token_path) if token_path else DEFAULT_TOKEN_PATH
        self._access: str = ""
        self._refresh: str = ""
        self._expires: float = 0.0
        self._account_id: str = ""
        self._nested_format: bool = False  # True when source file uses Codex CLI format

    @property
    def account_id(self) -> str:
        if not self._account_id:
            self._load()
        return self._account_id

    def get_token(self) -> str:
        now_ms = time.time() * 1000
        if self._access and now_ms < self._expires - EXPIRY_BUFFER_MS:
            return self._access

        self._load()
        now_ms = time.time() * 1000
        if now_ms < self._expires - EXPIRY_BUFFER_MS:
            return self._access

        # Token expired — try refresh
        if self._refresh:
            self._do_refresh()
            return self._access

        raise RuntimeError(
            f"Codex OAuth token expired and no refresh token available. "
            f"Re-run the OAuth login to obtain fresh tokens ({self._path})."
        )

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(
                f"Codex OAuth token file not found: {self._path}. "
                f"Run the OAuth login script first."
            )
        data = json.loads(self._path.read_text())

        # Support both formats:
        #   Codex CLI (~/.codex/auth.json): tokens nested under "tokens" key
        #   Flat format (~/.codex_oauth_tokens.json): top-level keys
        if "tokens" in data:
            self._nested_format = True
            tokens = data["tokens"]
            self._access = tokens.get("access_token", tokens.get("access", ""))
            self._refresh = tokens.get("refresh_token", tokens.get("refresh", ""))
            self._account_id = tokens.get("account_id", "")
            # Codex CLI format has no expires field; extract from JWT exp claim
            self._expires = data.get("expires", 0)
            if not self._expires and self._access:
                self._expires = _extract_exp_ms(self._access)
        else:
            self._access = data["access"]
            self._refresh = data.get("refresh", "")
            self._expires = data.get("expires", 0)
            self._account_id = data.get("account_id", "")

    def _do_refresh(self) -> None:
        logger.info("Refreshing Codex OAuth token...")
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self._refresh,
            "client_id": CLIENT_ID,
        }).encode()
        req = urllib.request.Request(
            TOKEN_URL, data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            tokens = json.loads(resp.read())

        self._access = tokens["access_token"]
        if tokens.get("refresh_token"):
            self._refresh = tokens["refresh_token"]
        self._expires = time.time() * 1000 + tokens.get("expires_in", 3600) * 1000

        # Extract account_id from JWT
        self._account_id = _extract_account_id(self._access) or self._account_id

        # Write back (preserve original file format)
        if self._nested_format:
            store = {
                "auth_mode": "chatgpt",
                "OPENAI_API_KEY": None,
                "tokens": {
                    "access_token": self._access,
                    "refresh_token": self._refresh,
                    "account_id": self._account_id,
                },
                "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        else:
            store = {
                "access": self._access,
                "refresh": self._refresh,
                "expires": self._expires,
                "account_id": self._account_id,
            }
        self._path.write_text(json.dumps(store, indent=2))
        logger.info("Codex OAuth token refreshed successfully.")


def _extract_exp_ms(jwt_token: str) -> float:
    """Extract expiration time (in ms) from a JWT access token."""
    import base64
    try:
        parts = jwt_token.split(".")
        if len(parts) != 3:
            return 0
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        exp = claims.get("exp", 0)
        return exp * 1000 if exp else 0
    except Exception:  # noqa: BLE001
        return 0


class MultiCodexAuthProvider:
    """Round-robins across multiple CodexAuthProvider instances.

    Each call to get_token() picks the next provider in order, spreading
    load across multiple ChatGPT accounts.
    """

    def __init__(self, token_paths: list[str]) -> None:
        if not token_paths:
            raise ValueError("At least one token path is required")
        self._providers = [CodexAuthProvider(p) for p in token_paths]
        self._index = 0
        self._lock_index = False

    @property
    def account_id(self) -> str:
        return self._current.account_id

    @property
    def _current(self) -> CodexAuthProvider:
        return self._providers[self._index % len(self._providers)]

    def get_token(self) -> str:
        provider = self._current
        self._index = (self._index + 1) % len(self._providers)
        return provider.get_token()

    def get_token_and_account(self) -> tuple[str, str]:
        """Return (token, account_id) from the next provider in rotation."""
        provider = self._current
        self._index = (self._index + 1) % len(self._providers)
        return provider.get_token(), provider.account_id


def fetch_latest_codex_model(base_url: str, token: str, account_id: str) -> str:
    """Query /codex/models and return the slug that sorts last alphabetically."""
    url = f"{base_url.rstrip('/')}/codex/models?client_version=0.1.0"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("chatgpt-account-id", account_id)
    req.add_header("OpenAI-Beta", "responses=experimental")
    req.add_header("originator", "pi")
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
        data = json.loads(resp.read())
    models = [m for m in data.get("models", []) if m.get("supported_in_api")]
    if not models:
        raise RuntimeError("No codex models available from the API")
    # lowest priority number = most preferred
    best = min(models, key=lambda m: m.get("priority", 999))
    return best["slug"]


def _extract_account_id(jwt_token: str) -> str:
    """Extract chatgpt_account_id from an OpenAI access token (JWT)."""
    import base64
    try:
        parts = jwt_token.split(".")
        if len(parts) != 3:
            return ""
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return claims.get("https://api.openai.com/auth", {}).get(
            "chatgpt_account_id", ""
        )
    except Exception:  # noqa: BLE001
        return ""
