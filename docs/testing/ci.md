# CI de FOCCUS_PRUEBA

Workflow: [`.github/workflows/tests.yml`](../../.github/workflows/tests.yml). Corre en cada push a `main` y en cada pull request.

```
frontend ─┐
backend  ─┼──▶ e2e
integracion ─┘          evidencia-individual (independiente)
```

| Job | Qué corre | BD | Comando local equivalente |
|---|---|---|---|
| `frontend` | Vitest + cobertura (umbral en `vite.config.js`) | — | `cd frontend && npm test` |
| `backend` | pytest: unitarias, API (SQLite), dobles; umbral en `.coveragerc` | SQLite en memoria | `cd backend/api_usuarios && pytest -m "not integration"` |
| `integracion` | `tests/integration` contra MariaDB 10.11 | **servicio** `mariadb:10.11` con health-check | `TEST_DATABASE_URL=… pytest tests/integration --no-cov` |
| `e2e` | Playwright (31 tests): backend en segundo plano + frontend levantado por Playwright | servicio `mariadb:10.11` | `cd e2e && npm test` |

## Decisiones de diseño

- **Cero saltados.** El job `backend` *deselecciona* la integración (`-m "not integration"`), no la salta. El job `integracion` define `REQUIRE_INTEGRATION=1`: si la BD no llega, el job **falla**; además un paso comprueba que la salida no contenga «skipped».
- **BD como servicio.** El job espera al `healthcheck` de MariaDB antes de empezar; el backend del E2E se espera con `curl --retry-connrefused`, no con `sleep`.
- **Caché**: dependencias de pip y npm (`setup-python`/`setup-node`) y el navegador de Playwright (clave con la versión de Playwright).
- **Artefactos**: `coverage-frontend`, `coverage-backend` (HTML, siempre) y, si el E2E falla, `playwright-report` (con trazas) y `backend-log`.
- **E2E depende de los demás** (`needs`): no se gastan 3 minutos de navegador si ya falló una unitaria.
- `permissions: contents: read` y `concurrency`: mínimo privilegio y un run por rama.
- Las contraseñas del workflow son las de una BD que solo existe durante el job; no son secretos.

## Qué pasa si se borra `TEST_DATABASE_URL` del job de integración

Sin `REQUIRE_INTEGRATION` los tests **se saltarían y el job quedaría en verde sin probar nada**. Con la guarda, el fixture `mysql_engine` llama a `pytest.fail` y el job queda en rojo. Verificado en local:

```text
REQUIRE_INTEGRATION=1 pytest tests/integration  →  Failed: REQUIRE_INTEGRATION=1 pero TEST_DATABASE_URL no está definida
```

## Configuración manual en GitHub (no se puede versionar en el repo)

Settings → Rules → Rulesets → *Add branch ruleset* sobre `main`:

1. **Require a pull request before merging**.
2. **Require status checks to pass**: marcar `frontend`, `backend`, `integracion` y `e2e`. Los nombres aparecen tras el primer run.
3. **Block force pushes**.

Comprobación: abrir un PR de prueba con un test roto en cada capa y confirmar que *Merge* queda bloqueado; cerrarlo sin fusionar.

## Rojo provocado (cómo demostrar que cada job detecta fallos)

| Job | Cambio que debe ponerlo en rojo |
|---|---|
| `frontend` | Cambiar `mail.trim().toLowerCase()` por `mail.trim()` en `Login.jsx`; o subir un umbral por encima de la cobertura real |
| `backend` | Quitar `Depends(require_admin)` de `DELETE /users/{id}` (la matriz de acceso falla); o `fail_under = 100` |
| `integracion` | Quitar `ON DELETE CASCADE` de un modelo; o borrar `TEST_DATABASE_URL` del job |
| `e2e` | `!isTokenValid()` → `false` en `ProtectedRoute.jsx` (3 specs de sesión fallan) |

Todos estos cambios se probaron en local durante la implementación y los tests los detectaron (ver el historial de mutaciones en cada commit); los enlaces a *runs* en rojo de GitHub Actions se generan al abrir el PR.
