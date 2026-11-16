"""Guiones (con versiones y notas) y escenas."""
import pytest

from app.models.escena_model import Escena
from app.models.Guion import Guion
from app.models.guion_version_model import GuionVersion
from tests.factories import make_escena, make_guion, make_guion_version, make_project

pytestmark = pytest.mark.api

PDF = ("guion.pdf", b"%PDF-1.4 contenido", "application/pdf")


@pytest.fixture
def proyecto(db):
    return make_project(db)


@pytest.fixture
def guion(db, proyecto, admin_user):
    g = make_guion(db, proyecto, nombre="Piloto")
    make_guion_version(db, g, admin_user, numero=1)
    return g


class TestCreateGuion:
    def test_creates_the_master_record_without_a_version(self, client, proyecto, admin_headers):
        body = client.post(
            "/guiones", json={"nombre": "Piloto", "id_project": proyecto.id_project}, headers=admin_headers
        ).json()

        assert body["success"] is True
        assert body["data"]["id_project"] == proyecto.id_project

    def test_creates_a_script_written_in_the_system_with_its_first_version(
        self, client, db, proyecto, admin_headers, admin_user
    ):
        body = client.post(
            "/guiones/texto",
            json={
                "nombre": "Piloto",
                "id_project": proyecto.id_project,
                "contenido": "INT. SALA - NOCHE",
                "fecha_de_emision": "2026-01-05",
            },
            headers=admin_headers,
        ).json()

        assert body["data"]["numero_de_version"] == 1
        version = db.get(GuionVersion, body["data"]["id_guion_version"])
        assert version.contenido == "INT. SALA - NOCHE"
        assert version.creado_por == admin_user.id_user
        assert db.get(Guion, body["data"]["id_guion"]).id_guion_version_actual == version.id_guion_version

    def test_uploads_a_script_file_as_version_one(self, client, db, proyecto, admin_headers, upload_dir):
        body = client.post(
            "/guiones/archivo",
            data={"nombre": "Piloto", "id_project": proyecto.id_project},
            files={"archivo": PDF},
            headers=admin_headers,
        ).json()

        assert body["success"] is True
        assert body["data"]["numero_de_version"] == 1
        archivos = list(upload_dir.rglob("*.pdf"))
        assert len(archivos) == 1
        assert archivos[0].read_bytes() == PDF[1]

    def test_rejects_a_file_with_a_forbidden_extension_and_leaves_no_script_behind(
        self, client, db, proyecto, admin_headers, upload_dir
    ):
        body = client.post(
            "/guiones/archivo",
            data={"nombre": "Piloto", "id_project": proyecto.id_project},
            files={"archivo": ("virus.exe", b"MZ", "application/octet-stream")},
            headers=admin_headers,
        ).json()

        assert body["error"] == "INVALID_FILE"
        assert db.query(Guion).count() == 0

    def test_returns_422_when_the_file_is_missing(self, client, proyecto, admin_headers):
        response = client.post(
            "/guiones/archivo", data={"nombre": "x", "id_project": proyecto.id_project}, headers=admin_headers
        )

        assert response.status_code == 422


class TestReadGuiones:
    def test_lists_scripts_newest_first_and_filters_by_project(self, client, db, member_headers, proyecto, admin_user):
        otro_proyecto = make_project(db)
        viejo = make_guion(db, proyecto, nombre="Viejo")
        nuevo = make_guion(db, proyecto, nombre="Nuevo")
        make_guion(db, otro_proyecto, nombre="Ajeno")

        body = client.get(f"/guiones?id_project={proyecto.id_project}", headers=member_headers).json()

        assert [g["nombre"] for g in body["data"]] == ["Nuevo", "Viejo"]

    def test_shows_the_current_version_state_and_origin(self, client, guion, member_headers):
        body = client.get(f"/guiones/{guion.id_guion}", headers=member_headers).json()

        assert body["data"]["numero_de_version_actual"] == 1
        assert body["data"]["estado_actual"] == "Borrador"
        assert body["data"]["origen_actual"] == "texto"

    def test_a_script_without_versions_has_no_current_version(self, client, db, proyecto, member_headers):
        sin_versiones = make_guion(db, proyecto)

        data = client.get(f"/guiones/{sin_versiones.id_guion}", headers=member_headers).json()["data"]

        assert data["numero_de_version_actual"] is None
        assert data["origen_actual"] is None

    def test_reports_a_script_that_does_not_exist(self, client, member_headers):
        assert client.get("/guiones/9999", headers=member_headers).json()["message"] == "Guion no encontrado"

    def test_admin_patches_and_deletes_a_script(self, client, db, proyecto, admin_headers):
        g = make_guion(db, proyecto, nombre="Viejo")

        client.patch(f"/guiones/{g.id_guion}", json={"nombre": "Nuevo"}, headers=admin_headers)
        db.refresh(g)
        assert g.nombre == "Nuevo"

        assert client.delete(f"/guiones/{g.id_guion}", headers=admin_headers).json()["success"] is True
        assert db.query(Guion).count() == 0

    @pytest.mark.parametrize("metodo", ["patch", "delete"])
    def test_changing_a_missing_script_is_reported(self, client, admin_headers, metodo):
        kwargs = {"json": {"nombre": "x"}} if metodo == "patch" else {}

        body = getattr(client, metodo)("/guiones/9999", headers=admin_headers, **kwargs).json()

        assert body["message"] == "Guion no encontrado"


