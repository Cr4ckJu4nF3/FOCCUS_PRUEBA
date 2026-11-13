# Análisis de ramas sin cubrir (semana 8)

Se activó cobertura de **ramas** en el backend (`branch = True`) y se revisó cada línea/rama marcada por `coverage report -m` y por el reporte de Vitest. Para cada una: se escribió el test o se justifica por qué no.

## Backend: 96,9 % → 99,02 %

| Dónde | Qué comportamiento quedaba sin probar | Resolución |
|---|---|---|
| 7 generadores de id (`escena`, `escenario`, `personaje`, `rodaje`, `project`, `desglose`, `requerimiento`) | El respaldo `except ValueError → 0001` cuando el último id no es numérico | ✅ `TestIdGenerationFallback`. Hallazgo H-B28: ese respaldo puede **repetir** un id existente |
| `desglose_controller` `_generar_id_escena_local` | Tercera copia del generador | ✅ `test_the_breakdown_import_restarts_scene_ids…` |
| `desglose_routes` / `rodaje_routes` | Falla al borrar el PDF temporal (`OSError`) | ✅ la importación no se rompe |
| `rodaje_controller` asignar escena | La escena ya tenía fecha de grabación: se conserva | ✅ |
| `desglose_controller` listado de guion | Escenas asignadas a un día de rodaje | ✅ |
| `project_controller` `create_and_link` | El alta falla → no se crea la membresía | ✅ |
| `user_controller` login / verificación 2FA | `id_client` ya guardado en el usuario; sin empresa ni proyectos; recurso por proyecto | ✅ |
| `user_controller` `reset_password` | Usuario borrado tras pedir el código | ✅ |
| `user_controller` invitaciones | Correo de aviso falla para una cuenta existente; un correo no procesable | ✅ (+ **H-B27**, defecto real) |
| `desglose_parser` | Escena sin conteo de páginas; página suelta antes de la primera escena; número de escena sin modo; encabezado sin momento del día; líneas vacías; sinopsis ya capturada; **lectura de un PDF real** con `pypdf` | ✅ (el PDF se fabrica en el test, sin dependencias nuevas) |
| `project_controller` líneas 48-67 y 202-214 | `create_project` y `create_project_and_link` **definidos dos veces**: la primera definición queda pisada por la segunda | ❌ **Código muerto** (H-B22): no se prueba, se borra |
| `user_controller` 261→264 y 471→474 | `if project:` falso: una membresía cuyo proyecto no existe | ❌ Inalcanzable: `user_projects.id_project` es FK, la BD no lo permite |
| `desglose_controller` 64→67 | `escena.id_desglose` apunta a un desglose inexistente | ❌ Inalcanzable por la FK `escenas.id_desglose` |
| `rodaje_controller` 257→244 | El día de la escena no existe tras haberlos creado todos | ❌ Inalcanzable: justo antes se crean todos los días del PDF |

## Frontend: 97,0 % líneas → 100 % (ramas 99,6 % → 100 %)

| Dónde | Rama | Resolución |
|---|---|---|
| `Login` | Respuesta de 2FA sin envoltorio `data`; envío del código sin motivo; registro fallido solo con `error` o sin nada | ✅ |
| `ForgotPassword` | Mensajes de respaldo y prioridad de `detail` sobre `message` | ✅ |
| `TwoFactor` | Pantalla abierta sin el correo en el estado; reenvío fallido sin motivo; el aviso «código reenviado» desaparece a los 3 s (reloj falso) | ✅ |
| `ProjectSelection` | Respuesta sin `data`, rol ausente, empresa ausente (usa 1), cierre del modal por la X y por el fondo | ✅ (+ H-F12, la X no tenía nombre accesible) |

## Mutación sobre los tests nuevos

| Test | Cambio en el código que lo hace fallar |
|---|---|
| `TestIdGenerationFallback` (escena) | `new_num = 1` → `new_num = 2` en `escena_controller` |
| `…keeps the recording date it already had` | `if rodaje.fecha_inicio and not escena.fecha_de_grabacion` → `if rodaje.fecha_inicio` |
| `…2fa_verify_falls_back_to_the_client_of_the_first_project` | eliminar el bloque que resuelve `id_client` por membresía |
| `TestRodajeParserBranches` (sin momento del día) | devolver `(resto, "Día")` en vez de `None` en `_parse_header_escena_rodaje` |
| (equivalente) | `if m_pag:` → `if True and m_pag:` no cambia el comportamiento: mutante equivalente, no detectable |
