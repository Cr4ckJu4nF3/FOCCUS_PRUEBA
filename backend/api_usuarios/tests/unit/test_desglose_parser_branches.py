"""Ramas del parser y lectura de un PDF real (análisis de cobertura de la semana 8)."""
import pytest

from app.utils.desglose_parser import extraer_texto_pdf, parse_desglose_pdf, parse_rodaje_pdf

pytestmark = pytest.mark.unit

DIA = "DÍA 1 · Lunes, 5 de enero 2026 · Bogotá · Llamado: 06:00 ·\n"


def pdf_con_texto(lineas):
    """Fabrica un PDF mínimo válido de una página con las líneas dadas (sin librerías de escritura)."""
    contenido = "BT /F1 12 Tf 14 TL 50 750 Td " + " T* ".join(f"({l}) Tj" for l in lineas) + " ET"
    objetos = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(contenido)} >>\nstream\n{contenido}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    salida, offsets = "%PDF-1.4\n", []
    for i, obj in enumerate(objetos, start=1):
        offsets.append(len(salida.encode("latin-1")))
        salida += f"{i} 0 obj\n{obj}\nendobj\n"
    xref = len(salida.encode("latin-1"))
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n"
    salida += "".join(f"{o:010d} 00000 n \n" for o in offsets)
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return salida.encode("latin-1")


class TestExtraerTextoPdf:
    def test_reads_the_text_of_a_real_pdf(self, tmp_path):
        archivo = tmp_path / "desglose.pdf"
        archivo.write_bytes(pdf_con_texto(["Hola Foccus", "Segunda linea"]))

        texto = extraer_texto_pdf(str(archivo))

        assert "Hola Foccus" in texto
        assert "Segunda linea" in texto

    def test_a_real_pdf_goes_through_the_whole_import_pipeline(self, tmp_path):
        # Secuencias octales de WinAnsi: \315 = Í, \267 = ·, \341 = á
        lineas = [
            r"D\315A 1 \267 Lunes, 5 de enero 2026 \267 Bogot\341 \267 Llamado: 06:00 \267",
            r"1 INT SALA Noche Props: l\341mpara 1/8",
        ]
        archivo = tmp_path / "d.pdf"
        archivo.write_bytes(pdf_con_texto(lineas))

        escenas, dias = parse_desglose_pdf(extraer_texto_pdf(str(archivo)))

        assert dias[0]["locacion_general"] == "Bogotá"
        assert escenas[0]["encabezado"] == "SALA"
        assert escenas[0]["requerimientos"][0]["etiqueta"] == "lámpara"

    def test_a_file_that_is_not_a_pdf_raises_an_error(self, tmp_path):
        archivo = tmp_path / "falso.pdf"
        archivo.write_bytes(b"esto no es un pdf")

        with pytest.raises(Exception):
            extraer_texto_pdf(str(archivo))


class TestDesgloseParserBranches:
    def test_a_scene_without_a_page_count_keeps_all_its_text_as_requirements(self):
        texto = DIA + "1 INT SALA Noche Elenco: Julia, Mateo"

        escenas, _ = parse_desglose_pdf(texto)

        assert [r["etiqueta"] for r in escenas[0]["requerimientos"]] == ["Julia", "Mateo"]

    def test_a_stray_page_count_line_before_any_scene_is_ignored(self):
        texto = DIA + "1/8\n1 INT SALA Noche Props: lámpara 1/8"

        escenas, _ = parse_desglose_pdf(texto)

        assert len(escenas) == 1
        assert escenas[0]["ciudad"] is None or "1/8" not in escenas[0]["ciudad"]

    def test_a_lone_scene_number_without_view_mode_produces_no_scene(self):
        texto = DIA + "7\ntexto suelto sin estructura"

        escenas, _ = parse_desglose_pdf(texto)

        assert escenas == []

    def test_a_scene_header_without_time_of_day_is_discarded(self):
        texto = DIA + "1 INT SALA sin momento del dia 1/8"

        escenas, _ = parse_desglose_pdf(texto)

        assert escenas == []


class TestRodajeParserBranches:
    def test_a_scene_header_without_time_of_day_is_skipped(self):
        texto = DIA + "Sc. 1 INT SALA SIN MOMENTO 1 págs.\nSc. 2 EXT PATIO Día 1 págs."

        _, escenas = parse_rodaje_pdf(texto)

        assert [e["numero_de_escena"] for e in escenas] == ["2"]

    def test_blank_lines_are_ignored(self):
        texto = "\n\n" + DIA + "\n\nSc. 1 INT SALA Noche 1 págs.\n\n"

        dias, escenas = parse_rodaje_pdf(texto)

        assert len(dias) == 1 and len(escenas) == 1

    def test_only_the_first_prose_line_is_the_description(self):
        texto = DIA + "Sc. 1 INT SALA Noche 1 págs.\nPrimera línea.\nSegunda línea."

        _, escenas = parse_rodaje_pdf(texto)

        assert escenas[0]["descripcion"] == "Primera línea."

    def test_prose_before_any_scene_becomes_the_specific_location(self):
        texto = DIA + "Casa de Julia\nSc. 1 INT SALA Noche 1 págs."

        _, escenas = parse_rodaje_pdf(texto)

        assert escenas[0]["ciudad"] == "Casa de Julia"


def test_a_stray_page_count_line_before_the_first_scene_of_a_shooting_plan_is_ignored():
    _, escenas = parse_rodaje_pdf(DIA + "1/8\nSc. 1 INT SALA Noche 1 págs.")

    assert len(escenas) == 1
    assert escenas[0]["ciudad"] == "Bogotá"
