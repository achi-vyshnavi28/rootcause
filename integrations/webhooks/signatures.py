"""Webhook authenticity checks. Constant-time comparison prevents timing attacks."""

import hashlib
import hmac


def razorpay_signature(body: bytes, secret: str) -> str:
    """Razorpay signs the raw request body with HMAC-SHA256 using the webhook secret (hex digest)."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_razorpay(body: bytes, signature: str | None, secret: str) -> bool:
    return bool(signature) and hmac.compare_digest(razorpay_signature(body, secret), signature)


def verify_token(received: str | None, expected: str) -> bool:
    return bool(received) and hmac.compare_digest(received, expected)


def body_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()[:40]
