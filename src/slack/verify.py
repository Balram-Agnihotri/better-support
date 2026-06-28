"""Slack signature verification."""

import hashlib
import hmac
import time
from typing import Optional


def verify_signature(
    signing_secret: str,
    timestamp: str,
    body: str,
    signature: str
) -> bool:
    """
    Verify Slack request signature.
    
    Args:
        signing_secret: Slack signing secret
        timestamp: X-Slack-Request-Timestamp header
        body: Raw request body
        signature: X-Slack-Signature header
    
    Returns:
        True if signature is valid, False otherwise
    """
    # Reject old requests (replay attack protection)
    try:
        request_time = int(timestamp)
    except (ValueError, TypeError):
        return False
    
    if abs(time.time() - request_time) > 60 * 5:
        return False
    
    # Compute expected signature
    sig_basestring = f"v0:{timestamp}:{body}"
    expected_signature = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison)
    return hmac.compare_digest(expected_signature, signature)
