# Cobertura y regla de trinquete

La cobertura se mide con el **mismo comando de test de siempre** y falla si baja del umbral.

| Capa | Comando (desde la carpeta) | Configuración |
|---|---|---|
| Backend | `backend/api_usuarios` → `pytest` | `pytest.ini` + `.coveragerc` (`fail_under`) |
| Frontend | `frontend` → `npm test` | `vite.config.js` → `test.coverage.thresholds` |

## Qué se mide (y qué no)

- **Backend** (con cobertura de **ramas** desde S8): todo `app/` salvo `app/main.py` y `app/config/database.py` (arranque y conexión: se ejercitan en integración, semana 6).
- **Frontend**: `api.js`, `utils/` y las pantallas del flujo de autenticación (`ProtectedRoute`, `Login`, `TwoFactor`, `ForgotPassword`, `ProjectSelection`). El resto de pantallas se cubre por E2E; para medirlas, amplía `coverage.include` en `vite.config.js`.

## Regla de trinquete

Umbral de la semana = **mayor** entre el piso del plan y la cobertura real de la semana anterior (redondeada hacia abajo). **Nunca baja.**

| Semana | Piso del plan | Frontend real | Backend real | Umbral front / back |
|---|:---:|:---:|:---:|:---:|
| S1 | línea base | 0 % | 44 % | 0 / 44 |
| S2 | 30 % | 10 % | 53 % | 10 / 53 |
| S3 | 40 % | 95 % | 53 % | 95 / 53 |
| S4 | 50 % | 95 % | 91 % | 95 / 90 |
| S5 | 60 % | 98 % | 97 % | 98 / 97 |
| S6 | 70 % | 98 % | 97 % | 98 / 97 |
| S7 | 75 % | 99 % | 97 % | 99 / 97 |
| S8 | **80 %** | 100 % | 99 % | 100 / 99 |
| S9 | 80 % | 100 % | 99 % | 100 / 99 (sin cambios) |

> **S2, frontend**: el piso del plan (30 %) no es alcanzable con solo pruebas unitarias porque el alcance incluye `Login.jsx` (≈550 líneas de JSX), `ForgotPassword.jsx` y `TwoFactor.jsx`, que se prueban en la semana 3. El umbral se fija en la cobertura real (10 %) y sube en la semana 3.

> **S3, frontend**: sube a 95 % porque el alcance es deliberadamente pequeño (5 módulos). Es una métrica del flujo de autenticación, no de toda la SPA.

> **S6**: las pruebas de integración (BD real) verifican comportamiento, no suman líneas nuevas: la cobertura se mantiene.

> **S7**: `ProjectSelection.jsx` entra al alcance del frontend (sus tests de componente son además el contrato de selectores de los E2E).

> **S8**: se activa `branch = True` en el backend (mide también cada `if`/`else`, no solo líneas). Con ramas el backend cae de 97,4 % a 96,9 % y vuelve a 99,02 % tras analizar las ramas sin cubrir ([análisis](ramas-sin-cubrir.md)). Piso del plan (80 %) superado desde la S3 en ambas capas.
