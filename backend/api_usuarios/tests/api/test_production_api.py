"""Rodajes, desglose, continuidad, personajes, escenarios y contacto."""
import pytest

from app.models.desglose_requerimiento_model import DesgloseRequerimiento
from app.models.escena_model import Escena
from app.models.proceso_rodaje_model import ProcesoRodaje
from app.models.rodaje_model import Rodaje
from tests.factories import (
    make_escena,
    make_guion,
    make_personaje,
    make_project,
    make_requerimiento,
    make_rodaje,
)

pytestmark = pytest.mark.api


@pytest.fixture
def proyecto(db):
    return make_project(db)


@pytest.fixture
def guion(db, proyecto):
    return make_guion(db, proyecto)


RODAJE = dict(nombre="Día 1", fecha_inicio="2026-01-05", dia_dramatico=1, semana=1, llamado="06:00")


class TestRodajes:
    def test_admin_creates_a_shooting_day_with_a_sequential_id(self, client, proyecto, admin_headers):
        primero = client.post("/rodajes", json={**RODAJE, "id_project": proyecto.id_project}, headers=admin_headers)
        segundo = client.post("/rodajes", json={**RODAJE, "id_project": proyecto.id_project}, headers=admin_headers)

        assert primero.json()["data"]["id_rodaje"] == "rod0001"
        assert segundo.json()["data"]["id_rodaje"] == "rod0002"
        assert primero.json()["data"]["estado"] == "Pendiente"

    def test_rejects_a_shooting_day_for_a_missing_project(self, client, admin_headers):
        body = client.post("/rodajes", json={**RODAJE, "id_project": "nada"}, headers=admin_headers).json()

        assert body["error"] == "PROJECT_NOT_FOUND"

    def test_returns_422_when_the_start_date_is_not_a_date(self, client, proyecto, admin_headers):
        response = client.post(
            "/rodajes",
            json={**RODAJE, "id_project": proyecto.id_project, "fecha_inicio": "mañana"},
            headers=admin_headers,
        )

        assert response.status_code == 422

    def test_lists_the_days_of_a_project_ordered_by_dramatic_day_with_their_scenes(
        self, client, db, proyecto, guion, member_headers
    ):
        dia2 = make_rodaje(db, proyecto, nombre="Día 2", dia_dramatico=2)
        dia1 = make_rodaje(db, proyecto, nombre="Día 1", dia_dramatico=1)
        make_escena(db, guion, numero="3", id_rodaje=dia1.id_rodaje)

        body = client.get(f"/projects/{proyecto.id_project}/rodajes", headers=member_headers).json()

        assert [r["nombre"] for r in body["data"]] == ["Día 1", "Día 2"]
        assert [e["numero_de_escena"] for e in body["data"][0]["escenas"]] == ["3"]

    def test_gets_a_day_and_reports_a_missing_one(self, client, db, proyecto, member_headers):
        dia = make_rodaje(db, proyecto)

        assert client.get(f"/rodajes/{dia.id_rodaje}", headers=member_headers).json()["success"] is True
        assert client.get("/rodajes/nada", headers=member_headers).json()["message"] == (
            "Plan de rodaje no encontrado"
        )

    def test_patch_changes_only_the_fields_that_are_sent(self, client, db, proyecto, admin_headers):
        dia = make_rodaje(db, proyecto, llamado="06:00", locacion="Bogotá")

        client.patch(f"/rodajes/{dia.id_rodaje}", json={"llamado": "07:30"}, headers=admin_headers)

        db.refresh(dia)
        assert (dia.llamado, dia.locacion) == ("07:30", "Bogotá")

    def test_admin_deletes_a_day(self, client, db, proyecto, admin_headers):
        dia = make_rodaje(db, proyecto)

        assert client.delete(f"/rodajes/{dia.id_rodaje}", headers=admin_headers).json()["success"] is True
        assert db.query(Rodaje).count() == 0

    @pytest.mark.parametrize("metodo", ["patch", "delete"])
    def test_changing_a_missing_day_is_reported(self, client, admin_headers, metodo):
        kwargs = {"json": {"llamado": "x"}} if metodo == "patch" else {}

        body = getattr(client, metodo)("/rodajes/nada", headers=admin_headers, **kwargs).json()

        assert body["message"] == "Plan de rodaje no encontrado"


