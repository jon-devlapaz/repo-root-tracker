"""Optional password protection for running the dashboard behind a reverse proxy.

Off by default: with no password configured the server behaves exactly as before
(loopback only, no login). Remote mode needs a password hash and the public host
name(s) the proxy forwards; TLS is the proxy's job (see deploy/Caddyfile).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

SESSION_SECONDS = 7 * 24 * 3600
MAX_FAILURES = 5
LOCKOUT_SECONDS = 15 * 60
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    b64 = lambda raw: base64.b64encode(raw).decode()
    return f"scrypt${_N}${_R}${_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                                dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def load_secret(config_dir: Path) -> bytes:
    """A stable signing key: RRT_SECRET if set, else a 0600 file created on first use."""
    env = os.environ.get("RRT_SECRET")
    if env:
        return env.encode()
    path = config_dir / "session.key"
    try:
        return path.read_bytes()
    except FileNotFoundError:
        config_dir.mkdir(parents=True, exist_ok=True)
        key = secrets.token_bytes(32)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(key)
        return key


def make_token(secret: bytes, now: float | None = None) -> str:
    expires = str(int((now if now is not None else time.time()) + SESSION_SECONDS))
    sig = hmac.new(secret, expires.encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{sig}"


def verify_token(secret: bytes, token: str, now: float | None = None) -> bool:
    try:
        expires, sig = token.split(".", 1)
        good = hmac.new(secret, expires.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, good) and int(expires) > (now if now is not None else time.time())
    except (ValueError, AttributeError):
        return False


class LoginLimiter:
    """Locks an address out after repeated wrong passwords."""

    def __init__(self) -> None:
        self._fails: dict[str, list[float]] = {}

    def locked_for(self, ip: str, now: float | None = None) -> int:
        now = now if now is not None else time.time()
        recent = [t for t in self._fails.get(ip, []) if now - t < LOCKOUT_SECONDS]
        self._fails[ip] = recent
        if len(recent) >= MAX_FAILURES:
            return int(LOCKOUT_SECONDS - (now - recent[0])) + 1
        return 0

    def failed(self, ip: str, now: float | None = None) -> None:
        self._fails.setdefault(ip, []).append(now if now is not None else time.time())

    def succeeded(self, ip: str) -> None:
        self._fails.pop(ip, None)


LOGIN_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Sign in · repo-root-tracker</title>
<style>:root{color-scheme:dark}body{margin:0;min-height:100dvh;display:grid;place-items:center;background:#100f0f;color:#ece9e1;
font:16px/1.5 Inter,system-ui,sans-serif}form{width:min(340px,calc(100vw - 32px))}h1{font:400 38px/1.1 "Instrument Serif",Georgia,serif;margin:0 0 20px}
label{display:block;color:#a9a69d;margin-bottom:6px}input{width:100%;box-sizing:border-box;min-height:44px;padding:8px 2px;background:transparent;border:0;
border-bottom:1px solid #4a4743;color:inherit;font:inherit}input:focus{outline:none;border-bottom-color:#3aa99f;box-shadow:0 1px 0 #3aa99f}
button{margin-top:22px;min-height:44px;padding:0 22px;border:0;border-radius:8px;background:#3aa99f;color:#06231f;font:inherit;font-weight:600;cursor:pointer}
p{color:#e8826f;min-height:1.5em}</style></head><body><form method="post" action="/login"><h1>repo-root-tracker</h1>
<label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" autofocus required>
<p role="alert">__ERROR__</p><button type="submit">Sign in</button></form></body></html>"""
