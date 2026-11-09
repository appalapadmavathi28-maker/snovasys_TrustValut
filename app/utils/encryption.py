import os
import io
from cryptography.fernet import Fernet
from flask import current_app


def get_cipher():
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        raise ValueError("ENCRYPTION_KEY is not configured.")
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_data(raw_bytes: bytes) -> bytes:
    cipher = get_cipher()
    return cipher.encrypt(raw_bytes)


def decrypt_data(encrypted_bytes: bytes) -> bytes:
    cipher = get_cipher()
    return cipher.decrypt(encrypted_bytes)


def save_encrypted_file(file_storage, target_filepath: str) -> int:
    """
    Reads the file stream from Flask's FileStorage, encrypts the raw bytes
    at rest, and writes the encrypted payload to disk.
    Returns the original plaintext file size in bytes.
    """
    raw_data = file_storage.read()
    file_size = len(raw_data)
    
    # Encrypt bytes
    encrypted_data = encrypt_data(raw_data)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(target_filepath), exist_ok=True)
    
    with open(target_filepath, 'wb') as f:
        f.write(encrypted_data)
        
    return file_size


def read_decrypted_file(filepath: str) -> bytes:
    """
    Reads an encrypted file from disk, decrypts it in-memory,
    and returns the plaintext bytes.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found on disk: {filepath}")
        
    with open(filepath, 'rb') as f:
        encrypted_data = f.read()
        
    return decrypt_data(encrypted_data)


def delete_file(filepath: str) -> bool:
    """
    Safely deletes a file from disk if it exists.
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    except OSError:
        return False