class TestAssigningScenesToShootingDays:
    def test_assigning_a_scene_copies_the_day_number_and_date_when_the_scene_has_none(
        self, client, db, proyecto, guion, admin_headers
    ):
        dia = make_rodaje(db, proyecto, dia_dramatico=4)
        escena = make_escena(db, guion)

        body = client.post(f"/rodajes/{dia.id_rodaje}/escenas/{escena.id_escena}", headers=admin_headers).json()

        assert body["success"] is True
        db.refresh(escena)
        assert escena.id_rodaje == dia.id_rodaje
        assert escena.dia_dramatico == 4
        assert str(escena.fecha_de_grabacion) == "2026-01-05"

    def test_assigning_keeps_the_scene_own_dramatic_day_when_it_already_has_one(
        self, client, db, proyecto, guion, admin_headers
    ):
        dia = make_rodaje(db, proyecto, dia_dramatico=4)
        escena = make_escena(db, guion, dia_dramatico=9)

        client.post(f"/rodajes/{dia.id_rodaje}/escenas/{escena.id_escena}", headers=admin_headers)

        db.refresh(escena)
        assert escena.dia_dramatico == 9

    def test_assigning_reports_a_missing_day_or_scene(self, client, db, proyecto, guion, admin_headers):
        dia = make_rodaje(db, proyecto)
        escena = make_escena(db, guion)

        sin_dia = client.post(f"/rodajes/nada/escenas/{escena.id_escena}", headers=admin_headers).json()
        sin_escena = client.post(f"/rodajes/{dia.id_rodaje}/escenas/nada", headers=admin_headers).json()

        assert sin_dia["message"] == "Plan de rodaje no encontrado"
        assert sin_escena["message"] == "Escena no encontrada"

    def test_removing_a_scene_unassigns_it_without_deleting_it(self, client, db, proyecto, guion, admin_headers):
        dia = make_rodaje(db, proyecto)
        escena = make_escena(db, guion, id_rodaje=dia.id_rodaje)

        body = client.delete(f"/rodajes/{dia.id_rodaje}/escenas/{escena.id_escena}", headers=admin_headers).json()

        assert body["success"] is True
        db.refresh(escena)
        assert escena.id_rodaje is None

    def test_removing_a_scene_that_is_not_assigned_is_reported(self, client, db, proyecto, guion, admin_headers):
        dia = make_rodaje(db, proyecto)
        escena = make_escena(db, guion)

        body = client.delete(f"/rodajes/{dia.id_rodaje}/escenas/{escena.id_escena}", headers=admin_headers).json()

        assert body["success"] is False

    def test_lists_only_the_project_scenes_that_have_no_shooting_day(
        self, client, db, proyecto, guion, member_headers
    ):
        dia = make_rodaje(db, proyecto)
        make_escena(db, guion, numero="1")
        make_escena(db, guion, numero="2", id_rodaje=dia.id_rodaje)
        ajeno = make_guion(db, make_project(db))
        make_escena(db, ajeno, numero="9")

        body = client.get(f"/projects/{proyecto.id_project}/escenas-disponibles", headers=member_headers).json()

        assert [e["numero_de_escena"] for e in body["data"]] == ["1"]


