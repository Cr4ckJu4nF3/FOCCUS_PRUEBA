"""Parser de PDFs de Desglose y Plan de Rodaje (app/utils/desglose_parser.py).

Reciben TEXTO ya extraído del PDF, así que son funciones puras: sin archivos ni BD.
"""
from datetime import date

import pytest

from app.utils.desglose_parser import (
    _limpiar_texto,
    _normalizar_departamento,
    parse_desglose_pdf,
    parse_rodaje_pdf,
)

pytestmark = pytest.mark.unit

DESGLOSE = """SEMANA 1
DÍA 1 · Lunes, 5 de enero 2026 · Bogotá Centro · Llamado: 06:00 ·
Casa de Julia
1 INT SALA Noche Elenco: Julia, Mateo Props: lámpara, libro Vestuario: bata 1/8
2 EXT PATIO Día Props: balón 2/8 Parque Norte
3 INT COCINA Día Props: taza 3/8
Fin Día 1
"""


class TestParseDesglose:
    def test_returns_one_scene_per_scene_block(self):
        escenas, _ = parse_desglose_pdf(DESGLOSE)

        assert [e["numero_de_escena"] for e in escenas] == ["1", "2", "3"]

    def test_extracts_heading_view_mode_and_time_of_day(self):
        escenas, _ = parse_desglose_pdf(DESGLOSE)

        primera = escenas[0]
        assert primera["modo_vista"] == "INT"
        assert primera["encabezado"] == "SALA"
        assert primera["momento_dia"] == "Noche"

    def test_creates_one_requirement_per_comma_separated_item(self):
        escenas, _ = parse_desglose_pdf(DESGLOSE)

        requerimientos = escenas[0]["requerimientos"]
        assert [(r["departamento"], r["etiqueta"]) for r in requerimientos] == [
            ("Elenco", "Julia"),
            ("Elenco", "Mateo"),
            ("Props", "lámpara"),
            ("Props", "libro"),
            ("Vestuario", "bata"),
        ]
        assert all(r["cantidad"] == 1 for r in requerimientos)

    def test_inherits_day_date_and_general_location_from_the_day_header(self):
        escenas, dias = parse_desglose_pdf(DESGLOSE)

        assert escenas[0]["dia_dramatico"] == 1
        assert escenas[0]["fecha_de_grabacion"] == date(2026, 1, 5)
        assert dias == [
            {
                "dia_dramatico": 1,
                "semana": 1,
                "fecha": date(2026, 1, 5),
                "locacion_general": "Bogotá Centro",
                "llamado": "06:00",
            }
        ]

    def test_uses_the_specific_location_line_before_the_first_scene(self):
        escenas, _ = parse_desglose_pdf(DESGLOSE)

        assert escenas[0]["ciudad"] == "Casa de Julia"

    def test_text_after_the_page_count_becomes_the_next_scene_location(self):
        # "2/8 Parque Norte": lo que sigue al conteo de páginas es la locación de la siguiente
        escenas, _ = parse_desglose_pdf(DESGLOSE)

        assert escenas[1]["ciudad"] == "Casa de Julia"
        assert escenas[2]["ciudad"] == "Parque Norte"

    def test_date_is_none_when_the_day_does_not_exist_in_the_calendar(self):
        texto = "DÍA 2 · Martes, 31 de febrero 2026 · Medellín · \n4 INT OFICINA Tarde Notas: llegar temprano 1/8"

        escenas, dias = parse_desglose_pdf(texto)

        assert dias[0]["fecha"] is None
        assert escenas[0]["fecha_de_grabacion"] is None

    def test_date_is_none_when_the_month_name_is_unknown(self):
        texto = "DÍA 1 · Lunes, 5 de smarch 2026 · Bogotá · \n1 INT SALA Día Props: taza 1/8"

        _, dias = parse_desglose_pdf(texto)

        assert dias[0]["fecha"] is None

    def test_call_time_is_none_when_the_day_header_has_no_call_time(self):
        texto = "DÍA 2 · Martes, 6 de enero 2026 · Medellín · "

        _, dias = parse_desglose_pdf(texto)

        assert dias[0]["llamado"] is None

    @pytest.mark.parametrize("texto", ["", "   \n  ", "texto sin ninguna estructura de desglose"])
    def test_returns_empty_lists_when_there_is_no_recognizable_structure(self, texto):
        assert parse_desglose_pdf(texto) == ([], [])

    def test_skips_a_scene_whose_time_of_day_is_missing(self):
        texto = "DÍA 1 · Lunes, 5 de enero 2026 · Bogotá · \n1 INT SALA Props: taza 1/8"

        escenas, _ = parse_desglose_pdf(texto)

        assert escenas == []

    def test_discards_browser_print_noise_lines(self):
        ruido = (
            "5/1/26, 10:30 AM Desglose\nabout:blank\nSC. INT/EXT   PÁGS.\n"
            "Documento de uso interno\n"
        )

        escenas, _ = parse_desglose_pdf(ruido + DESGLOSE)

        assert len(escenas) == 3


