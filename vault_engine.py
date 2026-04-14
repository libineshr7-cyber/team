import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

class VaultEngine:
    """
    Enterprise-grade encryption engine using AES-256-GCM.
    Provides authenticated encryption to ensure both confidentiality and integrity.
    """

    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        """Derive a 256-bit key using PBKDF2-HMAC-SHA256."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(password.encode())

    @classmethod
    def encrypt_file(cls, filepath: str, password: str) -> str:
        """Encrypts a file in place. Returns the path to the encrypted vault file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, "rb") as f:
            data = f.read()

        salt = os.urandom(16)
        key = cls.derive_key(password, salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        
        # Authenticated encryption
        ciphertext = aesgcm.encrypt(nonce, data, None)

        # Structure: SALT(16) | NONCE(12) | CIPHERTEXT(variable)
        vault_data = salt + nonce + ciphertext
        
        vault_path = filepath + ".vault"
        with open(vault_path, "wb") as f:
            f.write(vault_data)
            
        return vault_path

    @classmethod
    def decrypt_data(cls, vault_path: str, password: str) -> bytes:
        """Decrypts a vault file and returns the raw bytes."""
        if not os.path.exists(vault_path):
            raise FileNotFoundError(f"Vault not found: {vault_path}")

        with open(vault_path, "rb") as f:
            data = f.read()

        if len(data) < 28: # 16 (salt) + 12 (nonce)
            raise ValueError("Corrupted vault file.")

        salt = data[:16]
        nonce = data[16:28]
        ciphertext = data[28:]

        key = cls.derive_key(password, salt)
        aesgcm = AESGCM(key)
        
        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except Exception:
            raise ValueError("Authentication failed (wrong password or corrupted data).")

    @staticmethod
    def secure_wipe(filepath: str, passes: int = 3):
        """Securely wipes a file using multiple passes of random data."""
        if not os.path.exists(filepath):
            return
        
        size = os.path.getsize(filepath)
        with open(filepath, "ba+", buffering=0) as f:
            for _ in range(passes):
                f.seek(0)
                f.write(os.urandom(size))
            f.seek(0)
            f.write(b"\x00" * size)
        
        os.remove(filepath)
