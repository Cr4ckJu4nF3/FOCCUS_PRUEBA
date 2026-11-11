"""Usuarios, membresías de proyecto e invitaciones (contrato HTTP)."""
from datetime import datetime

import pytest

from app.models.user_model import User
from app.models.user_project_model import UserProject
from tests.factories import DEFAULT_PASSWORD, link_user, make_project, make_user

pytestmark = pytest.mark.api

NUEVO_USUARIO = dict(
    nombre="juan carlos",
    apellido="pérez",
    identificacion="CC",
    id_identificacion="1020304050",
    mail="  Juan@Foccus.test ",
    msisdn="3001112233",
    direccion="calle 10",
    fecha_de_nacimiento="1992-05-04T00:00:00",
    estado="activo",
    contrasena=DEFAULT_PASSWORD,
    id_departamento="ARTE",
    id_project="proj0001",
    id_rol=1005,
)


class TestListAndGetUsers:
    def test_admin_lists_every_user_without_password_hashes(self, client, db, admin_headers, member_user):
        response = client.get("/users", headers=admin_headers)

        body = response.json()
        assert body["success"] is True
        assert {u["mail"] for u in body["data"]} >= {"admin@foccus.test", "miembro@foccus.test"}
        assert "$2b$" not in response.text

    def test_returns_one_user_by_id_without_the_password_hash(self, client, member_user, admin_headers):
        response = client.get(f"/users/{member_user.id_user}", headers=admin_headers)

        body = response.json()
        assert body["data"]["mail"] == "miembro@foccus.test"
        assert "contrasena" not in body["data"]
        assert "$2b$" not in response.text

    def test_reports_a_user_that_does_not_exist(self, client, admin_headers):
        body = client.get("/users/9999", headers=admin_headers).json()

        assert body["success"] is False
        assert body["message"] == "Usuario no encontrado"

    def test_returns_422_when_the_id_is_not_a_number(self, client, admin_headers):
        assert client.get("/users/abc", headers=admin_headers).status_code == 422


class TestCreateUser:
    def test_admin_creates_a_user_with_normalized_data_and_a_hashed_password(self, client, db, admin_headers):
        body = client.post("/users", json=NUEVO_USUARIO, headers=admin_headers).json()

        assert body["success"] is True
        assert body["data"]["nombre"] == "Juan Carlos"
        assert body["data"]["mail"] == "juan@foccus.test"
        guardado = db.query(User).filter(User.mail == "juan@foccus.test").one()
        assert guardado.contrasena != DEFAULT_PASSWORD
        assert guardado.contrasena.startswith("$2")

    def test_rejects_a_duplicate_email(self, client, db, admin_headers):
        make_user(db, mail="juan@foccus.test")
        duplicado = {**NUEVO_USUARIO, "mail": "juan@foccus.test"}

        body = client.post("/users", json=duplicado, headers=admin_headers).json()

        assert body["error"] == "DUPLICATE_EMAIL"

    def test_rejects_a_duplicate_identification(self, client, db, admin_headers):
        make_user(db, id_identificacion="1020304050")

        body = client.post("/users", json=NUEVO_USUARIO, headers=admin_headers).json()

        assert body["error"] == "DUPLICATE_ID"

    def test_returns_422_when_a_required_field_is_missing(self, client, admin_headers):
        incompleto = {k: v for k, v in NUEVO_USUARIO.items() if k != "mail"}

        assert client.post("/users", json=incompleto, headers=admin_headers).status_code == 422


