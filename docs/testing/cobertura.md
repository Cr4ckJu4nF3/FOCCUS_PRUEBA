# Cobertura y regla de trinquete

La cobertura se mide con el **mismo comando de test de siempre** y falla si baja del umbral.

| Capa | Comando (desde la carpeta) | Configuración |
|---|---|---|
| Backend | `backend/api_usuarios` → `pytest` | `pytest.ini` + `.coveragerc` (`fail_under`) |
| Frontend | `frontend` → `npm test` | `vite.config.js` → `test.coverage.thresholds` |

## Qué se mide (y qué no)

- **Backend**: todo `app/` salvo `app/main.py` y `app/config/database.py` (arranque y conexión: se ejercitan en integración, semana 6).
- **Frontend**: `api.js`, `utils/` y las pantallas del flujo de autenticación (`ProtectedRoute`, `Login`, `TwoFactor`, `ForgotPassword`). El resto de pantallas se cubre por E2E; para medirlas, amplía `coverage.include` en `vite.config.js`.

## Regla de trinquete

Umbral de la semana = **mayor** entre el piso del plan y la cobertura real de la semana anterior (redondeada hacia abajo). **Nunca baja.**

| Semana | Piso del plan | Frontend real | Backend real | Umbral front / back |
|---|:---:|:---:|:---:|:---:|
| S1 | línea base | 0 % | 44 % | 0 / 44 |
| S2 | 30 % | 10 % | 53 % | 10 / 53 |
| S3 | 40 % | 95 % | 53 % | 95 / 53 |
| S4 | 50 % | 95 % | 91 % | 95 / 90 |

> **S2, frontend**: el piso del plan (30 %) no es alcanzable con solo pruebas unitarias porque el alcance incluye `Login.jsx` (≈550 líneas de JSX), `ForgotPassword.jsx` y `TwoFactor.jsx`, que se prueban en la semana 3. El umbral se fija en la cobertura real (10 %) y sube en la semana 3.

> **S3, frontend**: sube a 95 % porque el alcance es deliberadamente pequeño (5 módulos). Es una métrica del flujo de autenticación, no de toda la SPA.
