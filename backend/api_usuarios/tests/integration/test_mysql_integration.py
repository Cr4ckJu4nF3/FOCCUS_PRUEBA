"""Pruebas de integración: la API completa contra MySQL/MariaDB REAL.

Cubren lo que SQLite (la BD de las pruebas de API) no puede revelar:
collation, límites de longitud en modo estricto, claves foráneas con ON DELETE,
tipos de columna (LONGTEXT), transacciones y persistencia real entre sesiones.

Ejecutar:
    TEST_DATABASE_URL="mysql+pymysql://usuario:clave@127.0.0.1:3306/foccus_test" pytest tests/integration
"""
import pytest
from sqlalchemy import inspect, text

from app.models.client_model import Client
from app.models.escena_model import Escena
from app.models.guion_version_model import GuionVersion
from app.models.project_model import Project
from app.models.user_model import User
from tests.conftest import auth_headers
from tests.factories import (
    DEFAULT_PASSWORD,
    link_user,
    make_client,
    make_escena,
    make_guion,
    make_guion_version,
    make_personaje,
    make_project,
    make_requerimiento,
    make_rodaje,
    make_user,
)

pytestmark = pytest.mark.integration


def contar(db, tabla):
    """Cuenta filas en una transacción nueva (REPEATABLE READ: una sesión con transacción abierta ve una foto vieja)."""
    db.commit()
    return db.execute(text(f"SELECT COUNT(*) FROM `{tabla}`")).scalar()


@pytest.fixture
def admin(db):
    return make_user(db, mail="admin@foccus.test", id_rol=1001, id_identificacion="ADM-1")


@pytest.fixture
def admin_headers(admin):
    return auth_headers(admin)


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


class TestSchema:
    def test_every_model_table_exists_in_the_real_database(self, mysql_engine):
        from app.config.database import Base

        existentes = set(inspect(mysql_engine).get_table_names())

        assert set(Base.metadata.tables) <= existentes

    def test_the_circular_reference_between_script_and_version_is_created(self, mysql_engine):
        fks = {
            tabla: {fk["referred_table"] for fk in inspect(mysql_engine).get_foreign_keys(tabla)}
            for tabla in ("guion", "guion_version")
        }

        assert "guion_version" in fks["guion"]
        assert "guion" in fks["guion_version"]

    @pytest.mark.parametrize(
        "tabla, columna",
        [("users", "mail"), ("users", "id_identificacion"), ("clients", "email")],
    )
    def test_uniqueness_is_enforced_by_the_database(self, mysql_engine, tabla, columna):
        unicos = inspect(mysql_engine).get_unique_constraints(tabla)
        indices = inspect(mysql_engine).get_indexes(tabla)
        columnas_unicas = {c for u in unicos for c in u["column_names"]} | {
            c for i in indices if i.get("unique") for c in i["column_names"]
        }

        assert columna in columnas_unicas


class TestPersistenceAcrossSessions:
    def test_a_registration_made_through_the_api_is_visible_from_another_session(self, client, db):
        client.post("/register", json=REGISTRO)

        db.commit()
        usuario = db.query(User).filter(User.mail == "camila@sur.co").one()
        empresa = db.query(Client).filter(Client.email == "contacto@sur.co").one()
        assert usuario.id_client == empresa.id_cliente
        assert usuario.id_rol == 1001

    def test_the_stored_password_is_a_bcrypt_hash_and_the_login_works_against_the_real_database(self, client, db):
        client.post("/register", json=REGISTRO)

        db.commit()
        almacenada = db.query(User).filter(User.mail == "camila@sur.co").one().contrasena
        login = client.post("/users/login", json={"mail": "camila@sur.co", "contrasena": DEFAULT_PASSWORD}).json()
        assert almacenada.startswith("$2b$") and almacenada != DEFAULT_PASSWORD
        assert login["success"] is True

    def test_login_stamps_the_last_access_with_the_database_clock(self, client, db):
        usuario = make_user(db, mail="ana@foccus.test", ultimo_acceso=None)

        client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": DEFAULT_PASSWORD})

        db.commit()
        db.refresh(usuario)
        assert usuario.ultimo_acceso is not None


