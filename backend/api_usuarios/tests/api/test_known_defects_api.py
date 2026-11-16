"""Defectos conocidos de la API, documentados como pruebas.

Cada test afirma el comportamiento CORRECTO y está marcado `xfail(strict=True)`:
  * hoy la suite sigue en verde (el test "falla como se esperaba"),
  * el día que alguien corrija el defecto el test pasa, `strict` lo convierte en
    error y obliga a quitar la marca (el defecto queda cerrado con evidencia).

El detalle de cada uno (impacto, propuesta de arreglo) está en docs/testing/hallazgos.md.
"""
import pytest

from tests.factories import (
    DEFAULT_PASSWORD,
    link_user,
    make_client,
    make_escena,
    make_guion,
    make_project,
    make_user,
)

pytestmark = pytest.mark.api


def defect(codigo, razon):
    return pytest.mark.xfail(strict=True, reason=f"{codigo}: {razon}")


REGISTRO = dict(
    razon_social="Productora Sur",
    representante_legal="Laura",
    email_empresa="contacto@sur.co",
    telephone="6010000",
    document="NIT",
    id_document="900123",
    nombre="Camila",
    apellido="Prueba",
    mail="camila@sur.co",
    msisdn="3001112233",
    contrasena=DEFAULT_PASSWORD,
)


# ───────────── Seguridad: autenticación y autorización ─────────────