class TestLimpiarTexto:
    def test_separates_the_time_of_day_glued_to_the_last_heading_word(self):
        # Algunos extractores de PDF pegan el momento del día: "TRASEROAmanecer"
        assert "TRASERO Amanecer" in _limpiar_texto("1 EXT TRASEROAmanecer")

    def test_keeps_text_that_is_not_noise(self):
        assert _limpiar_texto("Elenco: Julia") == "Elenco: Julia"


class TestNormalizarDepartamento:
    @pytest.mark.parametrize(
        "etiqueta, esperado",
        [
            ("props", "Props"),
            ("  PROPS ", "Props"),
            ("cámara", "Cámara"),
            ("camara", "Cámara"),
            ("extras/bg", "Extras / BG"),
            ("extras  /  bg", "Extras / BG"),
            ("maquillaje fx", "Maquillaje FX"),
            ("maquillaje", "Maquillaje y Pelo"),
            ("vehiculos", "Vehículos"),
        ],
    )
    def test_maps_known_labels_to_the_internal_catalog_name(self, etiqueta, esperado):
        assert _normalizar_departamento(etiqueta) == esperado

    def test_returns_the_trimmed_label_when_it_is_unknown(self):
        assert _normalizar_departamento("  Catering ") == "Catering"


RODAJE = """SEMANA 2
DÍA 3 · Miércoles, 7 de enero 2026 · Bogotá Norte · Llamado: 07:30 ·
Plaza Bolívar
Sc. 5 EXT PLAZA Día 1 2/8 págs.
Julia espera a Mateo en la plaza.
ELENCO: Julia
Sc. 6 INT BAR Noche 3 págs.
Fin Día 3
"""


class TestParseRodaje:
    def test_returns_the_shooting_days_with_week_date_and_call_time(self):
        dias, _ = parse_rodaje_pdf(RODAJE)

        assert dias == [
            {
                "dia_dramatico": 3,
                "semana": 2,
                "fecha": date(2026, 1, 7),
                "locacion_general": "Bogotá Norte",
                "llamado": "07:30",
            }
        ]

    def test_extracts_scene_number_view_mode_heading_and_time_of_day(self):
        _, escenas = parse_rodaje_pdf(RODAJE)

        assert escenas[0]["numero_de_escena"] == "5"
        assert escenas[0]["modo_vista"] == "EXT"
        assert escenas[0]["encabezado"] == "PLAZA"
        assert escenas[0]["momento_dia"] == "Día"

    def test_uses_the_first_prose_line_as_description(self):
        _, escenas = parse_rodaje_pdf(RODAJE)

        assert escenas[0]["descripcion"] == "Julia espera a Mateo en la plaza."

    def test_description_is_none_when_the_scene_has_no_synopsis(self):
        _, escenas = parse_rodaje_pdf(RODAJE)

        assert escenas[1]["descripcion"] is None

    def test_does_not_use_a_department_line_as_description(self):
        texto = "DÍA 1 · Lunes, 5 de enero 2026 · Bogotá · \nSc. 1 INT SALA Día 1 págs.\nELENCO: Julia"

        _, escenas = parse_rodaje_pdf(texto)

        assert escenas[0]["descripcion"] is None

    def test_scenes_inherit_day_and_date(self):
        _, escenas = parse_rodaje_pdf(RODAJE)

        assert {e["dia_dramatico"] for e in escenas} == {3}
        assert {e["fecha_de_grabacion"] for e in escenas} == {date(2026, 1, 7)}

    def test_returns_empty_lists_when_text_is_empty(self):
        assert parse_rodaje_pdf("") == ([], [])
