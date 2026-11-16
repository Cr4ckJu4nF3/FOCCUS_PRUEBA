import { defineConfig, devices } from '@playwright/test';

// Puerto del frontend. Cámbialo con FRONT_PORT si el 5173 ya está ocupado
// (si otro proyecto usa ese puerto, los tests abrirían ESE proyecto).
const port = Number(process.env.FRONT_PORT ?? 5173);

export default defineConfig({
  testDir: './tests',
  // Un test no debe depender de otro: pueden correr en paralelo.
  fullyParallel: true,
  use: {
    baseURL: `http://localhost:${port}`,
    // La traza se guarda solo cuando un test falla y se reintenta: "npm run report"
    trace: 'on-first-retry',
  },
  reporter: [['list'], ['html', { open: 'never' }]],
  retries: process.env.CI ? 1 : 0,
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Opcional: usar un Chromium ya instalado (p. ej. donde no se pueda descargar el de Playwright)
        ...(process.env.CHROMIUM_PATH && {
          launchOptions: {
            executablePath: process.env.CHROMIUM_PATH,
            args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
          },
        }),
      },
    },
  ],
  // Playwright levanta el frontend. El backend (y su BD de PRUEBAS) los levantas tú
  // antes: ver e2e/README.md. api.js apunta a http://127.0.0.1:8000.
  webServer: {
    command: `node node_modules/vite/bin/vite.js --port ${port} --strictPort`,
    cwd: '../frontend',
    url: `http://localhost:${port}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
