"""
Tests para el módulo de seguridad (JWT, hashing, blacklist).
"""
import pytest
from datetime import timedelta

from app.auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    blacklist_token,
    _token_blacklist,
)


class TestPasswordHashing:
    """Tests para hashing y verificación de contraseñas."""

    def test_hash_password_returns_string(self):
        hashed = get_password_hash("mi_password_123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_differs_from_plain(self):
        plain = "mi_password_123"
        hashed = get_password_hash(plain)
        assert hashed != plain

    def test_verify_correct_password(self):
        plain = "password_seguro_2024"
        hashed = get_password_hash(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_incorrect_password(self):
        hashed = get_password_hash("password_correcta")
        assert verify_password("password_incorrecta", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Cada hash debe ser único (bcrypt usa sal aleatoria)."""
        hashed1 = get_password_hash("misma_password")
        hashed2 = get_password_hash("misma_password")
        assert hashed1 != hashed2
        # Pero ambos deben verificar correctamente
        assert verify_password("misma_password", hashed1)
        assert verify_password("misma_password", hashed2)


class TestJWT:
    """Tests para creación y decodificación de tokens JWT."""

    def test_create_token_returns_string(self):
        token = create_access_token(data={"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        data = {"sub": "admin", "role": "admin"}
        token = create_access_token(data=data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_decode_invalid_token(self):
        payload = decode_token("token.invalido.aqui")
        assert payload is None

    def test_decode_empty_token(self):
        payload = decode_token("")
        assert payload is None

    def test_token_with_custom_expiration(self):
        data = {"sub": "testuser"}
        token = create_access_token(data=data, expires_delta=timedelta(minutes=5))
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"

    def test_token_contains_expiration(self):
        token = create_access_token(data={"sub": "user1"})
        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload


class TestTokenBlacklist:
    """Tests para la blacklist de tokens."""

    def setup_method(self):
        """Limpiar blacklist antes de cada test."""
        _token_blacklist.clear()

    def test_blacklist_token(self):
        token = create_access_token(data={"sub": "user1"})
        # Antes de blacklist, el token es válido
        assert decode_token(token) is not None

        # Después de blacklist, el token es inválido
        blacklist_token(token)
        assert decode_token(token) is None

    def test_blacklist_does_not_affect_other_tokens(self):
        token1 = create_access_token(data={"sub": "user1"})
        token2 = create_access_token(data={"sub": "user2"})

        blacklist_token(token1)

        assert decode_token(token1) is None
        assert decode_token(token2) is not None
