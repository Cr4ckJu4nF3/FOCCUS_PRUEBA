"""Matriz de control de acceso: quién puede llamar a cada ruta.

La clasificación está escrita a mano a propósito. Si alguien agrega una ruta nueva
o le quita la protección a una existente, este archivo falla y obliga a decidirlo
de forma consciente (en vez de que el test se adapte solo y deje de proteger).
"""
import re
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.main import app
from app.utils.auth import ALGORITHM, SECRET_KEY

pytestmark = pytest.mark.api

# Sin token
PUBLIC = {
    ("GET", "/"),
    ("POST", "/users/login"),
    ("POST", "/users/recover-password"),
    ("POST", "/users/reset-password"),
    ("POST", "/register"),
    ("POST", "/users/2fa/check"),
    ("POST", "/users/2fa/send"),
    ("POST", "/users/2fa/verify"),
    ("POST", "/contact"),
}

# Cualquier usuario con sesión
AUTHENTICATED = {
    ("POST", "/users/invite"),
    ("GET", "/users/project/{id_project}"),
    ("GET", "/users/{id_user}/projects"),
    ("GET", "/users/{id}"),
    ("PUT", "/users/{id}"),
    ("PATCH", "/users/{id}"),
    ("DELETE", "/users/me/account"),
    ("POST", "/projects/create"),
    ("GET", "/projects/client/{id_client}"),
    ("GET", "/projects/{id}"),
    ("POST", "/projects"),
    ("PUT", "/projects/{id}"),
    ("PATCH", "/projects/{id}"),
    ("GET", "/clients"),
    ("GET", "/clients/{id}"),
    ("GET", "/roles"),
    ("GET", "/roles/{id}"),
    ("GET", "/guiones"),
    ("GET", "/guiones/{id_guion}"),
    ("GET", "/guiones/{id_guion}/versiones"),
    ("POST", "/guiones/versiones/{id_guion_version}/notas"),
    ("GET", "/guiones/versiones/{id_guion_version}/notas"),
    ("GET", "/guiones/{id_guion}/escenas"),
    ("GET", "/escenas/{id_escena}"),
    ("GET", "/escenas/{id_escena}/versiones"),
    ("GET", "/escenas/versiones/{id_escena_version}/fotos"),
    ("GET", "/guiones/{id_guion}/desglose"),
    ("GET", "/escenas/{id_escena}/desglose"),
    ("GET", "/projects/{id_project}/rodajes"),
    ("GET", "/projects/{id_project}/escenas-disponibles"),
    ("GET", "/rodajes/{id_rodaje}"),
    ("GET", "/rodajes/{id_rodaje}/procesos"),
    ("GET", "/projects/{id_project}/personajes"),
    ("GET", "/projects/{id_project}/escenarios"),
}

# Solo administradores (rol 1001)
ADMIN_ONLY = {
    ("GET", "/users"),
    ("POST", "/users"),
    ("DELETE", "/users/{id}"),
    ("DELETE", "/users/{id_user}/project/{id_project}"),
    ("PATCH", "/users/{id_user}/project/{id_project}"),
    ("GET", "/projects"),
    ("POST", "/projects/{id}/delete"),
    ("DELETE", "/projects/{id}"),
    ("POST", "/clients"),
    ("PUT", "/clients/{id}"),
    ("PATCH", "/clients/{id}"),
    ("DELETE", "/clients/{id}"),
    ("POST", "/roles"),
    ("PUT", "/roles/{id}"),
    ("PATCH", "/roles/{id}"),
    ("DELETE", "/roles/{id}"),
    ("POST", "/guiones"),
    ("POST", "/guiones/texto"),
    ("POST", "/guiones/archivo"),
    ("PATCH", "/guiones/{id_guion}"),
    ("DELETE", "/guiones/{id_guion}"),
    ("POST", "/guiones/{id_guion}/versiones"),
    ("POST", "/guiones/{id_guion}/versiones/texto"),
    ("POST", "/escenas"),
    ("PATCH", "/escenas/{id_escena}"),
    ("DELETE", "/escenas/{id_escena}"),
    ("POST", "/escenas/{id_escena}/versiones"),
    ("POST", "/escenas/versiones/{id_escena_version}/fotos"),
    ("POST", "/escenas/{id_escena}/desglose/requerimientos"),
    ("PATCH", "/desglose/requerimientos/{id_requerimiento}"),
    ("DELETE", "/desglose/requerimientos/{id_requerimiento}"),
    ("POST", "/guiones/{id_guion}/desglose/importar"),
    ("POST", "/rodajes"),
    ("PATCH", "/rodajes/{id_rodaje}"),
    ("DELETE", "/rodajes/{id_rodaje}"),
    ("POST", "/rodajes/{id_rodaje}/escenas/{id_escena}"),
    ("DELETE", "/rodajes/{id_rodaje}/escenas/{id_escena}"),
    ("POST", "/projects/{id_project}/rodajes/importar"),
    ("POST", "/rodajes/{id_rodaje}/procesos"),
    ("PATCH", "/rodajes/procesos/{id_proceso}"),
    ("DELETE", "/rodajes/procesos/{id_proceso}"),
    ("POST", "/personajes"),
    ("PATCH", "/personajes/{id_personaje}"),
    ("DELETE", "/personajes/{id_personaje}"),
    ("POST", "/escenarios"),
    ("PATCH", "/escenarios/{id_escenario}"),
    ("DELETE", "/escenarios/{id_escenario}"),
}


