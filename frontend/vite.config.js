import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    globals: false,
    setupFiles: ['./tests/setup.js'],
    passWithNoTests: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      // Alcance de la cobertura: flujo de autenticación y utilidades. Las pantallas
      // grandes (guion, escenas, rodaje, desglose, roles, perfil, proyectos, landing)
      // se verifican por E2E; entran aquí cuando se les escriban tests de componente.
      // (src/componentes/ queda fuera: Menu y Carruselista no se usan, ver hallazgo H-F02)
      include: [
        'src/api.js',
        'src/utils/**',
        'src/screen/ProtectedRoute.jsx',
        'src/screen/Login.jsx',
        'src/screen/TwoFactor.jsx',
        'src/screen/ForgotPassword.jsx',
      ],

      // Umbral mínimo: si la cobertura baja de aquí, "npm test" falla.
      // Regla de trinquete: nunca baja (ver docs/testing/cobertura.md).
      thresholds: { lines: 98, branches: 90, functions: 89, statements: 97 },
    },
  },
})
