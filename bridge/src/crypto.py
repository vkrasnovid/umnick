from __future__ import annotations

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import os


class CredentialCrypto:
    """AES-256-GCM шифрование OData-кредов."""

    def __init__(self, key: bytes | None = None):
        from config import settings

        if key is not None:
            self.key = key
        else:
            key_str = settings.encryption_key
            if key_str.startswith("base64:"):
                key_str = key_str[len("base64:"):]
            self.key = base64.b64decode(key_str)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt → base64-encoded ciphertext."""
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ct).decode()

    def decrypt(self, ciphertext_b64: str) -> str:
        """base64-encoded ciphertext → plaintext."""
        raw = base64.b64decode(ciphertext_b64)
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(self.key)
        return aesgcm.decrypt(nonce, ct, None).decode()