class TestUpdateUser:
    def test_put_replaces_the_profile_data(self, client, db, admin_headers):
        usuario = make_user(db, mail="viejo@foccus.test")
        datos = {**NUEVO_USUARIO, "mail": "nuevo@foccus.test", "id_identificacion": usuario.id_identificacion}

        body = client.put(f"/users/{usuario.id_user}", json=datos, headers=admin_headers).json()

        assert body["success"] is True
        db.refresh(usuario)
        assert usuario.mail == "nuevo@foccus.test"
        assert usuario.nombre == "Juan Carlos"

    def test_patch_changes_only_the_fields_that_are_sent(self, client, db, admin_headers):
        usuario = make_user(db, nombre="Ana", apellido="Ruiz")

        client.patch(f"/users/{usuario.id_user}", json={"nombre": "Marta"}, headers=admin_headers)

        db.refresh(usuario)
        assert usuario.nombre == "Marta"
        assert usuario.apellido == "Ruiz"

    def test_patch_hashes_a_new_password_so_the_user_can_log_in_with_it(self, client, db, admin_headers):
        usuario = make_user(db, mail="ana@foccus.test")

        client.patch(f"/users/{usuario.id_user}", json={"contrasena": "Otra#2026x"}, headers=admin_headers)

        login = client.post("/users/login", json={"mail": "ana@foccus.test", "contrasena": "Otra#2026x"}).json()
        assert login["success"] is True

    @pytest.mark.parametrize("metodo", ["put", "patch"])
    def test_reports_a_user_that_does_not_exist(self, client, admin_headers, metodo):
        payload = NUEVO_USUARIO if metodo == "put" else {"nombre": "X"}

        body = getattr(client, metodo)("/users/9999", json=payload, headers=admin_headers).json()

        assert body["message"] == "Usuario no encontrado"


class TestDeleteUser:
    def test_admin_deletes_a_user(self, client, db, admin_headers, member_user):
        body = client.delete(f"/users/{member_user.id_user}", headers=admin_headers).json()

        assert body["success"] is True
        assert db.query(User).filter(User.id_user == member_user.id_user).count() == 0

    def test_reports_a_user_that_does_not_exist(self, client, admin_headers):
        assert client.delete("/users/9999", headers=admin_headers).json()["message"] == "Usuario no encontrado"

    def test_any_user_can_delete_their_own_account(self, client, db, member_user, member_headers):
        body = client.delete("/users/me/account", headers=member_headers).json()

        assert body["success"] is True
        assert db.query(User).filter(User.id_user == member_user.id_user).count() == 0

    def test_deleting_my_account_does_not_touch_other_users(self, client, db, admin_user, member_headers, member_user):
        client.delete("/users/me/account", headers=member_headers)

        assert db.query(User).filter(User.id_user == admin_user.id_user).count() == 1


class TestProjectMembership:
    @pytest.fixture
    def proyecto_con_miembro(self, db, member_user):
        proyecto = make_project(db)
        link_user(db, member_user, proyecto, id_rol=1005, departamento="Arte", cargo="Utilero")
        return proyecto

    def test_lists_the_users_of_a_project_with_their_role_in_it(self, client, admin_headers, proyecto_con_miembro):
        body = client.get(f"/users/project/{proyecto_con_miembro.id_project}", headers=admin_headers).json()

        assert len(body["data"]) == 1
        assert body["data"][0]["mail"] == "miembro@foccus.test"
        assert body["data"][0]["departamento"] == "Arte"
        assert body["data"][0]["id_rol"] == 1005

    def test_lists_nobody_for_a_project_without_members(self, client, db, admin_headers):
        proyecto = make_project(db)

        assert client.get(f"/users/project/{proyecto.id_project}", headers=admin_headers).json()["data"] == []

    def test_lists_the_projects_of_a_user(self, client, admin_headers, member_user, proyecto_con_miembro):
        body = client.get(f"/users/{member_user.id_user}/projects", headers=admin_headers).json()

        assert [p["id_project"] for p in body["data"]] == [proyecto_con_miembro.id_project]
        assert body["data"][0]["id_rol"] == 1005

    def test_admin_updates_department_title_and_role_of_a_member(
        self, client, db, admin_headers, member_user, proyecto_con_miembro
    ):
        ruta = f"/users/{member_user.id_user}/project/{proyecto_con_miembro.id_project}"

        body = client.patch(ruta, json={"cargo": "Jefe de arte", "id_rol": 1002}, headers=admin_headers).json()

        assert body["data"]["cargo"] == "Jefe de arte"
        assert body["data"]["id_rol"] == 1002
        assert body["data"]["departamento"] == "Arte"  # lo que no se envía se conserva

    def test_updating_a_non_member_reports_membership_not_found(self, client, db, admin_headers, member_user):
        proyecto = make_project(db)

        body = client.patch(
            f"/users/{member_user.id_user}/project/{proyecto.id_project}", json={"cargo": "X"}, headers=admin_headers
        ).json()

        assert body["error"] == "MEMBERSHIP_NOT_FOUND"

    def test_admin_removes_a_member_from_the_project_but_keeps_the_user(
        self, client, db, admin_headers, member_user, proyecto_con_miembro
    ):
        ruta = f"/users/{member_user.id_user}/project/{proyecto_con_miembro.id_project}"

        body = client.delete(ruta, headers=admin_headers).json()

        assert body["success"] is True
        assert db.query(UserProject).count() == 0
        assert db.query(User).filter(User.id_user == member_user.id_user).count() == 1

    def test_removing_a_non_member_reports_it(self, client, db, admin_headers, member_user):
        proyecto = make_project(db)

        body = client.delete(f"/users/{member_user.id_user}/project/{proyecto.id_project}", headers=admin_headers).json()

        assert body["success"] is False


