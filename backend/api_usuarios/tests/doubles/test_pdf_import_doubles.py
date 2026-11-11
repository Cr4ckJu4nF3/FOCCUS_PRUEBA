"""Importación de PDFs de desglose y de plan de rodaje.

El extractor de texto (`extraer_texto_pdf`) se reemplaza por un STUB que devuelve
texto ya armado. Así se prueba la lógica de importación (crear/actualizar escenas,
asignar días) sin fabricar PDFs, y el SPY sobre el stub permite comprobar que el
archivo temporal se entrega al extractor y se borra después.
"""
import os

import pytest

from app.models.desglose_requerimiento_model import DesgloseRequerimiento
from app.models.escena_model import Escena
from app.models.rodaje_model import Rodaje
from tests.factories import make_escena, make_guion, make_project, make_rodaje

pytestmark = pytest.mark.doubles

PDF = {"archivo": ("desglose.pdf", b"%PDF-falso", "application/pdf")}

TEXTO_DESGLOSE = """SEMANA 1
DÍA 1 · Lunes, 5 de enero 2026 · Bogotá Centro · Llamado: 06:00 ·
Casa de Julia
1 INT SALA Noche Elenco: Julia, Mateo Props: lámpara 1/8
2 EXT PATIO Día Props: balón 2/8
"""

TEXTO_RODAJE = """SEMANA 1
DÍA 1 · Lunes, 5 de enero 2026 · Bogotá Centro · Llamado: 06:00 ·
Sc. 1 INT SALA Noche 1 págs.
Julia llega a casa.
DÍA 2 · Martes, 6 de enero 2026 · Medellín · Llamado: 07:30 ·
Sc. 2 EXT PATIO Día 1 págs.
"""


@pytest.fixture
def proyecto(db):
    return make_project(db)


@pytest.fixture
def guion(db, proyecto):
    return make_guion(db, proyecto)


def _stub_texto(mocker, modulo, texto):
    return mocker.patch(f"app.controllers.{modulo}.extraer_texto_pdf", return_value=texto)


class TestDesgloseImport:
    def _importar(self, client, guion, headers):
        return client.post(f"/guiones/{guion.id_guion}/desglose/importar", files=PDF, headers=headers).json()

    def test_creates_scenes_and_requirements_from_the_pdf_text(self, client, db, mocker, guion, admin_headers):
        _stub_texto(mocker, "desglose_controller", TEXTO_DESGLOSE)

        body = self._importar(client, guion, admin_headers)

        assert body["data"] == {
            "escenas_creadas": 2,
            "escenas_actualizadas": 0,
            "requerimientos_creados": 4,
            "total_escenas_en_pdf": 2,
        }
        escena = db.query(Escena).filter_by(id_guion=guion.id_guion, numero_de_escena="1").one()
        assert (escena.modo_vista, escena.momento_dia, escena.ciudad) == ("INT", "Noche", "Casa de Julia")
        assert str(escena.fecha_de_grabacion) == "2026-01-05"

    def test_importing_the_same_file_twice_updates_instead_of_duplicating(
        self, client, db, mocker, guion, admin_headers
    ):
        _stub_texto(mocker, "desglose_controller", TEXTO_DESGLOSE)
        self._importar(client, guion, admin_headers)

        segunda = self._importar(client, guion, admin_headers)

        assert segunda["data"]["escenas_creadas"] == 0
        assert segunda["data"]["escenas_actualizadas"] == 2
        assert db.query(Escena).count() == 2
        assert db.query(DesgloseRequerimiento).count() == 4

    def test_reimporting_replaces_the_requirements_of_an_existing_scene(
        self, client, db, mocker, guion, admin_headers
    ):
        escena = make_escena(db, guion, numero="1")
        from tests.factories import make_requerimiento

        make_requerimiento(db, escena, "Sonido", "micrófono viejo")
        _stub_texto(mocker, "desglose_controller", TEXTO_DESGLOSE)

        self._importar(client, guion, admin_headers)

        etiquetas = {r.etiqueta for r in db.query(DesgloseRequerimiento).all()}
        assert "micrófono viejo" not in etiquetas
        assert {"Julia", "Mateo", "lámpara"} <= etiquetas

    def test_reports_a_pdf_without_recognizable_scenes(self, client, mocker, guion, admin_headers):
        _stub_texto(mocker, "desglose_controller", "un texto cualquiera sin estructura")

        body = self._importar(client, guion, admin_headers)

        assert body["error"] == "NO_SCENES_FOUND"

    def test_reports_a_read_error_raised_by_the_extractor(self, client, mocker, guion, admin_headers):
        mocker.patch(
            "app.controllers.desglose_controller.extraer_texto_pdf", side_effect=ValueError("PDF cifrado")
        )

        body = self._importar(client, guion, admin_headers)

        assert body["error"] == "PDF_READ_ERROR"
        assert "PDF cifrado" in body["message"]

    def test_hands_a_temporary_pdf_to_the_extractor_and_deletes_it_afterwards(
        self, client, mocker, guion, admin_headers
    ):
        espia = _stub_texto(mocker, "desglose_controller", TEXTO_DESGLOSE)

        self._importar(client, guion, admin_headers)

        ruta = espia.call_args.args[0]
        assert ruta.endswith(".pdf")
        assert not os.path.exists(ruta)

    def test_deletes_the_temporary_file_even_when_the_extractor_fails(self, client, mocker, guion, admin_headers):
        espia = mocker.patch(
            "app.controllers.desglose_controller.extraer_texto_pdf", side_effect=RuntimeError("boom")
        )

        self._importar(client, guion, admin_headers)

        assert not os.path.exists(espia.call_args.args[0])


