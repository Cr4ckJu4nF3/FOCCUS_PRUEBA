"""Infraestructura de las pruebas de integración (semana 6): MySQL/MariaDB REAL.

Se activan con la variable de entorno TEST_DATABASE_URL, por ejemplo:

    TEST_DATABASE_URL="mysql+pymysql://foccus_test:foccus_test@127.0.0.1:3306/foccus_test" pytest tests/integration

Sin la variable, todo este directorio se SALTA (no falla), para que `pytest` siga
funcionando en un equipo sin base de datos.

Seguridad: estas pruebas BORRAN el contenido de todas las tablas. Por eso se
niegan a correr si el nombre de la base de datos no contiene "test".
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app.config.database as database
from app.main import app


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/integration" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def mysql_engine():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL no está definida: pruebas de integración omitidas")
    if "test" not in (make_url(url).database or "").lower():
        pytest.fail(
            f"TEST_DATABASE_URL apunta a '{make_url(url).database}': el nombre debe contener 'test' "
            "porque estas pruebas vacían las tablas."
        )
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        # drop_all() no puede ordenar guion <-> guion_version (FK sin nombre en un ciclo)
        for tabla in database.Base.metadata.tables.values():
            conn.execute(text(f"DROP TABLE IF EXISTS `{tabla.name}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    # create_all sí resuelve el ciclo con ALTER TABLE, igual que al arrancar main.py
    database.Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_mysql(mysql_engine):
    """Cada test arranca con todas las tablas vacías (aislamiento FIRST)."""
    with mysql_engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for tabla in database.Base.metadata.tables.values():
            conn.execute(text(f"TRUNCATE TABLE `{tabla.name}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    yield


@pytest.fixture
def db(mysql_engine):
    """Sesión sobre MySQL (sustituye a la de SQLite: las fábricas de tests/factories la usan igual)."""
    session = sessionmaker(bind=mysql_engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(mysql_engine):
    factory = sessionmaker(bind=mysql_engine, autoflush=False)

    def _get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[database.get_db] = _get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_500(mysql_engine, client):
    return TestClient(app, raise_server_exceptions=False)
