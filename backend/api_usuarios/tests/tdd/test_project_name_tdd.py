"""Historia TDD (semana 10): validar el nombre del proyecto. Ver docs/testing/tdd-nombre-de-proyecto.md."""
import pytest

from tests.factories import make_client, make_project

pytestmark = pytest.mark.tdd

LARGO = "x" * 46


def payload(id_client, **extra):
    datos = dict(project_name="La serie", formato_de_produccion="Serie", genero="Drama", id_client=id_client)
    datos.update(extra)
    return datos


def assert_rejects_name_with_422(response):
    assert response.status_code == 422
    assert "project_name" in str(response.json()["detail"])


# ── Ciclo 1 ──
def test_creating_a_project_with_a_46_character_name_is_rejected_with_422(client, db, admin_headers):
    empresa = make_client(db)

    response = client.post("/projects", json=payload(empresa.id_cliente, project_name=LARGO), headers=admin_headers)

    assert_rejects_name_with_422(response)