class TestGuionVersions:
    def test_a_text_version_gets_the_next_number_and_becomes_the_current_one(
        self, client, db, guion, admin_headers
    ):
        body = client.post(
            f"/guiones/{guion.id_guion}/versiones/texto",
            json={"contenido": "INT. COCINA - DÍA", "fecha_de_emision": "2026-02-01", "estado": "Final"},
            headers=admin_headers,
        ).json()

        assert body["data"]["numero_de_version"] == 2
        db.refresh(guion)
        assert guion.id_guion_version_actual == body["data"]["id_guion_version"]

    def test_a_file_version_keeps_the_numbering_going(self, client, guion, admin_headers, upload_dir):
        body = client.post(
            f"/guiones/{guion.id_guion}/versiones",
            data={"fecha_de_emision": "2026-02-01", "comentario_cambio": "Ajustes"},
            files={"archivo": PDF},
            headers=admin_headers,
        ).json()

        assert body["data"]["numero_de_version"] == 2
        assert body["data"]["estado"] == "Borrador"

    def test_rejects_a_version_file_with_a_forbidden_extension(self, client, guion, admin_headers, upload_dir):
        body = client.post(
            f"/guiones/{guion.id_guion}/versiones",
            data={"fecha_de_emision": "2026-02-01"},
            files={"archivo": ("x.exe", b"MZ", "application/octet-stream")},
            headers=admin_headers,
        ).json()

        assert body["error"] == "INVALID_FILE"

    @pytest.mark.parametrize("ruta", ["versiones/texto", "versiones"])
    def test_adding_a_version_to_a_missing_script_is_reported(self, client, admin_headers, upload_dir, ruta):
        if ruta == "versiones/texto":
            kwargs = {"json": {"contenido": "x", "fecha_de_emision": "2026-02-01"}}
        else:
            kwargs = {"data": {"fecha_de_emision": "2026-02-01"}, "files": {"archivo": PDF}}

        body = client.post(f"/guiones/9999/{ruta}", headers=admin_headers, **kwargs).json()

        assert body["message"] == "Guion no encontrado"

    def test_lists_versions_newest_first(self, client, db, guion, admin_user, member_headers):
        make_guion_version(db, guion, admin_user, numero=2, estado="Final")

        body = client.get(f"/guiones/{guion.id_guion}/versiones", headers=member_headers).json()

        assert [v["numero_de_version"] for v in body["data"]] == [2, 1]


class TestGuionNotes:
    def test_any_logged_user_can_add_and_read_a_note(self, client, db, guion, member_user, member_headers):
        version_id = guion.id_guion_version_actual

        creada = client.post(
            f"/guiones/versiones/{version_id}/notas", json={"contenido": "Revisar diálogo"}, headers=member_headers
        ).json()
        listada = client.get(f"/guiones/versiones/{version_id}/notas", headers=member_headers).json()

        assert creada["success"] is True
        assert [n["contenido"] for n in listada["data"]] == ["Revisar diálogo"]

    def test_adding_a_note_to_a_missing_version_is_reported(self, client, member_headers):
        body = client.post("/guiones/versiones/9999/notas", json={"contenido": "x"}, headers=member_headers).json()

        assert body["message"] == "Version de guion no encontrada"


ESCENA = dict(numero_de_escena="5", encabezado="SALA", modo_vista="INT", momento_dia="Noche", pagina=3)


class TestEscenas:
    def test_admin_creates_a_scene_with_a_sequential_id_and_pending_state(self, client, guion, admin_headers):
        primera = client.post("/escenas", json={**ESCENA, "id_guion": guion.id_guion}, headers=admin_headers).json()
        segunda = client.post("/escenas", json={**ESCENA, "id_guion": guion.id_guion}, headers=admin_headers).json()

        assert primera["data"]["id_escena"] == "esc0001"
        assert segunda["data"]["id_escena"] == "esc0002"
        assert primera["data"]["estado"] == "Pendiente"

    def test_rejects_a_scene_for_a_script_that_does_not_exist(self, client, admin_headers):
        body = client.post("/escenas", json={**ESCENA, "id_guion": 9999}, headers=admin_headers).json()

        assert body["error"] == "GUION_NOT_FOUND"

    def test_lists_the_scenes_of_a_script(self, client, db, guion, member_headers):
        make_escena(db, guion, numero="1")
        make_escena(db, guion, numero="2")

        body = client.get(f"/guiones/{guion.id_guion}/escenas", headers=member_headers).json()

        assert [e["numero_de_escena"] for e in body["data"]] == ["1", "2"]

    def test_gets_a_scene_and_reports_a_missing_one(self, client, db, guion, member_headers):
        escena = make_escena(db, guion, numero="7")

        assert client.get(f"/escenas/{escena.id_escena}", headers=member_headers).json()["data"]["numero_de_escena"] == "7"
        assert client.get("/escenas/nada", headers=member_headers).json()["message"] == "Escena no encontrada"

    def test_patch_changes_only_the_fields_that_are_sent(self, client, db, guion, admin_headers):
        escena = make_escena(db, guion, encabezado="SALA", ciudad="Bogotá")

        client.patch(f"/escenas/{escena.id_escena}", json={"estado": "Grabada"}, headers=admin_headers)

        db.refresh(escena)
        assert (escena.estado, escena.encabezado, escena.ciudad) == ("Grabada", "SALA", "Bogotá")

    def test_admin_deletes_a_scene(self, client, db, guion, admin_headers):
        escena = make_escena(db, guion)

        assert client.delete(f"/escenas/{escena.id_escena}", headers=admin_headers).json()["success"] is True
        assert db.query(Escena).count() == 0

    @pytest.mark.parametrize("metodo", ["patch", "delete"])
    def test_changing_a_missing_scene_is_reported(self, client, admin_headers, metodo):
        kwargs = {"json": {"estado": "x"}} if metodo == "patch" else {}

        assert getattr(client, metodo)("/escenas/nada", headers=admin_headers, **kwargs).json()["message"] == (
            "Escena no encontrada"
        )
