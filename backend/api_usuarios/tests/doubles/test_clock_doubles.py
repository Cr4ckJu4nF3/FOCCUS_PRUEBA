"""Reglas que dependen del tiempo, con un RELOJ falso en lugar de esperar o editar el estado interno."""
from datetime import datetime, timedelta

import pytest

from app.controllers import user_controller
from tests.factories import make_user

pytestmark = pytest.mark.doubles

INICIO = datetime(2026, 6, 1, 12, 0, 0)


@pytest.fixture
def reloj(mocker):
    """Reemplaza `datetime` en user_controller por uno cuyo now() se controla."""

    class RelojFalso(datetime):
        ahora = INICIO

        @classmethod
        def now(cls, tz=None):
            return cls.ahora

    mocker.patch.object(user_controller, "datetime", RelojFalso)
    return RelojFalso


def _avanzar(reloj, **delta):
    reloj.ahora = INICIO + timedelta(**delta)


class TestRecoveryCodeWindow:
    """El código de recuperación vale 15 minutos."""

    def _pedir_y_leer_codigo(self, client, db):
        make_user(db, mail="ana@foccus.test")
        client.post("/users/recover-password", json={"mail": "ana@foccus.test"})
        return user_controller.recovery_codes["ana@foccus.test"]["codigo"]

    def _reset(self, client, codigo):
        return client.post(
            "/users/reset-password",
            json={"mail": "ana@foccus.test", "codigo": codigo, "nueva_contrasena": "Nueva#2026x"},
        ).json()

    def test_the_code_still_works_one_second_before_the_deadline(self, client, db, reloj):
        codigo = self._pedir_y_leer_codigo(client, db)
        _avanzar(reloj, minutes=14, seconds=59)

        assert self._reset(client, codigo)["success"] is True

    def test_the_code_still_works_exactly_at_the_deadline(self, client, db, reloj):
        codigo = self._pedir_y_leer_codigo(client, db)
        _avanzar(reloj, minutes=15)

        assert self._reset(client, codigo)["success"] is True

    def test_the_code_expires_one_second_after_the_deadline(self, client, db, reloj):
        codigo = self._pedir_y_leer_codigo(client, db)
        _avanzar(reloj, minutes=15, seconds=1)

        assert self._reset(client, codigo)["error"] == "CODE_EXPIRED"


class TestTwoFactorCodeWindow:
    """El código 2FA vale 10 minutos y la verificación recuerda el dispositivo 5 horas."""

    def _pedir_y_leer_codigo(self, client, db):
        make_user(db, mail="ana@foccus.test", id_rol=1001)
        client.post("/users/2fa/send", json={"mail": "ana@foccus.test", "device_id": "d1"})
        return user_controller.two_factor_codes["ana@foccus.test"]["codigo"]

    def _verificar(self, client, codigo):
        return client.post(
            "/users/2fa/verify", json={"mail": "ana@foccus.test", "codigo": codigo, "device_id": "d1"}
        ).json()

    def test_the_code_works_just_before_the_deadline(self, client, db, reloj):
        codigo = self._pedir_y_leer_codigo(client, db)
        _avanzar(reloj, minutes=9, seconds=59)

        assert self._verificar(client, codigo)["success"] is True

    def test_the_code_expires_just_after_the_deadline(self, client, db, reloj):
        codigo = self._pedir_y_leer_codigo(client, db)
        _avanzar(reloj, minutes=10, seconds=1)

        assert self._verificar(client, codigo)["error"] == "CODE_EXPIRED"

    def test_verifying_remembers_the_device_for_five_hours(self, client, db, reloj):
        codigo = self._pedir_y_leer_codigo(client, db)

        self._verificar(client, codigo)

        assert user_controller.verified_devices["ana@foccus.test:d1"] == INICIO + timedelta(hours=5)
