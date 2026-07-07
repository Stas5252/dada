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

SENSITIVE_SETTINGS_KEYS = {
    "openai_api_key",
    "telegram_bot_token",
    "twilio_auth_token",
    "yookassa_secret_key",
    "sip_password",
    "whatsapp_token",
    "whatsapp_verify_token",
    "whatsapp_app_secret",
    "vk_group_token",
    "vk_confirmation_code",
    "vk_secret_key",
    "iiko_api_password",
}

def encrypt_json_secrets(data: dict, secret: str) -> dict:
    """Recursively encrypt sensitive keys in a JSON-like dictionary."""
    if not secret:
        return data
        
    result = {}
    for k, v in data.items():
        if isinstance(v, dict):
            result[k] = encrypt_json_secrets(v, secret)
        elif k in SENSITIVE_SETTINGS_KEYS and isinstance(v, str) and v and not v.startswith("gAAAAA"):
            result[k] = encrypt_token(v, secret)
        else:
            result[k] = v
    return result

def decrypt_json_secrets(data: dict, secret: str) -> dict:
    """Recursively decrypt sensitive keys in a JSON-like dictionary."""
    if not secret:
        return data
        
    result = {}
    for k, v in data.items():
        if isinstance(v, dict):
            result[k] = decrypt_json_secrets(v, secret)
        elif k in SENSITIVE_SETTINGS_KEYS and isinstance(v, str) and v:
            # Only try to decrypt if it looks like a Fernet token (starts with gAAAAA)
            if v.startswith("gAAAAA"):
                decrypted = decrypt_token(v, secret)
                result[k] = decrypted if decrypted is not None else v
            else:
                # It was plaintext in DB (migration missing), return as is
                result[k] = v
        else:
            result[k] = v
    return result
