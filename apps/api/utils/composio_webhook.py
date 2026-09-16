"""
Verifies Composio's webhook signatures (Svix-style scheme). See:
https://docs.composio.dev/docs/setting-up-triggers/subscribing-to-events#verifying-signatures

Composio signs every request with HMAC-SHA256 over
"{webhook-id}.{webhook-timestamp}.{raw_body}", base64-encoded, carried in
the `webhook-signature` header as "v1,<signature>" (space-separated if more
than one). `webhook-id` and `webhook-timestamp` are separate headers.
"""
import hashlib
import hmac
import base64
import time
from typing import Optional

DEFAULT_TOLERANCE_SECONDS = 300


def verify_composio_signature(
    secret: str,
    webhook_id: str,
    webhook_timestamp: str,
    raw_body: bytes,
    signature_header: str,
    tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
) -> bool:
    """
    True if signature_header contains a valid, non-stale signature for
    raw_body. Rejects a missing/malformed timestamp and one outside the
    tolerance window (replay protection) as well as a bad signature.
    """
    if not (webhook_id and webhook_timestamp and signature_header):
        return False

    try:
        ts = int(webhook_timestamp)
    except ValueError:
        return False

    if tolerance_seconds and abs(time.time() - ts) > tolerance_seconds:
        return False

    signed_content = f"{webhook_id}.{webhook_timestamp}.".encode() + raw_body
    expected = base64.b64encode(
        hmac.new(secret.encode(), signed_content, hashlib.sha256).digest()
    ).decode()

    for candidate in signature_header.split():
        received = candidate.split(",", 1)[1] if "," in candidate else candidate
        if hmac.compare_digest(expected, received):
            return True
    return False


def extract_trigger_slug(envelope: dict) -> Optional[str]:
    return (envelope.get("metadata") or {}).get("trigger_slug")