def _app_routes():
    # openapi() es la API pública para listar rutas (no depende de clases internas de FastAPI)
    return {
        (metodo.upper(), path)
        for path, operaciones in app.openapi()["paths"].items()
        for metodo in operaciones
    }


def _concrete(path):
    return re.sub(r"\{[^}]+\}", "1", path)


def _call(client, metodo, path, headers=None):
    return client.request(metodo, _concrete(path), headers=headers or {})


def test_the_three_lists_do_not_overlap():
    assert not (PUBLIC & AUTHENTICATED)
    assert not (PUBLIC & ADMIN_ONLY)
    assert not (AUTHENTICATED & ADMIN_ONLY)


def test_every_route_of_the_app_is_classified_and_every_classified_route_exists():
    clasificadas = PUBLIC | AUTHENTICATED | ADMIN_ONLY

    assert _app_routes() == clasificadas


@pytest.mark.parametrize("metodo, path", sorted(AUTHENTICATED | ADMIN_ONLY))
def test_protected_route_returns_401_without_a_token(client, metodo, path):
    assert _call(client, metodo, path).status_code == 401


@pytest.mark.parametrize("metodo, path", sorted(ADMIN_ONLY))
def test_admin_route_returns_403_for_a_non_admin_user(client, member_headers, metodo, path):
    assert _call(client, metodo, path, member_headers).status_code == 403


@pytest.mark.parametrize("metodo, path", sorted(ADMIN_ONLY))
def test_admin_route_lets_an_administrator_through(client, admin_headers, metodo, path):
    # El cuerpo vacío puede dar 422 o un error de negocio: lo único que se verifica es el acceso
    assert _call(client, metodo, path, admin_headers).status_code not in (401, 403)


@pytest.mark.parametrize("metodo, path", sorted(AUTHENTICATED))
def test_authenticated_route_lets_any_logged_in_user_through(client, member_headers, metodo, path):
    assert _call(client, metodo, path, member_headers).status_code not in (401, 403)


@pytest.mark.parametrize("metodo, path", sorted(PUBLIC))
def test_public_route_does_not_ask_for_a_token(client, metodo, path):
    assert _call(client, metodo, path).status_code != 401


class TestTokenValidation:
    def test_rejects_a_token_that_expired(self, client):
        vencido = jwt.encode(
            {"id_user": 1, "id_rol": 1001, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
            SECRET_KEY,
            algorithm=ALGORITHM,
        )

        response = client.get("/users", headers={"Authorization": f"Bearer {vencido}"})

        assert response.status_code == 401
        assert "expirada" in response.json()["detail"]

    def test_rejects_a_token_signed_with_another_secret(self, client):
        falso = jwt.encode({"id_user": 1, "id_rol": 1001}, "x" * 40, algorithm=ALGORITHM)

        assert client.get("/users", headers={"Authorization": f"Bearer {falso}"}).status_code == 401

    def test_rejects_a_token_with_the_none_algorithm(self, client):
        sin_firma = jwt.encode({"id_user": 1, "id_rol": 1001}, None, algorithm="none")

        assert client.get("/users", headers={"Authorization": f"Bearer {sin_firma}"}).status_code == 401

    def test_rejects_a_basic_auth_header(self, client):
        assert client.get("/users", headers={"Authorization": "Basic YTpi"}).status_code == 401
