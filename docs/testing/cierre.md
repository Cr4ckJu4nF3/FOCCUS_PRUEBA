# Cierre de la suite (semana 9)

Condición para sustentar: CI completo en verde, cobertura ≥ 80 % y hallazgos resueltos o registrados.

## 1. Dos corridas completas seguidas, sin reintentos manuales

Ejecutadas en local con los mismos comandos del CI (MariaDB 10.11, backend en :8000, Chromium real, `CI=1` para activar el modo de reintento del workflow). Los enlaces a los runs de GitHub Actions se obtienen al fusionar la rama.

| Job | Corrida 1 | Corrida 2 | Saltados |
|---|---|---|:---:|
| backend + integración (`pytest`, `TEST_DATABASE_URL` definida) | 577 pasan · 23 fallo esperado · 99,02 % | 577 · 23 · 99,02 % | 0 |
| frontend (`npm test`) | 148 pasan · 1 fallo esperado · 100 % | 148 · 1 · 100 % | 0 |
| e2e (`CI=1 npx playwright test`) | 31 pasan (55 s) | 31 pasan (54 s) | 0 |

Ninguna prueba intermitente: ningún test pasó solo en un reintento (el reporte no muestra «flaky»). Los E2E también se repitieron con `--repeat-each=2` (62/62).

## 2. Tests saltados: cero

- `backend` ejecuta `pytest -m "not integration"`: la integración queda **deseleccionada**, no saltada.
- `integracion` corre con `REQUIRE_INTEGRATION=1`: si falta la BD, **falla**.
- Los «fallos esperados» (`xfail(strict=True)`, `it.fails`) no son saltos: se ejecutan y deben fallar; si el defecto se corrige, el test pasa y `strict` rompe el build para obligar a retirar la marca.

## 3. Hallazgos del trimestre

40 en total ([hallazgos.md](hallazgos.md)):

| Estado | Cantidad | Qué es |
|---|:---:|---|
| ✅ Corregido | 6 | Etiquetas, nombres accesibles y roles en el frontend; `validarContrasena` extraída |
| 🔒 Abierto con test de fallo esperado | 22 | Se ejecutan como 24 tests: 23 `xfail(strict)` en backend (H-B25 son 3 casos) y 1 `it.fails` en frontend |
| 📝 Anotado sin test | 12 | Código muerto, riesgos de diseño, contrato HTTP 200, CSS |

Cada 🔒 pasará a verde cuando se corrija y obligará a quitar la marca. Los defectos **no** se corrigieron en el código de la aplicación a propósito: FOCCUS_PRUEBA es un espacio de pruebas y varios arreglos (H-B01, H-B18) cambian el contrato con el frontend de FOCCUS.

## 4. Umbrales

| Parte | Umbral | Plan |
|---|---|---|
| Frontend | 100 / 99 / 100 / 100 (líneas / ramas / funciones / sentencias) | ≥ 80 |
| Backend | 99 (líneas + ramas) | ≥ 80 |

## 5. Ensayo cruzado

Cada integrante debe poder, sobre una capa que **no** escribió: explicar un test, romperlo con un cambio en el código y escribir uno nuevo. Para practicar, estos puntos de partida salen de los mutantes verificados en cada commit (`git log --grep "mutante"`), p. ej.:

| Capa | Rompe… | …con este cambio |
|---|---|---|
| API | la matriz de acceso | quitar `Depends(require_admin)` de `DELETE /users/{id}` |
| Dobles | el reloj | `>` por `>=` en la expiración del código |
| Componentes | `ProtectedRoute` | `!isTokenValid()` por `false` |
| Integración | el collation | comparar con `BINARY` |
| E2E | el guardián de rutas | mismo cambio que en componentes: 3 specs de sesión fallan |
