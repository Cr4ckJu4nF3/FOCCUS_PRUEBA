"""Registro, login, 2FA y recuperación de contraseña (contrato HTTP).

Nota de contrato: esta API responde HTTP 200 también cuando la operación de negocio
falla; el fallo va en el cuerpo {"success": false, "error": "<CÓDIGO>"}. Solo la
autenticación (401/403) y la validación de Pydantic (422) usan otros códigos.
"""
from datetime import datetime, timedelta

import pytest

from app.controllers import user_controller
from tests.factories import DEFAULT_PASSWORD, make_user

pytestmark = pytest.mark.api

REGISTRO = dict(
    razon_social="productora sur",
    representante_legal="laura gómez",
    email_empresa="Contacto@Sur.co",
    address="calle 1",
    telephone="6010000",
    number_cellphone="3000000000",
    document="NIT",
    id_document="900123",
    nombre="camila",
    apellido="prueba",
    mail="  Camila@Sur.co ",
    msisdn="3001112233",
    contrasena=DEFAULT_PASSWORD,
)


class TestRegister:
    def test_creates_company_and_administrator_and_returns_a_token(self, client):
        response = client.post("/register", json=REGISTRO)

        body = response.json()
        assert response.status_code == 200
        assert body["success"] is True
        assert body["data"]["access_token"]
        assert body["data"]["id_cliente"]

    def test_normalizes_names_and_lowercases_the_email(self, client):
        data = client.post("/register", json=REGISTRO).json()["data"]

        assert data["nombre"] == "Camila"
        assert data["apellido"] == "Prueba"
        assert data["razon_social"] == "Productora Sur"
        assert data["mail"] == "camila@sur.co"

    def test_new_user_can_log_in_with_the_registered_password(self, client):
        client.post("/register", json=REGISTRO)

        login = client.post("/users/login", json={"mail": "camila@sur.co", "contrasena": DEFAULT_PASSWORD})

        assert login.json()["success"] is True

    def test_registered_user_is_an_administrator(self, client):
        client.post("/register", json=REGISTRO)

        login = client.post("/users/login", json={"mail": "camila@sur.co", "contrasena": DEFAULT_PASSWORD})

        assert login.json()["data"]["id_rol"] == 1001

    def test_rejects_a_company_email_that_is_already_registered(self, client):
        client.post("/register", json=REGISTRO)
        otro_usuario = {**REGISTRO, "email_empresa": "contacto@sur.co", "mail": "otra@persona.co", "id_document": "555"}

        body = client.post("/register", json=otro_usuario).json()

        assert body["success"] is False
        assert body["error"] == "DUPLICATE_CLIENT"

    def test_rejects_a_user_email_that_is_already_registered(self, client):
        client.post("/register", json=REGISTRO)
        otra_empresa = {**REGISTRO, "email_empresa": "otra@empresa.co", "mail": "camila@sur.co", "id_document": "777"}

        body = client.post("/register", json=otra_empresa).json()

        assert body["success"] is False
        assert body["error"] == "DUPLICATE_USER"

    @pytest.mark.parametrize("campo", ["razon_social", "email_empresa", "mail", "contrasena", "nombre", "document"])
    def test_returns_422_when_a_required_field_is_missing(self, client, campo):
        incompleto = {k: v for k, v in REGISTRO.items() if k != campo}

        response = client.post("/register", json=incompleto)

        assert response.status_code == 422

    def test_returns_422_when_the_password_exceeds_72_bytes(self, client):
        response = client.post("/register", json={**REGISTRO, "contrasena": "a" * 73})

        assert response.status_code == 422


