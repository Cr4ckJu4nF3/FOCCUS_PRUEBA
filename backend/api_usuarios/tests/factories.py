"""Fábricas de datos: arman filas directamente en la BD (el "Arrange" de cada test).

Los tests de la API usan estas funciones para preparar el estado y la API real
solo para el "Act", así un test no depende de que otro endpoint funcione.
"""
from datetime import date, datetime

from passlib.context import CryptContext

from app.models.client_model import Client
from app.models.desglose_model import Desglose
from app.models.desglose_requerimiento_model import DesgloseRequerimiento
from app.models.escena_model import Escena
from app.models.Guion import Guion
from app.models.guion_version_model import GuionVersion
from app.models.personajes_model import Personaje
from app.models.project_model import Project
from app.models.rodaje_model import Rodaje
from app.models.role_model import Role
from app.models.user_model import User
from app.models.user_project_model import UserProject

DEFAULT_PASSWORD = "Foccus#2026"
# cost bajo: los tests no necesitan un hash lento
_hasher = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4)

_counter = {"n": 0}


def _next():
    _counter["n"] += 1
    return _counter["n"]


def _save(db, obj):
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_client(db, **kw):
    n = _next()
    data = dict(
        document="NIT",
        id_document=f"900{n}",
        razon_social=f"Productora {n}",
        representante_legal="Laura Gómez",
        email=f"empresa{n}@foccus.test",
        address="Calle 1",
        telephone="6010000",
        number_cellphone="3000000000",
    )
    data.update(kw)
    return _save(db, Client(**data))


def make_role(db, id_rol, nombre=None, **kw):
    data = dict(id_rol=id_rol, nombre=nombre or f"Rol {id_rol}", nivel_jerarquia="1", activo=True)
    data.update(kw)
    return _save(db, Role(**data))


def make_user(db, *, mail=None, password=DEFAULT_PASSWORD, id_rol=1005, **kw):
    n = _next()
    data = dict(
        nombre="Ana",
        apellido="Ruiz",
        identificacion="CC",
        id_identificacion=f"ID-{n}",
        mail=mail or f"user{n}@foccus.test",
        msisdn="3001112233",
        direccion="Calle 2",
        fecha_de_nacimiento=datetime(1990, 1, 1),
        estado="activo",
        contrasena=_hasher.hash(password),
        id_rol=id_rol,
    )
    data.update(kw)
    return _save(db, User(**data))


def make_project(db, id_client=None, **kw):
    n = _next()
    data = dict(
        id_project=f"proj{n:04d}",
        project_name=f"Proyecto {n}",
        formato_de_produccion="Serie",
        genero="Drama",
        sinopsis="Sinopsis",
        director="Director",
        id_client=id_client if id_client is not None else make_client(db).id_cliente,
    )
    data.update(kw)
    return _save(db, Project(**data))


def link_user(db, user, project, id_rol=1005, **kw):
    return _save(db, UserProject(id_user=user.id_user, id_project=project.id_project, id_rol=id_rol, **kw))


def make_guion(db, project, **kw):
    data = dict(nombre="Guion piloto", descripcion="Primer borrador", id_project=project.id_project)
    data.update(kw)
    return _save(db, Guion(**data))


def make_guion_version(db, guion, user, numero=1, estado="Borrador", contenido="INT. SALA - NOCHE", **kw):
    version = _save(
        db,
        GuionVersion(
            id_guion=guion.id_guion,
            numero_de_version=numero,
            contenido=contenido,
            fecha_de_emision=date(2026, 1, 5),
            estado=estado,
            creado_por=user.id_user,
            **kw,
        ),
    )
    guion.id_guion_version_actual = version.id_guion_version
    db.commit()
    return version


def make_escena(db, guion, numero="1", **kw):
    n = _next()
    data = dict(
        id_escena=f"esc{n:04d}",
        numero_de_escena=numero,
        encabezado=f"Escena {numero}",
        id_guion=guion.id_guion,
        estado="Pendiente",
    )
    data.update(kw)
    return _save(db, Escena(**data))


def make_rodaje(db, project, **kw):
    n = _next()
    data = dict(
        id_rodaje=f"rod{n:04d}",
        id_project=project.id_project,
        nombre=f"Día {n}",
        fecha_inicio=date(2026, 1, 5),
        estado="Pendiente",
    )
    data.update(kw)
    return _save(db, Rodaje(**data))


def make_requerimiento(db, escena, departamento="Props", etiqueta="lámpara", cantidad=1):
    n = _next()
    if not escena.id_desglose:
        desglose = _save(db, Desglose(id_desglose=f"dsg{n:04d}"))
        escena.id_desglose = desglose.id_desglose
        db.commit()
    return _save(
        db,
        DesgloseRequerimiento(
            id_requerimiento=f"req{n:04d}",
            id_desglose=escena.id_desglose,
            departamento=departamento,
            etiqueta=etiqueta,
            cantidad=cantidad,
        ),
    )


def make_personaje(db, project, nombre="Julia", **kw):
    n = _next()
    data = dict(id_personaje=f"psj{n:04d}", nombre=nombre, id_project=project.id_project)
    data.update(kw)
    return _save(db, Personaje(**data))
