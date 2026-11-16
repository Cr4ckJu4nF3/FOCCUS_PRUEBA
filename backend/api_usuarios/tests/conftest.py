"""Fixtures compartidas de la suite del backend.

Decisión de aislamiento (semanas 2 a 5): `app/config/database.py` crea el motor
de MySQL y `app/main.py` ejecuta `create_all` al importarse. Para que ningún
test toque la BD de desarrollo (ni Railway), este archivo:

1. fija variables de entorno de prueba ANTES de importar la app
   (`load_dotenv()` no pisa variables que ya existen),
2. reemplaza el motor por SQLite en memoria,
3. crea y destruye las tablas en cada test (aislamiento FIRST).

Las diferencias entre SQLite y MySQL se verifican en `tests/integration`
(semana 6) contra una BD real.
"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
# La app usa rutas relativas ("app/assets/uploads"): se ejecuta siempre desde aquí.
os.chdir(BACKEND_DIR)

os.environ.update(
    DB_HOST="127.0.0.1",
    DB_PORT="3306",
    DB_USER="test",
    DB_PASSWORD="test",
    DB_NAME="foccus_test",
    MAIL_USER="no-reply@foccus.test",
    MAIL_PASSWORD="not-a-real-password",
    CONTACT_EMAIL="soporte@foccus.test",
    JWT_SECRET_KEY="clave-solo-para-tests-de-al-menos-32-bytes",
    JWT_EXPIRE_MINUTES="60",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.dialects.mysql import LONGTEXT  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.config.database as database  # noqa: E402


@compiles(LONGTEXT, "sqlite")
def _longtext_en_sqlite(element, compiler, **kw):
    # guion_version.contenido usa LONGTEXT de MySQL; SQLite lo llama TEXT.
    return "TEXT"


_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_test_engine, "connect")
def _enforce_foreign_keys(dbapi_connection, _record):
    # MySQL hace cumplir las claves foráneas; SQLite no, salvo que se le pida.
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


database.engine = _test_engine
database.SessionLocal.configure(bind=_test_engine)

from app.main import app  # noqa: E402  (importa después de aislar la BD)
from app.utils.auth import create_access_token  # noqa: E402

ADMIN_ROLE = 1001
MEMBER_ROLE = 1005


@pytest.fixture(autouse=True)
def fresh_database():
    """Esquema limpio en cada test: ningún test depende del anterior."""
    # guion <-> guion_version se referencian en círculo: se recrea con FK apagadas
    raw = _test_engine.raw_connection()
    raw.execute("PRAGMA foreign_keys=OFF")
    raw.close()
    database.Base.metadata.drop_all(bind=_test_engine)
    database.Base.metadata.create_all(bind=_test_engine)
    raw = _test_engine.raw_connection()
    raw.execute("PRAGMA foreign_keys=ON")
    raw.close()
    yield


@pytest.fixture(autouse=True)
def clear_in_memory_codes():
    """Los códigos 2FA y de recuperación viven en dicts de módulo: se limpian."""
    from app.controllers import user_controller

    for store in (
        user_controller.recovery_codes,
        user_controller.two_factor_codes,
        user_controller.verified_devices,
    ):
        store.clear()
    yield


@pytest.fixture(autouse=True)
def no_real_emails(mocker):
    """Ningún test envía correos reales: el mailer se reemplaza por un stub."""
    stubs = {
        name: mocker.patch(f"app.controllers.user_controller.{name}", return_value=True)
        for name in ("send_recovery_email", "send_2fa_email", "send_invitation_email")
    }
    stubs["send_contact_email"] = mocker.patch(
        "app.controllers.contact_controller.send_contact_email", return_value=True
    )
    return stubs


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    """Los archivos subidos en tests van a una carpeta temporal, no a app/assets."""
    from app.utils import file_storage

    monkeypatch.setattr(file_storage, "BASE_UPLOAD_DIR", str(tmp_path / "uploads"))
    return tmp_path / "uploads"


@pytest.fixture
def db():
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def client_500():
    """Como `client`, pero un error no controlado se devuelve como HTTP 500
    (lo que vería el frontend) en vez de relanzarse dentro del test."""
    return TestClient(app, raise_server_exceptions=False)


def auth_headers(user=None, *, id_user=None, id_rol=None):
    """Encabezado Authorization para un usuario (fila de BD) o para ids explícitos."""
    if user is not None:
        id_user, id_rol = user.id_user, user.id_rol
    token = create_access_token({"id_user": id_user, "id_rol": id_rol})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_user(db):
    from tests.factories import make_user

    return make_user(db, mail="admin@foccus.test", id_rol=ADMIN_ROLE, id_identificacion="ADM-1")


@pytest.fixture
def member_user(db):
    from tests.factories import make_user

    return make_user(db, mail="miembro@foccus.test", id_rol=MEMBER_ROLE, id_identificacion="MEM-1")


@pytest.fixture
def admin_headers(admin_user):
    return auth_headers(admin_user)


@pytest.fixture
def member_headers(member_user):
    return auth_headers(member_user)
