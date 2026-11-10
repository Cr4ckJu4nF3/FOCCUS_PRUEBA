# E2E con Playwright

Prueban FOCCUS_PRUEBA como lo usa una persona: navegador real, frontend y backend levantados.

## Requisitos

1. Una BD **de pruebas** (MySQL/MariaDB). No uses la de Railway ni la de desarrollo: los tests crean empresas y usuarios.
2. Backend en `http://127.0.0.1:8000` apuntando a esa BD:

   ```bash
   cd backend/api_usuarios
   DB_HOST=127.0.0.1 DB_PORT=3306 DB_USER=root DB_PASSWORD= DB_NAME=foccus_test \
     uvicorn app.main:app --port 8000
   ```
   En PowerShell define antes las variables: `$env:DB_NAME="foccus_test"`.
3. Dependencias (una sola vez):

   ```bash
   cd e2e && npm install && npx playwright install chromium
   cd ../frontend && npm install
   ```

## Ejecutar

```bash
cd e2e
npm test              # headless
npx playwright test --headed
npm run test:ui       # modo interactivo
npm run report        # reporte HTML con trazas
```

Playwright levanta el frontend solo (`webServer`). Si el 5173 está ocupado: `FRONT_PORT=5199 npm test`.

> El 2FA envía un correo real por Gmail. Los E2E que llegan a ese paso lo interceptan con `page.route` (ver semana 7); nunca dependen de SMTP.