class TestCollation:
    """MySQL compara texto sin distinguir mayúsculas (utf8mb4_general_ci); SQLite sí las distingue.

    Por eso H-B10 y los correos sin normalizar pasan desapercibidos en producción con
    MySQL, pero fallan en las pruebas de API con SQLite.
    """

    def test_a_company_email_that_differs_only_in_case_is_reported_as_duplicate(self, client):
        client.post("/register", json=REGISTRO)

        body = client.post(
            "/register",
            json={**REGISTRO, "email_empresa": "CONTACTO@Sur.co", "mail": "otra@persona.co", "id_document": "555"},
        ).json()

        assert body["error"] == "DUPLICATE_CLIENT"

    def test_a_user_email_that_differs_only_in_case_is_reported_as_duplicate(self, client):
        client.post("/register", json=REGISTRO)

        body = client.post(
            "/register",
            json={**REGISTRO, "email_empresa": "otra@empresa.co", "mail": "CAMILA@sur.co", "id_document": "777"},
        ).json()

        assert body["error"] == "DUPLICATE_USER"

    def test_two_factor_and_recovery_find_the_user_whatever_the_email_case(self, client, db):
        make_user(db, mail="ana@foccus.test")

        envio = client.post("/users/2fa/send", json={"mail": "ANA@Foccus.test", "device_id": "d"}).json()
        recuperacion = client.post("/users/recover-password", json={"mail": "ANA@Foccus.test"}).json()

        assert envio["success"] is True
        assert recuperacion["success"] is True


class TestUnicodeAndLargeContent:
    def test_accents_enie_and_emoji_survive_a_round_trip(self, client, db, admin_headers):
        empresa = make_client(db)
        nombre = "Niño y el ñandú 🎬 — ¿qué pasó?"

        creado = client.post(
            "/projects",
            json=dict(project_name=nombre, formato_de_produccion="Serie", genero="Drama", id_client=empresa.id_cliente),
            headers=admin_headers,
        ).json()

        leido = client.get(f"/projects/{creado['data']['id_project']}", headers=admin_headers).json()
        assert leido["data"]["project_name"] == nombre

    def test_a_script_larger_than_a_text_column_is_stored_whole(self, client, db, admin_headers):
        # TEXT de MySQL admite 64 KB; el guion usa LONGTEXT. 300 000 caracteres lo comprueban.
        proyecto = make_project(db)
        contenido = "INT. SALA - NOCHE\nJulia espera.\n" * 10_000

        creado = client.post(
            "/guiones/texto",
            json={
                "nombre": "Largo",
                "id_project": proyecto.id_project,
                "contenido": contenido,
                "fecha_de_emision": "2026-01-05",
            },
            headers=admin_headers,
        ).json()

        db.commit()
        guardado = db.get(GuionVersion, creado["data"]["id_guion_version"]).contenido
        assert len(contenido) > 300_000
        assert guardado == contenido


class TestForeignKeys:
    @pytest.fixture
    def proyecto_completo(self, db, admin):
        empresa = make_client(db)
        proyecto = make_project(db, id_client=empresa.id_cliente)
        guion = make_guion(db, proyecto)
        make_guion_version(db, guion, admin)
        escena = make_escena(db, guion, numero="1")
        make_requerimiento(db, escena)
        miembro = make_user(db, id_identificacion="MIEMBRO")
        link_user(db, miembro, proyecto)
        make_rodaje(db, proyecto)
        make_personaje(db, proyecto)
        return proyecto

    def test_deleting_a_project_removes_its_scripts_versions_scenes_members_days_and_characters(
        self, client, db, admin_headers, proyecto_completo
    ):
        client.delete(f"/projects/{proyecto_completo.id_project}", headers=admin_headers)

        for tabla in ("projects", "guion", "guion_version", "escenas", "user_projects", "rodaje", "personajes"):
            assert contar(db, tabla) == 0, tabla

    def test_deleting_a_project_keeps_the_users_who_were_members(self, client, db, admin_headers, proyecto_completo):
        client.delete(f"/projects/{proyecto_completo.id_project}", headers=admin_headers)

        assert db.query(User).filter(User.id_identificacion == "MIEMBRO").count() == 1

    def test_deleting_a_user_removes_their_memberships(self, client, db, admin_headers, proyecto_completo):
        miembro = db.query(User).filter(User.id_identificacion == "MIEMBRO").one()

        client.delete(f"/users/{miembro.id_user}", headers=admin_headers)

        assert contar(db, "user_projects") == 0
        assert contar(db, "projects") == 1

    def test_deleting_the_author_of_a_version_keeps_the_version_without_an_author(
        self, client, db, admin, admin_headers
    ):
        guion = make_guion(db, make_project(db))
        version = make_guion_version(db, guion, admin)
        otro_admin = make_user(db, mail="otro@foccus.test", id_rol=1001, id_identificacion="ADM-2")

        client.delete(f"/users/{admin.id_user}", headers=auth_headers(otro_admin))

        db.commit()
        db.refresh(version)
        assert version.creado_por is None

    def test_deleting_a_script_removes_its_scenes(self, client, db, admin, admin_headers):
        guion = make_guion(db, make_project(db))
        make_guion_version(db, guion, admin)
        make_escena(db, guion)

        client.delete(f"/guiones/{guion.id_guion}", headers=admin_headers)

        assert contar(db, "guion") == 0
        assert db.query(Escena).count() == 0

    def test_a_scene_cannot_point_to_a_script_that_does_not_exist(self, client_500, admin_headers):
        response = client_500.post(
            "/escenas", json={"numero_de_escena": "1", "encabezado": "X", "id_guion": 9999}, headers=admin_headers
        )

        # la API lo valida antes de llegar a la FK: respuesta controlada, no 500
        assert response.status_code == 200
        assert response.json()["error"] == "GUION_NOT_FOUND"

    @pytest.mark.xfail(
        strict=True,
        reason="H-B26: escenas.id_desglose tiene ON DELETE CASCADE en sentido inverso; "
        "borrar la escena deja huérfanos el desglose y sus requerimientos",
    )
    def test_deleting_a_scene_should_not_leave_its_breakdown_behind(self, client, db, admin, admin_headers):
        guion = make_guion(db, make_project(db))
        escena = make_escena(db, guion)
        make_requerimiento(db, escena)

        client.delete(f"/escenas/{escena.id_escena}", headers=admin_headers)

        assert contar(db, "desglose") == 0
        assert contar(db, "desglose_requerimientos") == 0


