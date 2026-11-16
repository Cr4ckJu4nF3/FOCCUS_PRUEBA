# Cobertura y regla de trinquete

La cobertura se mide con el **mismo comando de test de siempre** y falla si baja del umbral.

| Capa | Comando (desde la carpeta) | Configuración |
|---|---|---|
| Backend | `backend/api_usuarios` → `pytest` | `pytest.ini` + `.coveragerc` (`fail_under`) |
| Frontend | `frontend` → `npm test` | `vite.config.js` → `test.coverage.thresholds` |

## Qué se mide (y qué no)

- **Backend**: todo `app/` salvo `app/main.py` y `app/config/database.py` (arranque y conexión: se ejercitan en integración, semana 6).
- **Frontend**: `api.js`, `utils/`, `componentes/` y las pantallas del flujo de autenticación (`ProtectedRoute`, `Login`, `TwoFactor`, `ForgotPassword`). El resto de pantallas se cubre por E2E; para medirlas, amplía `coverage.include` en `vite.config.js`.

## Regla de trinquete

Umbral de la semana = **mayor** entre el piso del plan y la cobertura real de la semana anterior (redondeada hacia abajo). **Nunca baja.**

| Semana | Piso del plan | Frontend real | Backend real | Umbral front / back |
|---|:---:|:---:|:---:|:---:|
| S1 | línea base | 0 % | 44 % | 0 / 44 |
