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

## Resultado (historial de la rama `test/semana-10-tdd`)

Cada ciclo deja dos commits: el test en rojo y el código que lo pone en verde. Mensajes reales de cada Red:

| Ciclo | Red (por qué falló) | Green (cambio mínimo) |
|---|---|---|
| E2E inicial | `Received: 60 x` esperando 45 · no existe `8/45` · API `Expected 422, Received 500` | — (verde al final) |
| C1 `POST /projects` | `assert 200 == 422` | `max_length=45` en `ProjectSchema` |
| C2 `POST /projects/create` | `ValidationError` sin controlar: la ruta arma un `ProjectSchema` interno y explota (500 real) | mismo límite en `ProjectCreateSchema` |
| C3 `PATCH` / `PUT` | `PATCH: assert 200 == 422`. **`PUT` nació en verde** (ya lo cubría C1) | límite en `ProjectUpdateSchema` |
| **Refactor** | suite en verde | un solo tipo `ProjectName` en los tres schemas |
| C4 nombre vacío / solo espacios | 8 de 8: `assert 200 == 422` | `StringConstraints(strip_whitespace, min_length=1, max_length=45)`: **un solo cambio** sirve a los 4 endpoints gracias al refactor |
| F1 campo del modal | `Expected the element to have attribute maxLength=45` | `maxLength={45}` |
| F2 contador | `Unable to find an element with the text: 0/45` | `<small>{n}/45</small>` |

Nacieron en verde (documentan valores límite, no son ciclos): 45 caracteres exactos y recorte de espacios.

## Mutaciones sobre el código nuevo

| Cambio en el código | Tests que fallan |
|---|---|
| quitar `strip_whitespace` | 5 |
| quitar `min_length=1` | 8 |
| límite 45 → 46 | 4 |
| límite 45 → 44 | 1 |
| `maxLength={45}` → `{46}` (front) | 1 |
| contador `/45` → `/46` (front) | 1 |

Ningún cambio sobrevivió: no hay código que ningún test haya pedido.

## Cierre de la lista

- [x] Los 9 puntos de la lista. El E2E escrito al inicio (3 tests) pasó de rojo a verde.
- Quedan fuera (incidencia): mensajes de 422 en español; límites de las demás columnas (resto de H-B25); el código muerto `ProjectSchema` duplicado (H-B22) sigue en `project_schema.py`.
- Efecto en hallazgos: **H-B25 queda parcialmente corregido** (`project_name`). El test de integración correspondiente pasó de `xfail` a test normal.
- CI/cobertura: backend 99,02 % · frontend 100 % · E2E 34/34.
