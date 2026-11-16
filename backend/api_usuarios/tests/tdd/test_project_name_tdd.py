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


# ── Ciclo 2 ──
def test_create_and_link_with_a_46_character_name_is_rejected_with_422(client, db, member_user, member_headers):
    empresa = make_client(db)

    response = client.post(
        "/projects/create",
        json=payload(empresa.id_cliente, project_name=LARGO, id_user=member_user.id_user),
        headers=member_headers,
    )

    assert_rejects_name_with_422(response)


# ── Ciclo 3 ──
@pytest.mark.parametrize("metodo", ["patch", "put"])
def test_editing_a_project_with_a_46_character_name_is_rejected_with_422(client, db, member_headers, metodo):
    proyecto = make_project(db)
    cuerpo = {"project_name": LARGO}
    if metodo == "put":
        cuerpo = payload(proyecto.id_client, id_project=proyecto.id_project, project_name=LARGO)

    response = getattr(client, metodo)(f"/projects/{proyecto.id_project}", json=cuerpo, headers=member_headers)

    assert_rejects_name_with_422(response)