class TestTransactions:
    def test_a_failed_registration_leaves_no_orphan_company(self, client, db):
        make_user(db, mail="otro@sur.co", id_identificacion="900123")  # mismo documento: el INSERT del usuario falla
        antes = contar(db, "clients")

        body = client.post("/register", json=REGISTRO).json()

        assert body["success"] is False
        assert contar(db, "clients") == antes

    def test_inviting_several_people_commits_them_together(self, client, db, admin_headers):
        proyecto = make_project(db)

        client.post(
            "/users/invite",
            json={
                "correos": ["a@x.co", "b@x.co", "c@x.co"],
                "id_project": proyecto.id_project,
                "id_client": proyecto.id_client,
                "id_rol": 1005,
            },
            headers=admin_headers,
        )

        assert contar(db, "user_projects") == 3
        assert db.query(User).filter(User.estado == "pendiente").count() == 3


class TestOrdering:
    def test_the_breakdown_lists_scenes_without_a_dramatic_day_last_on_mysql(
        self, client, db, admin_headers
    ):
        """Regresión del arreglo «NULLS LAST no es compatible con MariaDB» (CASE WHEN)."""
        guion = make_guion(db, make_project(db))
        make_escena(db, guion, numero="1", dia_dramatico=None)
        make_escena(db, guion, numero="2", dia_dramatico=3)
        make_escena(db, guion, numero="3", dia_dramatico=1)

        body = client.get(f"/guiones/{guion.id_guion}/desglose", headers=admin_headers).json()

        assert [e["numero_de_escena"] for e in body["data"]] == ["3", "2", "1"]


class TestColumnLimits:
    """MySQL en modo estricto rechaza texto más largo que la columna (SQLite lo acepta sin quejarse).

    Hoy la API no valida longitudes y el cliente recibe un 500. El frontend tampoco limita
    lo que se escribe (solo el código 2FA tiene maxLength).
    """

    def test_a_project_name_of_exactly_45_characters_is_accepted(self, client, db, admin_headers):
        empresa = make_client(db)

        body = client.post(
            "/projects",
            json=dict(project_name="x" * 45, formato_de_produccion="S", genero="D", id_client=empresa.id_cliente),
            headers=admin_headers,
        ).json()

        assert body["success"] is True

    def test_a_project_name_of_46_characters_is_rejected_with_422_instead_of_a_500(self, client_500, db, admin_headers):
        empresa = make_client(db)

        response = client_500.post(
            "/projects",
            json=dict(project_name="x" * 46, formato_de_produccion="S", genero="D", id_client=empresa.id_cliente),
            headers=admin_headers,
        )

        assert response.status_code == 422

    @pytest.mark.xfail(
        strict=True,
        reason="H-B25: la API no valida longitudes; MySQL estricto rechaza el INSERT y el cliente recibe 500",
    )
    @pytest.mark.parametrize(
        "ruta, cuerpo",
        [
            (
                "/clients",
                dict(document="NIT", razon_social="x" * 51, representante_legal="Y", email="q@y.co",
                     id_document="1", telephone="1"),
            ),
            (
                "/roles",
                dict(nombre="x" * 51, nivel_jerarquia="1"),
            ),
        ],
        ids=["razon_social-51", "rol-nombre-51"],
    )
    def test_a_value_longer_than_its_column_should_be_rejected_with_a_validation_error(
        self, client_500, admin_headers, ruta, cuerpo
    ):
        response = client_500.post(ruta, json=cuerpo, headers=admin_headers)

        assert response.status_code in (200, 422)
