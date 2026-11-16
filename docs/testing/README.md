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

Documentos: [cobertura y trinquete](cobertura.md) · [hallazgos](hallazgos.md)