class TestShootingProcesses:
    PROCESO = dict(nombre="Scouting", ubicacion="Parque", fecha="2026-01-04", encargado="Luis", orden=2)

    def test_admin_adds_lists_updates_and_deletes_a_process(self, client, db, proyecto, admin_headers, member_headers):
        dia = make_rodaje(db, proyecto)

        creado = client.post(f"/rodajes/{dia.id_rodaje}/procesos", json=self.PROCESO, headers=admin_headers).json()
        id_proceso = creado["data"]["id_proceso"]
        listado = client.get(f"/rodajes/{dia.id_rodaje}/procesos", headers=member_headers).json()
        editado = client.patch(
            f"/rodajes/procesos/{id_proceso}", json={"estado": "Hecho"}, headers=admin_headers
        ).json()
        estado_guardado = db.get(ProcesoRodaje, id_proceso).estado
        borrado = client.delete(f"/rodajes/procesos/{id_proceso}", headers=admin_headers).json()

        assert estado_guardado == "Hecho"
        assert creado["success"] is True
        assert [p["nombre"] for p in listado["data"]] == ["Scouting"]
        assert editado["success"] is True
        assert borrado["success"] is True
        assert db.query(ProcesoRodaje).count() == 0

    def test_lists_processes_ordered_by_their_order_field(self, client, db, proyecto, admin_headers, member_headers):
        dia = make_rodaje(db, proyecto)
        client.post(f"/rodajes/{dia.id_rodaje}/procesos", json={**self.PROCESO, "nombre": "B", "orden": 2}, headers=admin_headers)
        client.post(f"/rodajes/{dia.id_rodaje}/procesos", json={**self.PROCESO, "nombre": "A", "orden": 1}, headers=admin_headers)

        body = client.get(f"/rodajes/{dia.id_rodaje}/procesos", headers=member_headers).json()

        assert [p["nombre"] for p in body["data"]] == ["A", "B"]

    def test_adding_a_process_to_a_missing_day_is_reported(self, client, admin_headers):
        body = client.post("/rodajes/nada/procesos", json=self.PROCESO, headers=admin_headers).json()

        assert body["error"] == "RODAJE_NOT_FOUND"

    @pytest.mark.parametrize("metodo", ["patch", "delete"])
    def test_changing_a_missing_process_is_reported(self, client, admin_headers, metodo):
        kwargs = {"json": {"estado": "x"}} if metodo == "patch" else {}

        body = getattr(client, metodo)("/rodajes/procesos/9999", headers=admin_headers, **kwargs).json()

        assert body["message"] == "Proceso no encontrado"


