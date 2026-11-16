"""Proyectos, clientes (empresas) y roles."""
import pytest

from app.models.project_model import Project
from app.models.user_project_model import UserProject
from tests.factories import make_client, make_project, make_role

pytestmark = pytest.mark.api


def proyecto_payload(id_client, **extra):
    datos = dict(
        project_name="La serie",
        formato_de_produccion="Serie",
        genero="Drama",
        sinopsis="Algo pasa",
        director="Dir",
        id_client=id_client,
    )
    datos.update(extra)
    return datos


class TestProjects:
    def test_creates_a_project_and_generates_a_sequential_id_when_none_is_given(self, client, db, admin_headers):
        empresa = make_client(db)

        primero = client.post("/projects", json=proyecto_payload(empresa.id_cliente), headers=admin_headers).json()
        segundo = client.post("/projects", json=proyecto_payload(empresa.id_cliente), headers=admin_headers).json()

        assert primero["data"]["id_project"] == "proj0001"
        assert segundo["data"]["id_project"] == "proj0002"

    def test_respects_an_explicit_project_id(self, client, db, admin_headers):
        empresa = make_client(db)

        body = client.post(
            "/projects", json=proyecto_payload(empresa.id_cliente, id_project="mi-proyecto"), headers=admin_headers
        ).json()

        assert body["data"]["id_project"] == "mi-proyecto"

    def test_rejects_a_project_id_that_already_exists(self, client, db, admin_headers):
        existente = make_project(db)

        body = client.post(
            "/projects",
            json=proyecto_payload(existente.id_client, id_project=existente.id_project),
            headers=admin_headers,
        ).json()

        assert body["error"] == "DUPLICATE_PROJECT"

    def test_returns_422_when_the_name_is_missing(self, client, admin_headers):
        assert client.post("/projects", json={"genero": "x"}, headers=admin_headers).status_code == 422

    def test_create_and_link_makes_the_user_administrator_of_the_new_project(
        self, client, db, member_user, member_headers
    ):
        empresa = make_client(db)

        body = client.post(
            "/projects/create",
            json=proyecto_payload(empresa.id_cliente, id_user=member_user.id_user),
            headers=member_headers,
        ).json()

        assert body["success"] is True
        vinculo = db.query(UserProject).filter_by(id_user=member_user.id_user).one()
        assert vinculo.id_project == body["data"]["id_project"]
        assert vinculo.id_rol == 1001

    def test_gets_a_project_by_id(self, client, db, member_headers):
        proyecto = make_project(db, project_name="Mi serie")

        body = client.get(f"/projects/{proyecto.id_project}", headers=member_headers).json()

        assert body["data"]["project_name"] == "Mi serie"

    def test_reports_a_project_that_does_not_exist(self, client, member_headers):
        assert client.get("/projects/nada", headers=member_headers).json()["message"] == "Proyecto no encontrado"

    def test_admin_lists_all_projects(self, client, db, admin_headers):
        make_project(db)
        make_project(db)

        assert len(client.get("/projects", headers=admin_headers).json()["data"]) == 2

    def test_lists_only_the_projects_of_the_requested_client(self, client, db, member_headers):
        empresa = make_client(db)
        propio = make_project(db, id_client=empresa.id_cliente)
        make_project(db)

        body = client.get(f"/projects/client/{empresa.id_cliente}", headers=member_headers).json()

        assert [p["id_project"] for p in body["data"]] == [propio.id_project]

    def test_patch_changes_only_the_fields_that_are_sent(self, client, db, member_headers):
        proyecto = make_project(db, project_name="Viejo", genero="Drama")

        client.patch(f"/projects/{proyecto.id_project}", json={"project_name": "Nuevo"}, headers=member_headers)

        db.refresh(proyecto)
        assert (proyecto.project_name, proyecto.genero) == ("Nuevo", "Drama")

    def test_put_replaces_the_project_data(self, client, db, member_headers):
        proyecto = make_project(db)

        body = client.put(
            f"/projects/{proyecto.id_project}",
            json=proyecto_payload(proyecto.id_client, id_project=proyecto.id_project, genero="Comedia"),
            headers=member_headers,
        ).json()

        assert body["success"] is True
        db.refresh(proyecto)
        assert proyecto.genero == "Comedia"

    @pytest.mark.parametrize("metodo", ["put", "patch"])
    def test_updating_a_missing_project_is_reported(self, client, member_headers, metodo):
        payload = {"project_name": "x", "formato_de_produccion": "x", "genero": "x", "id_client": 1}

        body = getattr(client, metodo)("/projects/nada", json=payload, headers=member_headers).json()

        assert body["message"] == "Proyecto no encontrado"

    @pytest.mark.parametrize("metodo, ruta", [("delete", "/projects/{id}"), ("post", "/projects/{id}/delete")])
    def test_admin_deletes_a_project_with_either_endpoint(self, client, db, admin_headers, metodo, ruta):
        proyecto = make_project(db)

        body = getattr(client, metodo)(ruta.format(id=proyecto.id_project), headers=admin_headers).json()

        assert body["success"] is True
        assert db.query(Project).count() == 0

    def test_deleting_a_missing_project_is_reported(self, client, admin_headers):
        assert client.delete("/projects/nada", headers=admin_headers).json()["message"] == "Proyecto no encontrado"


