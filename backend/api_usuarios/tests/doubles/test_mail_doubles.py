"""app/utils/mail.py con el servidor SMTP reemplazado por un MOCK.

Ninguna prueba abre una conexión real a smtp.gmail.com. Se verifican las
interacciones con el servidor (starttls → login → sendmail → quit) y el contenido
del mensaje, que es lo que hace este módulo.
"""
import email
from email import policy

import pytest

from app.utils import mail

pytestmark = pytest.mark.doubles


@pytest.fixture
def smtp(mocker):
    """Reemplaza smtplib.SMTP; devuelve el servidor falso para inspeccionarlo."""
    clase = mocker.patch("app.utils.mail.smtplib.SMTP")
    return clase.return_value, clase


def _mensaje_enviado(servidor):
    """Reconstruye el correo que recibió sendmail()."""
    remitente, destinatario, crudo = servidor.sendmail.call_args.args
    return remitente, destinatario, email.message_from_string(crudo, policy=policy.default)


def _html(mensaje):
    return mensaje.get_body(preferencelist=("html",)).get_content()


ENVIOS = [
    ("send_recovery_email", ("ana@x.co", "123456"), "Recuperación de contraseña - Foccus", "123456"),
    ("send_2fa_email", ("ana@x.co", "654321"), "Código de verificación - Foccus", "654321"),
    (
        "send_invitation_email",
        ("ana@x.co", "Mi serie", "Temporal123"),
        None,  # el asunto de la invitación se comprueba aparte
        "Temporal123",
    ),
]


@pytest.mark.parametrize("funcion, argumentos, asunto, dato_clave", ENVIOS)
class TestUserFacingEmails:
    def test_follows_the_smtp_handshake_with_the_configured_credentials(
        self, smtp, funcion, argumentos, asunto, dato_clave
    ):
        servidor, clase = smtp

        resultado = getattr(mail, funcion)(*argumentos)

        assert resultado is True
        clase.assert_called_once_with("smtp.gmail.com", 587)
        servidor.starttls.assert_called_once()
        servidor.login.assert_called_once_with("no-reply@foccus.test", "not-a-real-password")
        servidor.quit.assert_called_once()

    def test_sends_one_message_to_the_recipient_that_contains_the_key_data(
        self, smtp, funcion, argumentos, asunto, dato_clave
    ):
        servidor, _ = smtp

        getattr(mail, funcion)(*argumentos)

        servidor.sendmail.assert_called_once()
        remitente, destinatario, mensaje = _mensaje_enviado(servidor)
        assert remitente == "no-reply@foccus.test"
        assert destinatario == "ana@x.co"
        assert mensaje["To"] == "ana@x.co"
        assert dato_clave in _html(mensaje)
        if asunto:
            assert mensaje["Subject"] == asunto

    def test_embeds_the_logo_as_an_inline_image(self, smtp, funcion, argumentos, asunto, dato_clave):
        servidor, _ = smtp

        getattr(mail, funcion)(*argumentos)

        _, _, mensaje = _mensaje_enviado(servidor)
        imagenes = [p for p in mensaje.walk() if p.get_content_maintype() == "image"]
        assert len(imagenes) == 1
        assert imagenes[0]["Content-ID"] == "<logo>"

    def test_returns_false_instead_of_raising_when_the_smtp_login_fails(
        self, smtp, funcion, argumentos, asunto, dato_clave
    ):
        servidor, _ = smtp
        servidor.login.side_effect = RuntimeError("credenciales rechazadas")

        assert getattr(mail, funcion)(*argumentos) is False
        servidor.sendmail.assert_not_called()

    def test_returns_false_when_the_connection_cannot_be_opened(
        self, smtp, funcion, argumentos, asunto, dato_clave
    ):
        _, clase = smtp
        clase.side_effect = ConnectionRefusedError("sin red")

        assert getattr(mail, funcion)(*argumentos) is False

    def test_returns_false_when_sending_fails(self, smtp, funcion, argumentos, asunto, dato_clave):
        servidor, _ = smtp
        servidor.sendmail.side_effect = RuntimeError("buzón lleno")

        assert getattr(mail, funcion)(*argumentos) is False


class TestInvitationEmail:
    def test_names_the_project_in_the_subject_or_body(self, smtp):
        servidor, _ = smtp

        mail.send_invitation_email("ana@x.co", "Mi serie", "Temporal123")

        _, _, mensaje = _mensaje_enviado(servidor)
        assert "Mi serie" in mensaje["Subject"] + _html(mensaje)


class TestContactEmail:
    DATOS = dict(
        nombre="Ana Ruiz",
        email="ana@x.co",
        celular="3001112233",
        empresa="Productora Sur",
        tipo="demo",
        mensaje="Quiero ver una demo",
    )

    def test_sends_the_form_to_the_support_address(self, smtp):
        servidor, _ = smtp

        resultado = mail.send_contact_email(**self.DATOS)

        assert resultado is True
        _, destinatario, mensaje = _mensaje_enviado(servidor)
        assert destinatario == "soporte@foccus.test"
        html = _html(mensaje)
        for dato in ("Ana Ruiz", "ana@x.co", "3001112233", "Productora Sur", "Quiero ver una demo"):
            assert dato in html

    def test_returns_false_when_the_smtp_server_fails(self, smtp):
        servidor, _ = smtp
        servidor.starttls.side_effect = RuntimeError("TLS no disponible")

        assert mail.send_contact_email(**self.DATOS) is False

    @pytest.mark.xfail(
        strict=True,
        reason="H-B24: los campos del visitante se insertan sin escapar en el HTML del correo de soporte",
    )
    def test_keeps_html_out_of_the_message_when_the_visitor_writes_markup(self, smtp):
        servidor, _ = smtp

        mail.send_contact_email(**{**self.DATOS, "mensaje": "<script>alert(1)</script>"})

        _, _, mensaje = _mensaje_enviado(servidor)
        assert "<script>" not in _html(mensaje)