class TestBreakdownRequirements:
    def test_adding_a_requirement_creates_the_scene_breakdown_on_demand(
        self, client, db, guion, admin_headers
    ):
        escena = make_escena(db, guion)
        assert escena.id_desglose is None

        body = client.post(
            f"/escenas/{escena.id_escena}/desglose/requerimientos",
            json={"departamento": "Props", "etiqueta": "lámpara", "cantidad": 2},
            headers=admin_headers,
        ).json()

        assert body["data"]["id_requerimiento"] == "req0001"
        db.refresh(escena)
        assert escena.id_desglose == body["data"]["id_desglose"]

    def test_quantity_defaults_to_one(self, client, db, guion, admin_headers):
        escena = make_escena(db, guion)

        body = client.post(
            f"/escenas/{escena.id_escena}/desglose/requerimientos", json={"departamento": "Props"}, headers=admin_headers
        ).json()

        assert body["data"]["cantidad"] == 1

    def test_a_second_requirement_reuses_the_same_breakdown(self, client, db, guion, admin_headers):
        escena = make_escena(db, guion)
        ruta = f"/escenas/{escena.id_escena}/desglose/requerimientos"

        a = client.post(ruta, json={"departamento": "Props"}, headers=admin_headers).json()["data"]
        b = client.post(ruta, json={"departamento": "Vestuario"}, headers=admin_headers).json()["data"]

        assert a["id_desglose"] == b["id_desglose"]

    def test_adding_to_a_missing_scene_is_reported(self, client, admin_headers):
        body = client.post(
            "/escenas/nada/desglose/requerimientos", json={"departamento": "Props"}, headers=admin_headers
        ).json()

        assert body["message"] == "Escena no encontrada"

    def test_reads_the_breakdown_of_one_scene(self, client, db, guion, member_headers):
        escena = make_escena(db, guion)
        make_requerimiento(db, escena, "Vestuario", "bata")
        make_requerimiento(db, escena, "Props", "lámpara")

        body = client.get(f"/escenas/{escena.id_escena}/desglose", headers=member_headers).json()

        assert [r["departamento"] for r in body["data"]["requerimientos"]] == ["Props", "Vestuario"]

    def test_a_scene_without_breakdown_returns_an_empty_list(self, client, db, guion, member_headers):
        escena = make_escena(db, guion)

        assert client.get(f"/escenas/{escena.id_escena}/desglose", headers=member_headers).json()["data"][
            "requerimientos"
        ] == []

    def test_reading_the_breakdown_of_a_missing_scene_is_reported(self, client, member_headers):
        assert client.get("/escenas/nada/desglose", headers=member_headers).json()["message"] == (
            "Escena no encontrada"
        )

    def test_the_script_breakdown_summarizes_quantities_per_department(
        self, client, db, guion, member_headers
    ):
        escena = make_escena(db, guion, numero="1", dia_dramatico=1)
        make_requerimiento(db, escena, "Props", "lámpara", cantidad=2)
        make_requerimiento(db, escena, "Props", "libro", cantidad=1)
        make_requerimiento(db, escena, "Vestuario", "bata", cantidad=1)

        body = client.get(f"/guiones/{guion.id_guion}/desglose", headers=member_headers).json()

        fila = body["data"][0]
        assert fila["total_requerimientos"] == 3
        assert {d["departamento"]: d["cantidad"] for d in fila["resumen_departamentos"]} == {"Props": 3, "Vestuario": 1}

    def test_the_script_breakdown_lists_scenes_without_a_dramatic_day_last(
        self, client, db, guion, member_headers
    ):
        make_escena(db, guion, numero="1", dia_dramatico=None)
        make_escena(db, guion, numero="2", dia_dramatico=1)

        body = client.get(f"/guiones/{guion.id_guion}/desglose", headers=member_headers).json()

        assert [e["numero_de_escena"] for e in body["data"]] == ["2", "1"]

    def test_updates_and_deletes_a_requirement(self, client, db, guion, admin_headers):
        escena = make_escena(db, guion)
        req = make_requerimiento(db, escena)

        editado = client.patch(
            f"/desglose/requerimientos/{req.id_requerimiento}", json={"cantidad": 5}, headers=admin_headers
        ).json()
        borrado = client.delete(f"/desglose/requerimientos/{req.id_requerimiento}", headers=admin_headers).json()

        assert editado["data"]["cantidad"] == 5
        assert borrado["success"] is True
        assert db.query(DesgloseRequerimiento).count() == 0

    @pytest.mark.parametrize("metodo", ["patch", "delete"])
    def test_changing_a_missing_requirement_is_reported(self, client, admin_headers, metodo):
        kwargs = {"json": {"cantidad": 1}} if metodo == "patch" else {}

        body = getattr(client, metodo)("/desglose/requerimientos/nada", headers=admin_headers, **kwargs).json()

        assert body["message"] == "Requerimiento no encontrado"


class TestPdfImportErrors:
    NO_ES_PDF = {"archivo": ("falso.pdf", b"esto no es un pdf", "application/pdf")}

    def test_breakdown_import_reports_a_file_that_is_not_a_readable_pdf(self, client, guion, admin_headers):
        body = client.post(
            f"/guiones/{guion.id_guion}/desglose/importar", files=self.NO_ES_PDF, headers=admin_headers
        ).json()

        assert body["error"] == "PDF_READ_ERROR"

    def test_shooting_plan_import_reports_a_file_that_is_not_a_readable_pdf(self, client, proyecto, admin_headers):
        body = client.post(
            f"/projects/{proyecto.id_project}/rodajes/importar", files=self.NO_ES_PDF, headers=admin_headers
        ).json()

        assert body["error"] == "PDF_READ_ERROR"


