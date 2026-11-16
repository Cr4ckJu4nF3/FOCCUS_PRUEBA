"""Ramas que el reporte de cobertura marcó como sin probar (análisis de la semana 8).

Cada test nace de una línea/rama concreta de `coverage report`; ver docs/testing/ramas-sin-cubrir.md.
"""
import os

import pytest

from app.models.desglose_model import Desglose
from tests.factories import (
    DEFAULT_PASSWORD,
    link_user,
    make_client,
    make_escena,
    make_guion,
    make_personaje,
    make_project,
    make_requerimiento,
    make_rodaje,
    make_user,
)

pytestmark = pytest.mark.api

PDF = {"archivo": ("x.pdf", b"%PDF-falso", "application/pdf")}


# ───────────── Generación de ids: respaldo cuando el último id no es numérico ─────────────


class TestIdGenerationFallback:
    """Si el último id tiene el prefijo pero no un número («escZZZ»), el siguiente id es 0001.

    Es código defensivo: los ids los genera la propia API, así que solo ocurre con filas
    insertadas a mano. Ojo: si ya existiera «esc0001» el respaldo repetiría el id.
    """

    def test_scene_id_restarts_at_0001(self, client, db, admin_headers):
        guion = make_guion(db, make_project(db))
        make_escena(db, guion, id_escena="escZZZ")

        body = client.post(
            "/escenas", json={"numero_de_escena": "1", "encabezado": "X", "id_guion": guion.id_guion}, headers=admin_headers
        ).json()

        assert body["data"]["id_escena"] == "esc0001"

    def test_character_id_restarts_at_0001(self, client, db, admin_headers):
        proyecto = make_project(db)
        make_personaje(db, proyecto, id_personaje="psjZZZ")

        body = client.post(
            "/personajes", json={"nombre": "Ana", "id_project": proyecto.id_project}, headers=admin_headers
        ).json()

        assert body["data"]["id_personaje"] == "psj0001"

    @pytest.mark.parametrize("id_previo", ["locZZZ", "X-123"], ids=["prefijo-sin-numero", "sin-prefijo"])
    def test_location_id_restarts_at_0001(self, client, db, admin_headers, id_previo):
        from app.models.escenario_model import Escenario

        proyecto = make_project(db)
        db.add(Escenario(id_escenario=id_previo, nombre="Casa", id_project=proyecto.id_project))
        db.commit()

        body = client.post(
            "/escenarios", json={"nombre": "Otra", "id_project": proyecto.id_project}, headers=admin_headers
        ).json()

        assert body["data"]["id_escenario"] == "loc0001"

    def test_shooting_day_id_restarts_at_0001(self, client, db, admin_headers):
        proyecto = make_project(db)
        make_rodaje(db, proyecto, id_rodaje="rodZZZ")

        body = client.post(
            "/rodajes",
            json={"nombre": "Día", "fecha_inicio": "2026-01-05", "id_project": proyecto.id_project},
            headers=admin_headers,
        ).json()

        assert body["data"]["id_rodaje"] == "rod0001"

    def test_project_id_restarts_at_0001(self, client, db, admin_headers):
        empresa = make_client(db)
        make_project(db, id_client=empresa.id_cliente, id_project="projZZZ")

        body = client.post(
            "/projects",
            json={"project_name": "P", "formato_de_produccion": "S", "genero": "D", "id_client": empresa.id_cliente},
            headers=admin_headers,
        ).json()

        assert body["data"]["id_project"] == "proj0001"

    def test_requirement_and_breakdown_ids_restart_at_0001(self, client, db, admin_headers):
        guion = make_guion(db, make_project(db))
        escena = make_escena(db, guion)
        db.add(Desglose(id_desglose="dsgZZZ"))
        db.commit()
        # un requerimiento previo con id no numérico, en un desglose que no es el de la escena
        otra = make_escena(db, guion, numero="2")
        make_requerimiento(db, otra)
        from app.models.desglose_requerimiento_model import DesgloseRequerimiento

        db.query(DesgloseRequerimiento).update({"id_requerimiento": "reqZZZ"})
        db.commit()

        body = client.post(
            f"/escenas/{escena.id_escena}/desglose/requerimientos", json={"departamento": "Props"}, headers=admin_headers
        ).json()

        assert body["data"]["id_requerimiento"] == "req0001"
        assert body["data"]["id_desglose"] == "dsg0001"