class TestLogin:
    def test_returns_session_data_and_a_token_when_credentials_are_valid(self, client, db):
        make_user(db, mail="ana@foccus.test", id_rol=1005)

        body = client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": DEFAULT_PASSWORD}).json()

        assert body["success"] is True
        assert body["data"]["mail"] == "ana@foccus.test"
        assert body["data"]["id_rol"] == 1005
        assert body["data"]["token_type"] == "bearer"
        assert body["data"]["access_token"]

    def test_never_returns_the_password_hash(self, client, db):
        make_user(db, mail="ana@foccus.test")

        response = client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": DEFAULT_PASSWORD})

        assert "contrasena" not in response.json()["data"]
        assert "$2b$" not in response.text

    def test_accepts_the_email_with_uppercase_and_surrounding_spaces(self, client, db):
        make_user(db, mail="ana@foccus.test")

        body = client.post("/users/login", json={"mail": "  ANA@Foccus.test ", "contrasena": DEFAULT_PASSWORD}).json()

        assert body["success"] is True

    def test_reports_an_unknown_email(self, client):
        body = client.post("/users/login", json={"mail": "nadie@foccus.test", "contrasena": "x"}).json()

        assert body["success"] is False
        assert body["error"] == "USER_NOT_FOUND"

    def test_reports_a_wrong_password(self, client, db):
        make_user(db, mail="ana@foccus.test")

        body = client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": "equivocada"}).json()

        assert body["success"] is False
        assert body["error"] == "INVALID_PASSWORD"

    def test_falls_back_to_the_client_of_the_first_project_when_the_user_has_no_client(self, client, db):
        from tests.factories import link_user, make_project

        usuario = make_user(db, mail="invitado@foccus.test", id_client=None)
        proyecto = make_project(db)
        link_user(db, usuario, proyecto)

        body = client.post("/users/login", json={"mail": "invitado@foccus.test", "contrasena": DEFAULT_PASSWORD}).json()

        assert body["data"]["id_client"] == proyecto.id_client

    def test_updates_the_last_access_timestamp(self, client, db):
        usuario = make_user(db, mail="ana@foccus.test", ultimo_acceso=datetime(2020, 1, 1))

        client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": DEFAULT_PASSWORD})

        db.refresh(usuario)
        assert usuario.ultimo_acceso > datetime(2020, 1, 1)

    def test_token_from_login_opens_a_protected_route(self, client, db):
        make_user(db, mail="ana@foccus.test", id_rol=1001)
        token = client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": DEFAULT_PASSWORD}).json()[
            "data"
        ]["access_token"]

        response = client.get("/users", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200


class TestTwoFactor:
    def test_check_always_requires_verification(self, client):
        body = client.post("/users/2fa/check", json={"mail": "a@x.co", "device_id": "d1"}).json()

        assert body["data"]["requires_2fa"] is True

    def test_send_emails_a_six_digit_code_and_remembers_it(self, client, db, no_real_emails):
        make_user(db, mail="ana@foccus.test")

        body = client.post("/users/2fa/send", json={"mail": "ana@foccus.test", "device_id": "d1"}).json()

        assert body["success"] is True
        correo, codigo = no_real_emails["send_2fa_email"].call_args.args
        assert correo == "ana@foccus.test"
        assert len(codigo) == 6 and codigo.isdigit()
        assert user_controller.two_factor_codes["ana@foccus.test"]["codigo"] == codigo

    def test_send_reports_an_unknown_user(self, client):
        body = client.post("/users/2fa/send", json={"mail": "nadie@foccus.test", "device_id": "d1"}).json()

        assert body["error"] == "USER_NOT_FOUND"

    def test_send_reports_a_mail_error_when_the_email_cannot_be_delivered(self, client, db, no_real_emails):
        make_user(db, mail="ana@foccus.test")
        no_real_emails["send_2fa_email"].return_value = False

        body = client.post("/users/2fa/send", json={"mail": "ana@foccus.test", "device_id": "d1"}).json()

        assert body["error"] == "MAIL_ERROR"

    def _request_code(self, client, db, mail="ana@foccus.test"):
        make_user(db, mail=mail, id_rol=1001)
        client.post("/users/2fa/send", json={"mail": mail, "device_id": "d1"})
        return user_controller.two_factor_codes[mail]["codigo"]

    def test_verify_returns_a_session_when_the_code_is_correct(self, client, db):
        codigo = self._request_code(client, db)

        body = client.post(
            "/users/2fa/verify", json={"mail": "ana@foccus.test", "codigo": codigo, "device_id": "d1"}
        ).json()

        assert body["success"] is True
        assert body["data"]["access_token"]
        assert body["data"]["device_verified"] is True

    def test_a_code_can_only_be_used_once(self, client, db):
        codigo = self._request_code(client, db)
        payload = {"mail": "ana@foccus.test", "codigo": codigo, "device_id": "d1"}
        client.post("/users/2fa/verify", json=payload)

        segundo = client.post("/users/2fa/verify", json=payload).json()

        assert segundo["error"] == "NO_CODE"

    def test_verify_rejects_a_wrong_code_and_keeps_the_pending_one(self, client, db):
        codigo = self._request_code(client, db)
        mala = "000000" if codigo != "000000" else "111111"

        body = client.post(
            "/users/2fa/verify", json={"mail": "ana@foccus.test", "codigo": mala, "device_id": "d1"}
        ).json()

        assert body["error"] == "INVALID_CODE"
        assert "ana@foccus.test" in user_controller.two_factor_codes

    def test_verify_reports_when_no_code_was_requested(self, client):
        body = client.post(
            "/users/2fa/verify", json={"mail": "ana@foccus.test", "codigo": "123456", "device_id": "d1"}
        ).json()

        assert body["error"] == "NO_CODE"

    def test_verify_rejects_an_expired_code_and_discards_it(self, client, db):
        codigo = self._request_code(client, db)
        user_controller.two_factor_codes["ana@foccus.test"]["expira"] = datetime.now() - timedelta(seconds=1)

        body = client.post(
            "/users/2fa/verify", json={"mail": "ana@foccus.test", "codigo": codigo, "device_id": "d1"}
        ).json()

        assert body["error"] == "CODE_EXPIRED"
        assert "ana@foccus.test" not in user_controller.two_factor_codes


class TestPasswordRecovery:
    def test_emails_a_recovery_code_to_a_registered_user(self, client, db, no_real_emails):
        make_user(db, mail="ana@foccus.test")

        body = client.post("/users/recover-password", json={"mail": "ana@foccus.test"}).json()

        assert body["success"] is True
        no_real_emails["send_recovery_email"].assert_called_once()
        assert user_controller.recovery_codes["ana@foccus.test"]["codigo"]

    def test_normalizes_the_email_before_looking_it_up(self, client, db):
        make_user(db, mail="ana@foccus.test")

        body = client.post("/users/recover-password", json={"mail": "  ANA@foccus.test "}).json()

        assert body["success"] is True

    def test_reports_an_unknown_email(self, client):
        body = client.post("/users/recover-password", json={"mail": "nadie@foccus.test"}).json()

        assert body["error"] == "USER_NOT_FOUND"

    def test_reports_a_mail_error_when_the_email_cannot_be_delivered(self, client, db, no_real_emails):
        make_user(db, mail="ana@foccus.test")
        no_real_emails["send_recovery_email"].return_value = False

        body = client.post("/users/recover-password", json={"mail": "ana@foccus.test"}).json()

        assert body["error"] == "MAIL_ERROR"

    def _request_recovery(self, client, db):
        usuario = make_user(db, mail="ana@foccus.test")
        client.post("/users/recover-password", json={"mail": "ana@foccus.test"})
        return usuario, user_controller.recovery_codes["ana@foccus.test"]["codigo"]

    def test_reset_changes_the_password_so_only_the_new_one_works(self, client, db):
        _, codigo = self._request_recovery(client, db)

        reset = client.post(
            "/users/reset-password",
            json={"mail": "ana@foccus.test", "codigo": codigo, "nueva_contrasena": "Nueva#2026x"},
        ).json()

        assert reset["success"] is True
        viejo = client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": DEFAULT_PASSWORD}).json()
        nuevo = client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": "Nueva#2026x"}).json()
        assert viejo["success"] is False
        assert nuevo["success"] is True

    def test_reset_code_cannot_be_reused(self, client, db):
        _, codigo = self._request_recovery(client, db)
        payload = {"mail": "ana@foccus.test", "codigo": codigo, "nueva_contrasena": "Nueva#2026x"}
        client.post("/users/reset-password", json=payload)

        segundo = client.post("/users/reset-password", json=payload).json()

        assert segundo["error"] == "NO_REQUEST"

    def test_reset_rejects_a_wrong_code_and_keeps_the_old_password(self, client, db):
        _, codigo = self._request_recovery(client, db)
        mala = "000000" if codigo != "000000" else "111111"

        body = client.post(
            "/users/reset-password",
            json={"mail": "ana@foccus.test", "codigo": mala, "nueva_contrasena": "Nueva#2026x"},
        ).json()

        assert body["error"] == "INVALID_CODE"
        login = client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": DEFAULT_PASSWORD}).json()
        assert login["success"] is True

    def test_reset_rejects_an_expired_code(self, client, db):
        _, codigo = self._request_recovery(client, db)
        user_controller.recovery_codes["ana@foccus.test"]["expira"] = datetime.now() - timedelta(seconds=1)

        body = client.post(
            "/users/reset-password",
            json={"mail": "ana@foccus.test", "codigo": codigo, "nueva_contrasena": "Nueva#2026x"},
        ).json()

        assert body["error"] == "CODE_EXPIRED"

    def test_reset_reports_when_there_is_no_pending_request(self, client):
        body = client.post(
            "/users/reset-password",
            json={"mail": "ana@foccus.test", "codigo": "123456", "nueva_contrasena": "Nueva#2026x"},
        ).json()

        assert body["error"] == "NO_REQUEST"

    def test_reset_returns_422_when_the_new_password_exceeds_72_bytes(self, client):
        response = client.post(
            "/users/reset-password",
            json={"mail": "a@x.co", "codigo": "123456", "nueva_contrasena": "a" * 73},
        )

        assert response.status_code == 422
