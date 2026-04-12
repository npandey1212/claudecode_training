# =============================================================================
# Implements:
#   REQ-SHORT-002 (6-char alphanumeric short code)
#   REQ-SHORT-005 (unique code, retry on collision)
# TASK-005: Short code generator
# =============================================================================

import secrets
import string

# REQ-SHORT-002: code space = 62^6 ≈ 56 billion unique codes
SHORT_CODE_LENGTH = 6
ALPHABET = string.ascii_letters + string.digits  # a-z + A-Z + 0-9 = 62 chars

# REQ-SHORT-005: max attempts before raising an error
MAX_RETRIES = 5


def generate_short_code() -> str:
    """
    Generate a random 6-character alphanumeric string.
    REQ-SHORT-002: matches regex ^[a-zA-Z0-9]{6}$

    Uses secrets.choice() (OS CSPRNG) instead of random.choices() (Mersenne Twister)
    so that short codes cannot be predicted by an attacker who observes past outputs.
    Fix: FINDING-C2-001 from self-critique-log.md.

    Collision checking and retry logic lives in crud.create_short_url()
    so that the database is the source of truth for uniqueness.
    """
    return "".join(secrets.choice(ALPHABET) for _ in range(SHORT_CODE_LENGTH))