# ───────────── Proyectos ─────────────


def test_create_and_link_reports_the_failure_and_creates_no_membership(client, db, member_user, member_headers):
    # El id de respaldo («proj0001» tras un último id no numérico) ya existe: el alta falla
    empresa = make_client(db)
    make_project(db, id_client=empresa.id_cliente, id_project="proj0001")
    make_project(db, id_client=empresa.id_cliente, id_project="projZZZ")

    body = client.post(
        "/projects/create",
        json={
            "project_name": "Otro",
            "formato_de_produccion": "S",
            "genero": "D",
            "id_client": empresa.id_cliente,
            "id_user": member_user.id_user,
        },
        headers=member_headers,
    ).json()

    assert body["error"] == "DUPLICATE_PROJECT"
    from app.models.user_project_model import UserProject

    assert db.query(UserProject).count() == 0


# ───────────── Rodajes y desglose ─────────────


def test_assigning_a_scene_keeps_the_recording_date_it_already_had(client, db, admin_headers):
    from datetime import date

    proyecto = make_project(db)
    guion = make_guion(db, proyecto)
    dia = make_rodaje(db, proyecto, fecha_inicio=date(2026, 1, 5))
    escena = make_escena(db, guion, fecha_de_grabacion=date(2026, 3, 3))

    client.post(f"/rodajes/{dia.id_rodaje}/escenas/{escena.id_escena}", headers=admin_headers)

    db.refresh(escena)
    assert str(escena.fecha_de_grabacion) == "2026-03-03"


def test_the_script_breakdown_includes_the_shooting_day_of_each_scene(client, db, member_headers):
    proyecto = make_project(db)
    guion = make_guion(db, proyecto)
    dia = make_rodaje(db, proyecto, nombre="Día 7")
    make_escena(db, guion, numero="1", id_rodaje=dia.id_rodaje)

    body = client.get(f"/guiones/{guion.id_guion}/desglose", headers=member_headers).json()

    assert dia.id_rodaje in str(body["data"][0])