class TestShootingPlanImport:
    def _importar(self, client, proyecto, headers):
        return client.post(f"/projects/{proyecto.id_project}/rodajes/importar", files=PDF, headers=headers).json()

    def test_creates_one_shooting_day_per_day_in_the_pdf(self, client, db, mocker, proyecto, admin_headers):
        _stub_texto(mocker, "rodaje_controller", TEXTO_RODAJE)

        body = self._importar(client, proyecto, admin_headers)

        assert body["data"]["dias_creados"] == 2
        dia1 = db.query(Rodaje).filter_by(id_project=proyecto.id_project, dia_dramatico=1).one()
        assert (dia1.nombre, dia1.llamado, dia1.locacion, dia1.semana) == ("Día 1", "06:00", "Bogotá Centro", 1)
        assert str(dia1.fecha_inicio) == "2026-01-05"

    def test_assigns_existing_scenes_to_their_day_by_scene_number(
        self, client, db, mocker, proyecto, guion, admin_headers
    ):
        escena1 = make_escena(db, guion, numero="1")
        escena2 = make_escena(db, guion, numero="2")
        _stub_texto(mocker, "rodaje_controller", TEXTO_RODAJE)

        body = self._importar(client, proyecto, admin_headers)

        assert body["data"]["escenas_asignadas"] == 2
        db.refresh(escena1)
        db.refresh(escena2)
        assert escena1.id_rodaje != escena2.id_rodaje
        assert escena1.descripcion == "Julia llega a casa."

    def test_ignores_pdf_scenes_that_do_not_exist_in_the_project(self, client, db, mocker, proyecto, admin_headers):
        _stub_texto(mocker, "rodaje_controller", TEXTO_RODAJE)

        body = self._importar(client, proyecto, admin_headers)

        assert body["data"]["escenas_asignadas"] == 0

    def test_importing_again_updates_the_existing_days(self, client, db, mocker, proyecto, admin_headers):
        make_rodaje(db, proyecto, dia_dramatico=1, llamado="05:00")
        _stub_texto(mocker, "rodaje_controller", TEXTO_RODAJE)

        body = self._importar(client, proyecto, admin_headers)

        assert (body["data"]["dias_creados"], body["data"]["dias_actualizados"]) == (1, 1)
        assert db.query(Rodaje).filter_by(dia_dramatico=1).one().llamado == "06:00"

    def test_reports_a_pdf_without_recognizable_days(self, client, mocker, proyecto, admin_headers):
        _stub_texto(mocker, "rodaje_controller", "sin días")

        assert self._importar(client, proyecto, admin_headers)["error"] == "NO_DAYS_FOUND"

    def test_reports_a_read_error_raised_by_the_extractor(self, client, mocker, proyecto, admin_headers):
        mocker.patch("app.controllers.rodaje_controller.extraer_texto_pdf", side_effect=ValueError("ilegible"))

        assert self._importar(client, proyecto, admin_headers)["error"] == "PDF_READ_ERROR"
