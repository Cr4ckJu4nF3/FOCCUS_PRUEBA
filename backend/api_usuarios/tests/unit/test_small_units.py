"""Funciones pequeñas: format_text, api_response, validación de schemas y guardado de archivos."""
import io

import pytest
from fastapi import UploadFile
from pydantic import ValidationError

from app.controllers.user_controller import format_text
from app.schemas.user_schema import RegisterSchema, ResetPasswordSchema
from app.utils.file_storage import (
    EXTENSIONES_FOTO,
    EXTENSIONES_GUION,
    guardar_archivo,
)
from app.utils.response import api_response

pytestmark = pytest.mark.unit


class TestFormatText:
    @pytest.mark.parametrize(
        "entrada, esperado",
        [
            ("juan pérez", "Juan Pérez"),
            ("  MARÍA  ", "María"),
            ("ana", "Ana"),
            ("", ""),
        ],
    )
    def test_trims_and_capitalizes_each_word(self, entrada, esperado):
        assert format_text(entrada) == esperado

    @pytest.mark.parametrize("valor", [None, 5, ["a"]])
    def test_returns_non_string_values_untouched(self, valor):
        assert format_text(valor) == valor


class TestApiResponse:
    def test_builds_the_standard_envelope(self):
        assert api_response(True, "ok", {"a": 1}) == {
            "success": True,
            "message": "ok",
            "data": {"a": 1},
            "error": None,
        }

    def test_carries_the_error_code_when_it_fails(self):
        respuesta = api_response(False, "mal", error="CODIGO")

        assert respuesta["success"] is False
        assert respuesta["error"] == "CODIGO"
        assert respuesta["data"] is None


REGISTRO = dict(
    razon_social="Productora",
    representante_legal="Laura",
    email_empresa="e@x.co",
    document="NIT",
    id_document="900",
    nombre="Ana",
    apellido="Ruiz",
    mail="ana@x.co",
    msisdn="300",
)


class TestPasswordLengthRule:
    """bcrypt solo admite 72 bytes: el schema lo rechaza antes de llegar al hash."""

    def test_register_accepts_a_password_of_exactly_72_bytes(self):
        RegisterSchema(**REGISTRO, contrasena="a" * 72)

    def test_register_rejects_a_password_of_73_bytes(self):
        with pytest.raises(ValidationError, match="72 bytes"):
            RegisterSchema(**REGISTRO, contrasena="a" * 73)

    def test_counts_bytes_not_characters(self):
        # "ñ" ocupa 2 bytes en UTF-8: 37 letras = 74 bytes aunque sean menos de 72 caracteres
        with pytest.raises(ValidationError, match="72 bytes"):
            RegisterSchema(**REGISTRO, contrasena="ñ" * 37)

    def test_reset_password_applies_the_same_rule(self):
        with pytest.raises(ValidationError, match="72 bytes"):
            ResetPasswordSchema(mail="a@x.co", codigo="123456", nueva_contrasena="b" * 73)


def _upload(nombre, contenido=b"datos"):
    return UploadFile(filename=nombre, file=io.BytesIO(contenido))


class TestGuardarArchivo:
    def test_saves_the_content_and_returns_a_relative_path_with_forward_slashes(self, upload_dir):
        ruta = guardar_archivo(_upload("Guion.PDF", b"%PDF-1"), "guiones/3")

        assert ruta.startswith("uploads/guiones/3/")
        assert "\\" not in ruta
        guardado = upload_dir / ruta.removeprefix("uploads/")
        assert guardado.read_bytes() == b"%PDF-1"

    def test_lowercases_the_extension(self, upload_dir):
        assert guardar_archivo(_upload("Guion.PDF"), "g").endswith(".pdf")

    def test_never_reuses_the_original_name_so_two_uploads_do_not_collide(self, upload_dir):
        primera = guardar_archivo(_upload("mi-guion-original.pdf"), "g")
        segunda = guardar_archivo(_upload("mi-guion-original.pdf"), "g")

        assert primera != segunda
        assert "mi-guion-original" not in primera

    @pytest.mark.parametrize("nombre", ["virus.exe", "guion.txt", "sin_extension", ""])
    def test_rejects_extensions_that_are_not_allowed(self, upload_dir, nombre):
        with pytest.raises(ValueError, match="no permitida"):
            guardar_archivo(_upload(nombre), "g", EXTENSIONES_GUION)

    def test_accepts_any_extension_when_no_whitelist_is_given(self, upload_dir):
        assert guardar_archivo(_upload("nota.txt"), "g").endswith(".txt")

    def test_photos_whitelist_allows_images_but_not_documents(self, upload_dir):
        assert guardar_archivo(_upload("a.webp"), "f", EXTENSIONES_FOTO).endswith(".webp")
        with pytest.raises(ValueError):
            guardar_archivo(_upload("a.pdf"), "f", EXTENSIONES_FOTO)
