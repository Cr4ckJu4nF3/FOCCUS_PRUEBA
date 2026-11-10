"""JWT y dependencias de autorización (app/utils/auth.py)."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app.utils import auth

pytestmark = pytest.mark.unit


def _token_with(payload, secret=None, algorithm="HS256"):
    return jwt.encode(payload, secret or auth.SECRET_KEY, algorithm=algorithm)


def _expired_token():
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    return _token_with({"id_user": 1, "id_rol": 1001, "exp": past})


class TestCreateAndDecodeToken:
    def test_decode_returns_the_original_claims_when_token_is_valid(self):
        # Arrange
        token = auth.create_access_token({"id_user": 7, "id_rol": 1005})

        # Act
        payload = auth.decode_access_token(token)

        # Assert
        assert payload["id_user"] == 7
        assert payload["id_rol"] == 1005

    def test_create_does_not_mutate_the_dict_it_receives(self):
        data = {"id_user": 7}

        auth.create_access_token(data)

        assert data == {"id_user": 7}

    def test_token_expires_after_the_configured_minutes(self):
        token = auth.create_access_token({"id_user": 1})

        payload = auth.decode_access_token(token)

        remaining = payload["exp"] - datetime.now(timezone.utc).timestamp()
        assert 0 < remaining <= auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_decode_raises_401_with_expiry_message_when_token_is_expired(self):
        with pytest.raises(HTTPException) as error:
            auth.decode_access_token(_expired_token())

        assert error.value.status_code == 401
        assert "expirada" in error.value.detail

    @pytest.mark.parametrize("token", ["no-es-un-jwt", "", "a.b.c"])
    def test_decode_raises_401_when_token_is_malformed(self, token):
        with pytest.raises(HTTPException) as error:
            auth.decode_access_token(token)

        assert error.value.status_code == 401
        assert error.value.detail == "Token inválido"

    def test_decode_raises_401_when_token_was_signed_with_another_secret(self):
        forged = _token_with({"id_user": 1, "id_rol": 1001}, secret="otra-clave-distinta-de-32-bytes-o-mas!")

        with pytest.raises(HTTPException) as error:
            auth.decode_access_token(forged)

        assert error.value.status_code == 401


class TestGetCurrentUser:
    @pytest.mark.parametrize(
        "header",
        [None, "", "Token abc", "bearer abc", "Bearer"],
        ids=["sin-header", "vacio", "esquema-distinto", "minuscula", "sin-token"],
    )
    def test_raises_401_when_authorization_header_is_missing_or_wrong(self, header):
        with pytest.raises(HTTPException) as error:
            auth.get_current_user(header)

        assert error.value.status_code == 401

    def test_returns_the_payload_when_bearer_token_is_valid(self):
        token = auth.create_access_token({"id_user": 3, "id_rol": 1005})

        user = auth.get_current_user(f"Bearer {token}")

        assert user["id_user"] == 3

    def test_raises_401_when_token_has_no_id_user_claim(self):
        token = auth.create_access_token({"id_rol": 1001})

        with pytest.raises(HTTPException) as error:
            auth.get_current_user(f"Bearer {token}")

        assert error.value.status_code == 401


class TestRequireAdmin:
    def test_returns_the_user_when_role_is_administrator(self):
        user = {"id_user": 1, "id_rol": 1001}

        assert auth.require_admin(user) is user

    @pytest.mark.parametrize("id_rol", [1002, 1005, 0, None])
    def test_raises_403_when_role_is_not_administrator(self, id_rol):
        with pytest.raises(HTTPException) as error:
            auth.require_admin({"id_user": 1, "id_rol": id_rol})

        assert error.value.status_code == 403