CLIENTE = dict(
    document="NIT",
    razon_social="Productora Sur",
    representante_legal="Laura",
    email="contacto@sur.co",
    address="Calle 1",
    telephone="6010000",
    number_cellphone="3000000000",
    id_document="900123",
)


class TestClients:
    def test_admin_creates_a_client(self, client, admin_headers):
        body = client.post("/clients", json=CLIENTE, headers=admin_headers).json()

        assert body["success"] is True
        assert body["data"]["email"] == "contacto@sur.co"

    def test_rejects_a_duplicate_email(self, client, db, admin_headers):
        make_client(db, email="contacto@sur.co")

        assert client.post("/clients", json=CLIENTE, headers=admin_headers).json()["error"] == "DUPLICATE_EMAIL"

    def test_lists_and_gets_clients_for_any_logged_user(self, client, db, member_headers):
        empresa = make_client(db, razon_social="Mi empresa")

        lista = client.get("/clients", headers=member_headers).json()["data"]
        uno = client.get(f"/clients/{empresa.id_cliente}", headers=member_headers).json()["data"]

        assert [c["razon_social"] for c in lista] == ["Mi empresa"]
        assert uno["razon_social"] == "Mi empresa"

    def test_reports_a_client_that_does_not_exist(self, client, member_headers):
        assert client.get("/clients/9999", headers=member_headers).json()["message"] == "Cliente no encontrado"

    def test_admin_patches_and_replaces_a_client(self, client, db, admin_headers):
        empresa = make_client(db, razon_social="Vieja")

        client.patch(f"/clients/{empresa.id_cliente}", json={"razon_social": "Nueva"}, headers=admin_headers)
        db.refresh(empresa)
        assert empresa.razon_social == "Nueva"

        client.put(
            f"/clients/{empresa.id_cliente}", json={**CLIENTE, "email": empresa.email}, headers=admin_headers
        )
        db.refresh(empresa)
        assert empresa.razon_social == "Productora Sur"

    @pytest.mark.parametrize("metodo", ["put", "patch", "delete"])
    def test_changing_a_missing_client_is_reported(self, client, admin_headers, metodo):
        kwargs = {} if metodo == "delete" else {"json": CLIENTE if metodo == "put" else {"razon_social": "x"}}

        body = getattr(client, metodo)("/clients/9999", headers=admin_headers, **kwargs).json()

        assert body["message"] == "Cliente no encontrado"

    def test_admin_deletes_a_client(self, client, db, admin_headers):
        empresa = make_client(db)

        assert client.delete(f"/clients/{empresa.id_cliente}", headers=admin_headers).json()["success"] is True


ROL = dict(nombre="Director de arte", nivel_jerarquia="2", descripcion="Lidera arte", activo=True)


class TestRoles:
    def test_admin_creates_a_role(self, client, admin_headers):
        body = client.post("/roles", json=ROL, headers=admin_headers).json()

        assert body["success"] is True
        assert body["data"]["nombre"] == "Director de arte"

    def test_rejects_a_duplicate_role_name(self, client, db, admin_headers):
        make_role(db, 2001, nombre="Director de arte")

        assert client.post("/roles", json=ROL, headers=admin_headers).json()["error"] == "DUPLICATE_ROLE"

    def test_lists_and_gets_roles_for_any_logged_user(self, client, db, member_headers):
        rol = make_role(db, 2001, nombre="Utilero")

        lista = client.get("/roles", headers=member_headers).json()["data"]
        uno = client.get(f"/roles/{rol.id_rol}", headers=member_headers).json()["data"]

        assert [r["nombre"] for r in lista] == ["Utilero"]
        assert uno["nombre"] == "Utilero"

    def test_reports_a_role_that_does_not_exist(self, client, member_headers):
        assert client.get("/roles/9999", headers=member_headers).json()["message"] == "Rol no encontrado"

    def test_admin_patches_replaces_and_deletes_a_role(self, client, db, admin_headers):
        rol = make_role(db, 2001, nombre="Viejo")

        client.patch(f"/roles/{rol.id_rol}", json={"activo": False}, headers=admin_headers)
        db.refresh(rol)
        assert rol.activo is False

        client.put(f"/roles/{rol.id_rol}", json={**ROL, "nombre": "Reemplazado"}, headers=admin_headers)
        db.refresh(rol)
        assert rol.nombre == "Reemplazado"

        assert client.delete(f"/roles/{rol.id_rol}", headers=admin_headers).json()["success"] is True

    @pytest.mark.parametrize("metodo", ["put", "patch", "delete"])
    def test_changing_a_missing_role_is_reported(self, client, admin_headers, metodo):
        kwargs = {} if metodo == "delete" else {"json": ROL if metodo == "put" else {"nombre": "x"}}

        body = getattr(client, metodo)("/roles/9999", headers=admin_headers, **kwargs).json()

        assert body["message"] == "Rol no encontrado"
