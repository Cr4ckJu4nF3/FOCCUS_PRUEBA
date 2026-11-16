# Semana 10 (opcional): TDD — validar el nombre del proyecto

> Historia derivada del hallazgo **H-B25**. Los criterios y la lista de pruebas se escribieron **antes** del primer commit de código. Es una propuesta de ejemplo: la semana 10 pide una historia nueva del backlog del equipo; si prefieren otra, este documento sirve de molde.

## Historia

Como **administrador**, quiero que el sistema valide el nombre del proyecto al crearlo o editarlo, para recibir un aviso claro en vez de un error 500 cuando el nombre es demasiado largo.

## Criterios de aceptación

1. **Dado** un nombre de 46 caracteres, **cuando** se crea un proyecto (`POST /projects`), **entonces** responde **422** y el detalle nombra el campo `project_name`. (Hoy: 500 en MySQL estricto.)
2. Lo mismo al crear y vincular (`POST /projects/create`) y al editar (`PUT` y `PATCH /projects/{id}`).
3. **Dado** un nombre vacío o solo de espacios, **entonces** responde 422.
4. **Dado** un nombre de exactamente 45 caracteres, **entonces** se acepta (valor límite).
5. **En el formulario**, el campo no deja escribir más de 45 caracteres y muestra cuántos lleva («12/45»).

## Lista de pruebas (se tacha al terminar cada ciclo)

| # | Capa | Prueba | Ciclo |
|---|---|---|:---:|
| 0 | E2E | No se pueden teclear más de 45 caracteres en el nombre · se ve el contador · la API rechaza 46 con 422 | al inicio, en rojo |
| 1 | API | `POST /projects` con 46 caracteres → 422 con `project_name` | C1 |
| 2 | API | `POST /projects/create` con 46 caracteres → 422 | C2 |
| 3 | API | `PATCH` y `PUT /projects/{id}` con 46 caracteres → 422 | C3 |
| — | — | *Refactor*: una sola definición del tipo «nombre de proyecto» | R |
| 4 | API | Nombre vacío o solo espacios → 422 (en los 4 endpoints) | C4 |
| 5 | API | 45 caracteres exactos se aceptan | (nace verde: valor límite) |
| 6 | Integración | Con MariaDB real, 46 caracteres → 422 y no 500 | C1 |
| 7 | Front | El campo tiene `maxLength=45` | F1 |
| 8 | Front | Un contador «n/45» se actualiza al escribir | F2 |

## Ideas que aparecieron y quedan fuera de esta historia

- Validar longitudes de `razon_social`, `roles.nombre`, etc. (resto de H-B25).
- Mensajes de error en español (hoy son los de Pydantic).