@pytest.mark.parametrize(
    "ruta, extractor",
    [
        ("/guiones/{guion}/desglose/importar", "desglose_controller"),
        ("/projects/{proyecto}/rodajes/importar", "rodaje_controller"),
    ],
)
def test_a_failure_deleting_the_temporary_pdf_does_not_break_the_import(
    client, db, mocker, admin_headers, ruta, extractor
):
    proyecto = make_project(db)
    guion = make_guion(db, proyecto)
    mocker.patch(f"app.controllers.{extractor}.extraer_texto_pdf", return_value="sin estructura")
    mocker.patch("os.remove", side_effect=OSError("archivo en uso"))

    response = client.post(
        ruta.format(guion=guion.id_guion, proyecto=proyecto.id_project), files=PDF, headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["success"] is False  # "sin estructura": el error esperado, no un 500


# ───────────── Usuarios ─────────────


class TestSessionClientResolution:
    def _verificar_2fa(self, client, mail):
        from app.controllers import user_controller

        client.post("/users/2fa/send", json={"mail": mail, "device_id": "d"})
        codigo = user_controller.two_factor_codes[mail]["codigo"]
        return client.post("/users/2fa/verify", json={"mail": mail, "codigo": codigo, "device_id": "d"}).json()

    def test_login_returns_the_client_stored_on_the_user(self, client, db):
        empresa = make_client(db)
        make_user(db, mail="ana@foccus.test", id_client=empresa.id_cliente)

        body = client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": DEFAULT_PASSWORD}).json()

        assert body["data"]["id_client"] == empresa.id_cliente

    def test_2fa_verify_returns_the_client_stored_on_the_user(self, client, db):
        empresa = make_client(db)
        make_user(db, mail="ana@foccus.test", id_client=empresa.id_cliente)

        assert self._verificar_2fa(client, "ana@foccus.test")["data"]["id_client"] == empresa.id_cliente

    def test_2fa_verify_falls_back_to_the_client_of_the_first_project(self, client, db):
        usuario = make_user(db, mail="ana@foccus.test", id_client=None)
        proyecto = make_project(db)
        link_user(db, usuario, proyecto)

        assert self._verificar_2fa(client, "ana@foccus.test")["data"]["id_client"] == proyecto.id_client

    def test_2fa_verify_returns_no_client_for_a_user_without_company_or_projects(self, client, db):
        make_user(db, mail="ana@foccus.test", id_client=None)

        assert self._verificar_2fa(client, "ana@foccus.test")["data"]["id_client"] is None


def test_reset_password_reports_a_user_deleted_after_requesting_the_code(client, db):
    from app.controllers import user_controller

    usuario = make_user(db, mail="ana@foccus.test")
    client.post("/users/recover-password", json={"mail": "ana@foccus.test"})
    codigo = user_controller.recovery_codes["ana@foccus.test"]["codigo"]
    db.delete(usuario)
    db.commit()

    body = client.post(
        "/users/reset-password",
        json={"mail": "ana@foccus.test", "codigo": codigo, "nueva_contrasena": "Nueva#2026x"},
    ).json()

    assert body["error"] == "USER_NOT_FOUND"


class TestInvitationEdgeCases:
    def _invitar(self, client, headers, proyecto, correos):
        return client.post(
            "/users/invite",
            json={"correos": correos, "id_project": proyecto.id_project, "id_client": proyecto.id_client, "id_rol": 1005},
            headers=headers,
        ).json()

    def test_an_existing_account_is_still_linked_when_its_notification_email_fails(
        self, client, db, admin_headers, no_real_emails, member_user
    ):
        proyecto = make_project(db)
        no_real_emails["send_invitation_email"].side_effect = RuntimeError("SMTP caído")

        body = self._invitar(client, admin_headers, proyecto, ["miembro@foccus.test"])

        assert body["data"]["usuarios_creados"][0]["invitacion_enviada"] is False
        assert body["data"]["usuarios_creados"][0]["usuario_existente"] is True

    @pytest.mark.xfail(
        strict=True,
        reason="H-B27: tras un fallo en flush() la sesión queda sin rollback y todos los correos siguientes fallan",
    )
    def test_one_email_that_cannot_be_processed_is_reported_without_losing_the_others(
        self, client, db, admin_headers
    ):
        proyecto = make_project(db)
        # el identificador temporal «TEMP-a@x.co» ya lo usa otra cuenta: el alta de a@x.co falla
        make_user(db, mail="otro@foccus.test", id_identificacion="TEMP-a@x.co")

        body = self._invitar(client, admin_headers, proyecto, ["a@x.co", "b@x.co"])

        assert [e["mail"] for e in body["data"]["errores"]] == ["a@x.co"]
        assert [u["mail"] for u in body["data"]["usuarios_creados"]] == ["b@x.co"]


def test_the_breakdown_import_restarts_scene_ids_when_the_last_one_is_not_numeric(client, db, mocker, admin_headers):
    proyecto = make_project(db)
    guion = make_guion(db, proyecto)
    make_escena(db, make_guion(db, make_project(db)), id_escena="escZZZ")
    mocker.patch(
        "app.controllers.desglose_controller.extraer_texto_pdf",
        return_value="DÍA 1 · Lunes, 5 de enero 2026 · Bogotá · Llamado: 06:00 ·\n1 INT SALA Noche Props: lámpara 1/8",
    )

    client.post(f"/guiones/{guion.id_guion}/desglose/importar", files=PDF, headers=admin_headers)

    from app.models.escena_model import Escena

    assert db.query(Escena).filter_by(id_guion=guion.id_guion).one().id_escena == "esc0001"