class TestContinuity:
    @pytest.fixture
    def escena(self, db, guion):
        return make_escena(db, guion)

    def _nueva_version(self, client, escena, headers, comentario=None):
        data = {"comentario_cambio": comentario} if comentario else {}
        return client.post(f"/escenas/{escena.id_escena}/versiones", data=data, headers=headers).json()

    def test_each_continuity_version_gets_the_next_number_and_records_the_author(
        self, client, escena, admin_headers, admin_user
    ):
        uno = self._nueva_version(client, escena, admin_headers, "Inicial")["data"]
        dos = self._nueva_version(client, escena, admin_headers)["data"]

        assert (uno["numero_version"], dos["numero_version"]) == (1, 2)

    def test_creating_a_version_for_a_missing_scene_is_reported(self, client, admin_headers):
        body = client.post("/escenas/nada/versiones", headers=admin_headers).json()

        assert body["message"] == "Escena no encontrada"

    def test_lists_versions_newest_first(self, client, escena, admin_headers, member_headers):
        self._nueva_version(client, escena, admin_headers)
        self._nueva_version(client, escena, admin_headers)

        body = client.get(f"/escenas/{escena.id_escena}/versiones", headers=member_headers).json()

        assert [v["numero_version"] for v in body["data"]] == [2, 1]

    def test_uploads_several_photos_to_a_version(self, client, escena, admin_headers, upload_dir):
        version = self._nueva_version(client, escena, admin_headers)["data"]["id_escena_version"]

        body = client.post(
            f"/escenas/versiones/{version}/fotos",
            data={"tipo": "vestuario", "etiqueta": "Bata azul"},
            files=[
                ("archivos", ("a.jpg", b"\xff\xd8a", "image/jpeg")),
                ("archivos", ("b.png", b"\x89PNGb", "image/png")),
            ],
            headers=admin_headers,
        ).json()

        assert len(body["data"]) == 2
        assert len(list(upload_dir.rglob("*"))) >= 2

    def test_filters_photos_by_type(self, client, escena, admin_headers, member_headers, upload_dir):
        version = self._nueva_version(client, escena, admin_headers)["data"]["id_escena_version"]
        for tipo in ("vestuario", "objeto"):
            client.post(
                f"/escenas/versiones/{version}/fotos",
                data={"tipo": tipo},
                files=[("archivos", ("a.jpg", b"x", "image/jpeg"))],
                headers=admin_headers,
            )

        todas = client.get(f"/escenas/versiones/{version}/fotos", headers=member_headers).json()["data"]
        objetos = client.get(f"/escenas/versiones/{version}/fotos?tipo=objeto", headers=member_headers).json()["data"]

        assert len(todas) == 2
        assert [f["tipo"] for f in objetos] == ["objeto"]

    def test_rejects_an_invalid_photo_type(self, client, escena, admin_headers, upload_dir):
        version = self._nueva_version(client, escena, admin_headers)["data"]["id_escena_version"]

        body = client.post(
            f"/escenas/versiones/{version}/fotos",
            data={"tipo": "sonido"},
            files=[("archivos", ("a.jpg", b"x", "image/jpeg"))],
            headers=admin_headers,
        ).json()

        assert body["error"] == "INVALID_TIPO"

    def test_rejects_a_photo_with_a_forbidden_extension(self, client, escena, admin_headers, upload_dir):
        version = self._nueva_version(client, escena, admin_headers)["data"]["id_escena_version"]

        body = client.post(
            f"/escenas/versiones/{version}/fotos",
            data={"tipo": "objeto"},
            files=[("archivos", ("a.pdf", b"x", "application/pdf"))],
            headers=admin_headers,
        ).json()

        assert body["error"] == "INVALID_FILE"

    def test_uploading_to_a_missing_version_is_reported(self, client, admin_headers, upload_dir):
        body = client.post(
            "/escenas/versiones/9999/fotos",
            data={"tipo": "objeto"},
            files=[("archivos", ("a.jpg", b"x", "image/jpeg"))],
            headers=admin_headers,
        ).json()

        assert body["message"] == "Version de escena no encontrada"


