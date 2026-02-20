"""
Security utilities: token generation, HMAC signing, password hashing.
"""
import hashlib
import hmac
import secrets
import time
from functools import wraps
from flask import request, jsonify


def generate_session_token(length=32):
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(length)


def generate_hmac(payload_str, secret):
    """Generate HMAC-SHA256 signature for a payload string."""
    return hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_hmac(payload_str, signature, secret):
    """Verify an HMAC-SHA256 signature."""
    expected = generate_hmac(payload_str, secret)
    return hmac.compare_digest(expected, signature)


def hash_pin(pin):
    """Hash a PIN using SHA-256 with a salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_pin(pin, stored_hash):
    """Verify a PIN against its stored hash."""
    if not stored_hash:
        return True  # no PIN set
    salt, expected_hash = stored_hash.split(':')
    actual_hash = hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()
    return hmac.compare_digest(actual_hash, expected_hash)
