import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _get_fernet(secret: str) -> Fernet:
    """
    Derive a 32-byte url-safe base64-encoded key from the given secret.
    """
    # Use SHA-256 to ensure we have exactly 32 bytes of deterministic pseudorandom data
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    # Fernet requires urlsafe base64 encoding
    b64_key = base64.urlsafe_b64encode(key)
    return Fernet(b64_key)

def encrypt_token(plain_text: str, secret: str) -> str:
    """Encrypt a plain text token."""
    if not plain_text:
        return ""
    fernet = _get_fernet(secret)
    return fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

def decrypt_token(cipher_text: str, secret: str) -> str | None:
    """Decrypt a cipher text token. Returns None if decryption fails."""
    if not cipher_text:
        return None
    try:
        fernet = _get_fernet(secret)
        return fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
    except Exception:
        return None
