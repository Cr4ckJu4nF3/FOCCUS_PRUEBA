# Pruebas de FOCCUS_PRUEBA

Implementación del bootcamp de testing ADSO ([bc-testing-adso](https://github.com/ergrato-dev/bc-testing-adso)) sobre este repo. Una semana por commit (`test(semana-NN)`).

| Sem | Tema | Dónde está |
|:---:|---|---|
| 1 | Primer E2E + línea base | `e2e/tests/login.spec.js`, `register.spec.js` · `docs/matriz-rotacion.md` |
| 2 | Unitarias + CI + umbral | `backend/api_usuarios/tests/unit/` · `frontend/tests/*.test.js` · `.github/workflows/tests.yml` |
| 3 | Componentes React | `frontend/tests/components/` (Login, TwoFactor, ForgotPassword, ProtectedRoute) |
| 4 | Contrato de la API | `backend/api_usuarios/tests/api/` (incluye `test_access_control_api.py` y `test_known_defects_api.py`) |
| 5 | Dobles de prueba | `backend/.../tests/doubles/` (SMTP mock, extractor de PDF stub, reloj falso) · `frontend/tests/api-fetch.test.js`, `components/Login.msw.test.jsx` (MSW) |
| 6 | Integración con BD real | `backend/.../tests/integration/` · `docker-compose.test.yml` · [integracion.md](integracion.md) |
| 7 | E2E avanzados | `e2e/tests/` (`pages/` Page Objects, `fixtures.js`, 6 specs, 31 tests) · [e2e/README.md](../../e2e/README.md) |
| 8 | CI completo | `.github/workflows/tests.yml` · [ci.md](ci.md) · [ramas-sin-cubrir.md](ramas-sin-cubrir.md) |
| 9 | Integrador | [estrategia-pruebas.md](../estrategia-pruebas.md) · [cierre.md](cierre.md) |
| 10 | TDD (rama `test/semana-10-tdd`) | [tdd-nombre-de-proyecto.md](tdd-nombre-de-proyecto.md) · `backend/.../tests/tdd/` · `e2e/tests/project-name-limit.spec.js` |

Documentos: [cobertura y trinquete](cobertura.md) · [hallazgos](hallazgos.md)