class TestInviteUsers:
    @pytest.fixture
    def proyecto(self, db):
        return make_project(db, project_name="Mi serie")

    def _invitar(self, client, headers, proyecto, correos, id_rol=1005):
        return client.post(
            "/users/invite",
            json={"correos": correos, "id_project": proyecto.id_project, "id_client": proyecto.id_client, "id_rol": id_rol},
            headers=headers,
        ).json()

    def test_creates_a_pending_account_linked_to_the_project_and_emails_a_temporary_password(
        self, client, db, admin_headers, proyecto, no_real_emails
    ):
        body = self._invitar(client, admin_headers, proyecto, ["nuevo@foccus.test"])

        assert body["data"]["total_invitados"] == 1
        assert body["data"]["usuarios_creados"][0]["usuario_existente"] is False
        usuario = db.query(User).filter(User.mail == "nuevo@foccus.test").one()
        assert usuario.estado == "pendiente"
        assert db.query(UserProject).filter_by(id_user=usuario.id_user, id_project=proyecto.id_project).count() == 1
        correo, nombre_proyecto, contrasena = no_real_emails["send_invitation_email"].call_args.args
        assert (correo, nombre_proyecto) == ("nuevo@foccus.test", "Mi serie")
        assert len(contrasena) == 10

    def test_the_emailed_temporary_password_lets_the_invitee_log_in(
        self, client, admin_headers, proyecto, no_real_emails
    ):
        self._invitar(client, admin_headers, proyecto, ["nuevo@foccus.test"])
        contrasena = no_real_emails["send_invitation_email"].call_args.args[2]

        login = client.post("/users/login", json={"mail": "nuevo@foccus.test", "contrasena": contrasena}).json()

        assert login["success"] is True

    def test_links_an_existing_account_without_creating_a_new_one(
        self, client, db, admin_headers, proyecto, member_user
    ):
        body = self._invitar(client, admin_headers, proyecto, ["miembro@foccus.test"])

        assert body["data"]["usuarios_creados"][0]["usuario_existente"] is True
        assert db.query(User).filter(User.mail == "miembro@foccus.test").count() == 1
        assert db.query(UserProject).filter_by(id_user=member_user.id_user).count() == 1

    def test_reports_an_error_for_someone_already_in_the_project_and_still_invites_the_rest(
        self, client, db, admin_headers, proyecto, member_user
    ):
        link_user(db, member_user, proyecto)

        body = self._invitar(client, admin_headers, proyecto, ["miembro@foccus.test", "otro@foccus.test"])

        assert body["data"]["total_errores"] == 1
        assert body["data"]["errores"][0]["error"] == "Usuario ya está en el proyecto"
        assert body["data"]["total_invitados"] == 1

    def test_reports_a_project_that_does_not_exist(self, client, admin_headers, proyecto):
        body = client.post(
            "/users/invite",
            json={"correos": ["a@x.co"], "id_project": "proj9999", "id_client": 1, "id_rol": 1005},
            headers=admin_headers,
        ).json()

        assert body["error"] == "PROJECT_NOT_FOUND"

    def test_keeps_the_account_and_flags_it_when_the_email_cannot_be_sent(
        self, client, db, admin_headers, proyecto, no_real_emails
    ):
        no_real_emails["send_invitation_email"].side_effect = RuntimeError("SMTP caído")

        body = self._invitar(client, admin_headers, proyecto, ["nuevo@foccus.test"])

        assert body["data"]["usuarios_creados"][0]["invitacion_enviada"] is False
        assert db.query(User).filter(User.mail == "nuevo@foccus.test").count() == 1
