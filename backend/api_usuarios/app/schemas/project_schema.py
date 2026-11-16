from pydantic import BaseModel, StringConstraints
from typing import Annotated, Optional

# projects.project_name es VARCHAR(45) (ver models/project_model.py): una sola definición del límite
PROJECT_NAME_MAX_LENGTH = 45
ProjectName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=PROJECT_NAME_MAX_LENGTH)]

class ProjectSchema(BaseModel):
    id_project: str
    project_name: str
    formato_de_produccion: str
    genero: str
    sinopsis: Optional[str] = None
    director: Optional[str] = None
    id_client: int

class ProjectUpdateSchema(BaseModel):
    project_name: Optional[ProjectName] = None
    formato_de_produccion: Optional[str] = None
    genero: Optional[str] = None
    sinopsis: Optional[str] = None
    director: Optional[str] = None
    id_client: Optional[int] = None

class ProjectSchema(BaseModel):
    id_project: Optional[str] = None
    project_name: ProjectName
    formato_de_produccion: str
    genero: str
    sinopsis: Optional[str] = None
    director: Optional[str] = None
    id_client: int

class ProjectCreateSchema(BaseModel):
    project_name: ProjectName
    formato_de_produccion: str
    genero: str
    sinopsis: Optional[str] = None
    director: Optional[str] = None
    id_client: int
    id_user: int