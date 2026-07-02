import logging

import pytest
from cryptography.fernet import Fernet

from src.infrastructure.security.token_cipher import TokenCipher


def _key() -> str:
    return Fernet.generate_key().decode()


def test_roundtrip_returns_original():
    cipher = TokenCipher([_key()])
    assert cipher.decrypt(cipher.encrypt("secret-token")) == "secret-token"


def test_ciphertext_hides_plaintext_and_is_non_deterministic():
    cipher = TokenCipher([_key()])
    a = cipher.encrypt("secret-token")
    b = cipher.encrypt("secret-token")
    # Fernet lleva IV + timestamp: mismo texto -> ciphertexts distintos.
    assert a != b
    assert "secret-token" not in a


def test_empty_keys_raises():
    with pytest.raises(ValueError):
        TokenCipher([])


def test_legacy_plaintext_falls_back_with_warning(caplog):
    cipher = TokenCipher([_key()])
    with caplog.at_level(logging.WARNING):
        assert cipher.decrypt("plaintext-legacy-token") == "plaintext-legacy-token"
    assert "legacy" in caplog.text.lower()
    # El fallback nunca debe loguear el valor del token.
    assert "plaintext-legacy-token" not in caplog.text


def test_is_encrypted_detects_ciphertext_vs_plaintext():
    cipher = TokenCipher([_key()])
    assert cipher.is_encrypted(cipher.encrypt("t")) is True
    assert cipher.is_encrypted("not-a-fernet-token") is False


def test_key_rotation_decrypts_with_multifernet():
    old_key = _key()
    new_key = _key()
    # Cifrado con la clave vieja...
    old_cipher = TokenCipher([old_key])
    ciphertext = old_cipher.encrypt("secret-token")
    # ...se descifra con [nueva, vieja] (la nueva cifra, ambas descifran).
    rotated = TokenCipher([new_key, old_key])
    assert rotated.decrypt(ciphertext) == "secret-token"