@defect("H-B01", "el token de /users/login ya da acceso total sin completar el 2FA")
def test_login_token_should_not_open_protected_routes_before_the_2fa_is_verified(client, db):
    usuario = make_user(db, mail="ana@foccus.test")
    token = client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": DEFAULT_PASSWORD}).json()[
        "data"
    ]["access_token"]

    response = client.get(f"/users/{usuario.id_user}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code in (401, 403)


@defect("H-B02", "cualquier usuario con sesión puede cambiar su propio rol (PATCH /users/{id})")
def test_a_regular_user_should_not_be_able_to_make_themselves_administrator(client, db, member_user, member_headers):
    client.patch(f"/users/{member_user.id_user}", json={"id_rol": 1001}, headers=member_headers)

    db.refresh(member_user)
    assert member_user.id_rol != 1001


@defect("H-B03", "PUT/PATCH /users/{id} no exige ser administrador ni ser el propio usuario")
def test_a_regular_user_should_not_be_able_to_edit_another_user(client, db, admin_user, member_headers):
    client.patch(f"/users/{admin_user.id_user}", json={"mail": "robada@evil.test"}, headers=member_headers)

    db.refresh(admin_user)
    assert admin_user.mail == "admin@foccus.test"


@defect("H-B04", "/users/invite no exige ser administrador y acepta id_rol 1001 del cuerpo")
def test_a_regular_user_should_not_be_able_to_invite_someone_as_administrator(
    client, db, member_headers
):
    proyecto = make_project(db)

    client.post(
        "/users/invite",
        json={
            "correos": ["intruso@evil.test"],
            "id_project": proyecto.id_project,
            "id_client": proyecto.id_client,
            "id_rol": 1001,
        },
        headers=member_headers,
    )

    from app.models.user_model import User

    intruso = db.query(User).filter(User.mail == "intruso@evil.test").first()
    assert intruso is None or intruso.id_rol != 1001


@defect("H-B05", "POST /projects/create toma id_user del cuerpo y lo vincula como administrador")
def test_creating_a_project_should_not_link_a_different_user_than_the_caller(
    client, db, admin_user, member_user, member_headers
):
    empresa = make_client(db)

    client.post(
        "/projects/create",
        json={
            "project_name": "P",
            "formato_de_produccion": "Serie",
            "genero": "Drama",
            "id_client": empresa.id_cliente,
            "id_user": admin_user.id_user,  # el que llama es member_user
        },
        headers=member_headers,
    )

    from app.models.user_project_model import UserProject

    assert db.query(UserProject).filter_by(id_user=admin_user.id_user).count() == 0


@defect("H-B06", "no hay aislamiento entre empresas: se puede leer a un usuario de otra empresa")
def test_a_user_should_not_read_the_profile_of_a_user_from_another_company(client, db, member_headers):
    otra_empresa = make_client(db)
    ajeno = make_user(db, mail="ajeno@otra.test", id_client=otra_empresa.id_cliente)

    body = client.get(f"/users/{ajeno.id_user}", headers=member_headers).json()

    assert body["success"] is False


@defect("H-B07", "no hay aislamiento entre empresas: se puede leer un proyecto ajeno")
def test_a_user_should_not_read_a_project_of_another_company(client, db, member_user, member_headers):
    mi_empresa = make_client(db)
    otra_empresa = make_client(db)
    db.query(type(member_user)).filter_by(id_user=member_user.id_user).update({"id_client": mi_empresa.id_cliente})
    db.commit()
    ajeno = make_project(db, id_client=otra_empresa.id_cliente)

    body = client.get(f"/projects/{ajeno.id_project}", headers=member_headers).json()

    assert body["success"] is False


# ───────────── Fuga de información y manejo de errores ─────────────


@defect("H-B08", "/register devuelve la sentencia SQL (con el hash de la contraseña) en el campo error")
def test_a_failed_registration_should_not_leak_sql_or_the_password_hash(client, db):
    # Mismo documento que otro usuario: el chequeo previo no lo detecta y el INSERT falla
    make_user(db, mail="otro@sur.co", id_identificacion="111")
    cuerpo = {**REGISTRO, "email_empresa": "otra@sur.co", "id_document": "111"}

    response = client.post("/register", json=cuerpo)

    assert "INSERT INTO" not in response.text
    assert "$2b$" not in response.text


@defect("H-B09", "telephone es opcional en el schema y el formulario pero NOT NULL en la tabla clients")
def test_registration_should_succeed_when_the_optional_company_phone_is_omitted(client):
    cuerpo = {k: v for k, v in REGISTRO.items() if k != "telephone"}

    assert client.post("/register", json=cuerpo).json()["success"] is True


@defect("H-B10", "el chequeo de empresa duplicada no normaliza el correo antes de buscar")
def test_a_company_email_that_differs_only_in_case_should_be_reported_as_duplicate(client):
    client.post("/register", json=REGISTRO)
    repetido = {**REGISTRO, "email_empresa": "CONTACTO@sur.co", "mail": "otra@persona.co", "id_document": "555"}

    body = client.post("/register", json=repetido).json()

    assert body["error"] == "DUPLICATE_CLIENT"


@defect("H-B11", "POST /users compara el correo sin normalizar y el INSERT revienta con 500")
def test_creating_a_user_with_an_untrimmed_duplicate_email_should_not_crash(client_500, db, admin_headers):
    make_user(db, mail="juan@foccus.test")
    cuerpo = dict(
        nombre="Juan", apellido="P", identificacion="CC", id_identificacion="X1",
        mail="  JUAN@foccus.test ", msisdn="1", direccion="d", fecha_de_nacimiento="1990-01-01T00:00:00",
        estado="activo", contrasena=DEFAULT_PASSWORD, id_departamento="A", id_project="p", id_rol=1005,
    )

    response = client_500.post("/users", json=cuerpo, headers=admin_headers)

    assert response.status_code != 500


@defect("H-B12", "telephone opcional en ClientSchema pero NOT NULL en la tabla: POST /clients sin teléfono da 500")
def test_creating_a_client_without_a_phone_should_not_crash(client_500, admin_headers):
    cuerpo = dict(
        document="NIT", razon_social="X", representante_legal="Y", email="x@y.co", id_document="1"
    )

    assert client_500.post("/clients", json=cuerpo, headers=admin_headers).status_code != 500


@defect("H-B13", "verify_2fa_code asume que el usuario aún existe y falla con AttributeError (500)")
def test_verifying_a_2fa_code_for_a_user_deleted_in_the_meantime_should_not_crash(client_500, db):
    from app.controllers import user_controller

    usuario = make_user(db, mail="ana@foccus.test")
    client_500.post("/users/2fa/send", json={"mail": "ana@foccus.test", "device_id": "d"})
    codigo = user_controller.two_factor_codes["ana@foccus.test"]["codigo"]
    db.delete(usuario)
    db.commit()

    response = client_500.post(
        "/users/2fa/verify", json={"mail": "ana@foccus.test", "codigo": codigo, "device_id": "d"}
    )

    assert response.status_code != 500


@defect("H-B14", "crear un guion no valida que el proyecto exista: la FK revienta con 500")
def test_creating_a_script_for_a_missing_project_should_report_it_instead_of_crashing(client_500, admin_headers):
    response = client_500.post(
        "/guiones", json={"nombre": "Piloto", "id_project": "no-existe"}, headers=admin_headers
    )

    assert response.status_code != 500


@defect("H-B15", "el plan de rodaje con fecha inválida crea un día con fecha_inicio NULL (NOT NULL) y da 500")
def test_importing_a_shooting_plan_with_an_impossible_date_should_not_crash(
    client_500, db, mocker, admin_headers
):
    proyecto = make_project(db)
    mocker.patch(
        "app.controllers.rodaje_controller.extraer_texto_pdf",
        return_value="DÍA 1 · Lunes, 31 de febrero 2026 · Bogotá · Llamado: 06:00 ·\nSc. 1 INT SALA Día 1 págs.",
    )

    response = client_500.post(
        f"/projects/{proyecto.id_project}/rodajes/importar",
        files={"archivo": ("plan.pdf", b"%PDF", "application/pdf")},
        headers=admin_headers,
    )

    assert response.status_code != 500


# ───────────── Lógica de negocio ─────────────


@defect("H-B16", "numero_de_escena es texto: el orden alfabético pone la 10 antes que la 2")
def test_scenes_should_be_listed_in_numeric_order(client, db, member_headers):
    guion = make_guion(db, make_project(db))
    for numero in ("1", "2", "10"):
        make_escena(db, guion, numero=numero)

    body = client.get(f"/guiones/{guion.id_guion}/escenas", headers=member_headers).json()

    assert [e["numero_de_escena"] for e in body["data"]] == ["1", "2", "10"]


@defect("H-B17", "el siguiente id de proyecto se calcula con orden alfabético y se rompe pasado proj9999")
def test_project_id_generation_should_keep_growing_past_four_digits(client, db, admin_headers):
    empresa = make_client(db)
    make_project(db, id_client=empresa.id_cliente, id_project="proj9999")
    make_project(db, id_client=empresa.id_cliente, id_project="proj10000")

    body = client.post(
        "/projects",
        json={"project_name": "P", "formato_de_produccion": "S", "genero": "D", "id_client": empresa.id_cliente},
        headers=admin_headers,
    ).json()

    assert body["data"]["id_project"] == "proj10001"