class TestCharactersAndLocations:
    def test_admin_manages_the_characters_of_a_project(self, client, db, proyecto, admin_headers, member_headers):
        creado = client.post(
            "/personajes", json={"nombre": "Julia", "id_project": proyecto.id_project}, headers=admin_headers
        ).json()
        id_personaje = creado["data"]["id_personaje"]
        editado = client.patch(f"/personajes/{id_personaje}", json={"descripcion": "Protagonista"}, headers=admin_headers).json()
        listado = client.get(f"/projects/{proyecto.id_project}/personajes", headers=member_headers).json()
        borrado = client.delete(f"/personajes/{id_personaje}", headers=admin_headers).json()

        assert id_personaje == "psj0001"
        assert editado["data"]["descripcion"] == "Protagonista"
        assert [p["nombre"] for p in listado["data"]] == ["Julia"]
        assert borrado["success"] is True

    def test_lists_characters_alphabetically(self, client, db, proyecto, member_headers):
        make_personaje(db, proyecto, nombre="Zoe")
        make_personaje(db, proyecto, nombre="Ana")

        body = client.get(f"/projects/{proyecto.id_project}/personajes", headers=member_headers).json()

        assert [p["nombre"] for p in body["data"]] == ["Ana", "Zoe"]

    @pytest.mark.parametrize("metodo", ["patch", "delete"])
    def test_changing_a_missing_character_is_reported(self, client, admin_headers, metodo):
        kwargs = {"json": {"nombre": "x"}} if metodo == "patch" else {}

        assert getattr(client, metodo)("/personajes/nada", headers=admin_headers, **kwargs).json()["message"] == (
            "Personaje no encontrado"
        )

    def test_admin_manages_the_locations_of_a_project(self, client, proyecto, admin_headers, member_headers):
        creado = client.post(
            "/escenarios",
            json={"nombre": "Casa de Julia", "tipo": "locación", "id_project": proyecto.id_project},
            headers=admin_headers,
        ).json()
        id_escenario = creado["data"]["id_escenario"]
        editado = client.patch(f"/escenarios/{id_escenario}", json={"nombre": "Casa nueva"}, headers=admin_headers).json()
        listado = client.get(f"/projects/{proyecto.id_project}/escenarios", headers=member_headers).json()
        borrado = client.delete(f"/escenarios/{id_escenario}", headers=admin_headers).json()

        assert editado["data"]["nombre"] == "Casa nueva"
        assert [e["nombre"] for e in listado["data"]] == ["Casa nueva"]
        assert borrado["success"] is True

    @pytest.mark.parametrize("metodo", ["patch", "delete"])
    def test_changing_a_missing_location_is_reported(self, client, admin_headers, metodo):
        kwargs = {"json": {"nombre": "x"}} if metodo == "patch" else {}

        assert getattr(client, metodo)("/escenarios/nada", headers=admin_headers, **kwargs).json()["message"] == (
            "Escenario no encontrado"
        )


class TestContact:
    FORMULARIO = dict(nombre="Ana", email="ana@x.co", celular="300", mensaje="Quiero una demo")

    def test_a_visitor_without_session_can_send_the_contact_form(self, client, no_real_emails):
        body = client.post("/contact", json=self.FORMULARIO).json()

        assert body["success"] is True
        no_real_emails["send_contact_email"].assert_called_once_with(
            nombre="Ana", email="ana@x.co", celular="300", empresa="", tipo="demo", mensaje="Quiero una demo"
        )

    def test_reports_a_mail_error_when_the_message_cannot_be_delivered(self, client, no_real_emails):
        no_real_emails["send_contact_email"].return_value = False

        assert client.post("/contact", json=self.FORMULARIO).json()["error"] == "MAIL_ERROR"

    def test_returns_422_when_the_message_is_missing(self, client):
        incompleto = {k: v for k, v in self.FORMULARIO.items() if k != "mensaje"}

        assert client.post("/contact", json=incompleto).status_code == 422
