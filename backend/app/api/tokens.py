import base64
import hashlib
import hmac
import json
import time

TOKEN_SECRET = "booknest-class-demo-secret"
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def create_token(user_id: int) -> str:
    payload = {"userId": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{body}.{signature}"


def read_token(token: str) -> int:
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(
            TOKEN_SECRET.encode("utf-8"),
            body.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("bad signature")
        payload = json.loads(_decode(body))
        if int(payload["exp"]) < time.time():
            raise ValueError("expired")
        return int(payload["userId"])
    except (ValueError, KeyError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("invalid token") from exc
