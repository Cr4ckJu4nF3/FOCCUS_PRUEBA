# Estrategia de pruebas — FOCCUS_PRUEBA

**Integrantes**: Camilo (Aerxs666) y Juan (Cr4ckJu4nF3) · **Stack**: React 19 (Vite) + FastAPI + MySQL/MariaDB · **Fecha**: 2026-11-13
_FOCCUS_PRUEBA es el espacio donde se prueban cosas antes de llevarlas a FOCCUS; esta estrategia se escribió contra el código que hay aquí._

## 1. Qué hace la app y qué no puede fallar

Gestiona la continuidad de producciones audiovisuales: empresas, proyectos con roles, guiones versionados, escenas, desglose y plan de rodaje.

| Riesgo | Por qué importa |
|---|---|
| Entrar a una cuenta ajena o escalar de rol | Un usuario vería o editaría guiones de otra productora (material confidencial) |
| Perder o duplicar datos al borrar/importar | Un desglose o plan de rodaje importado mal obliga a rehacer semanas de trabajo |
| No poder iniciar sesión (login, 2FA, recuperar contraseña) | Nadie del equipo de rodaje puede trabajar |
| El orden y los números de escena | Un rodaje con la escena 10 antes que la 2 genera errores en set |

## 2. Qué prueba cada capa y por qué

| Capa | Qué verifica | Herramienta | Tests |
|---|---|---|---|
| Unitarias | JWT y roles, parser de PDFs, schemas, archivos; reglas de contraseña y sesión del navegador | pytest · Vitest | 87 + 42 |
| Componentes React | Login (ingreso y registro en 3 pasos), 2FA, recuperación, selección y creación de proyecto, ruta protegida | Vitest + Testing Library | 91 |
| API | Contrato HTTP de **todas** las rutas, incluida una matriz de acceso (pública/autenticada/admin) | pytest + TestClient + SQLite | 426 |
| Dobles | SMTP, extractor de PDF, reloj; `apiFetch` y Login contra un servidor simulado | pytest-mock · MSW | 40 + 15 |
| Integración con BD | Collation, límites de columna, cascadas, LONGTEXT, transacciones en MariaDB real | pytest + MariaDB 10.11 | 23 |
| E2E | 31 flujos en Chromium: login, registro, 2FA, sesión/401/logout, proyectos admin vs miembro, recuperación | Playwright | 31 |
| **Total** | | | **756** (+ 24 defectos documentados como fallo esperado; incluye 1 smoke test) |

**Por qué esta forma**: la lógica de negocio vive en los controladores de FastAPI (no hay capa de servicios), así que la capa más gruesa es la de **API**: ahí se verifican permisos, validaciones y reglas, rápido y sin navegador. Las unitarias se reservan para lo que es lógica pura (parser, JWT). La integración es pequeña pero indispensable: reveló tres defectos que SQLite oculta (H-B10, H-B25, H-B26). El E2E es deliberadamente corto porque cada flujo cuesta segundos y depende de tres procesos.

## 3. Qué no se prueba y por qué

| Fuera de la suite o de la cobertura | Motivo |
|---|---|
| Pantallas `Guion`, `Escena`, `Rodaje`, `Desglose`, `Roles`, `Profile`, `Landing`, `ProjectDashboard`, `ProjectRegistration` (≈ 4 800 de 6 400 líneas de frontend) | Alcance medido = flujo de autenticación y selección de proyecto (1 621 líneas, **25 %**). El 100 % de cobertura es de **ese** alcance, no de toda la SPA |
| Envío real de correo (SMTP/Gmail) | Depende de un tercero; se prueba el contenido y el protocolo con un SMTP simulado |
| Diseño visual, CSS, responsive | Ninguna prueba de comportamiento lo detecta (p. ej. H-F09, fuentes que no cargan) |
| Rendimiento, carga, seguridad ofensiva | Fuera del bootcamp; los hallazgos de seguridad vienen de pruebas funcionales |
| Railway / producción | Las pruebas nunca tocan la BD de desarrollo ni la de la nube |

## 4. Datos y entornos

- **BD**: SQLite en memoria para API (esquema recreado en cada test, claves foráneas activas); MariaDB 10.11 para integración y E2E (`docker-compose.test.yml`, tablas vaciadas en cada test; se niega a correr si la BD no se llama `*test*`).
- **Dobles**: SMTP, extractor de PDF y reloj. **Reales**: JWT, bcrypt, SQLAlchemy y el backend completo en E2E.
- **E2E**: el *Arrange* se hace por API (usuario, sesión, miembro) y solo se intercepta el envío de correo (`page.route`).

## 5. CI y umbrales

Workflow `.github/workflows/tests.yml`: `frontend`, `backend`, `integracion` (MariaDB como servicio, falla si faltara la BD) y `e2e`. Cero tests saltados. Ver [ci.md](testing/ci.md). Checks obligatorios en el ruleset de `main`: `frontend`, `backend`, `integracion`, `e2e` (**configuración manual pendiente**, ver ci.md).

| Parte | Cobertura actual | Umbral configurado |
|---|---|---|
| Frontend (alcance de 7 módulos) | 100 % líneas · 100 % ramas | 100 / 99 / 100 / 100 |
| Backend (con ramas) | 99,02 % | 99 |

## 6. Hallazgos y riesgos conocidos

28 hallazgos de backend y 12 de frontend: [hallazgos.md](testing/hallazgos.md). Corregidos: 6 (5 de accesibilidad y la validación de contraseña duplicada). Abiertos con test de fallo esperado (`xfail(strict)` / `it.fails`):

| Defecto | Capa que lo encontró | Estado |
|---|---|---|
| H-B01 el token de login da acceso antes del 2FA | API | abierto (xfail) |
| H-B02 / H-B03 / H-B04 / H-B05 escalada de rol y edición ajena | API | abierto (xfail) |
| H-B08 `/register` filtra SQL y el hash de la contraseña | API | abierto (xfail) |
| H-B25 textos largos → 500 en MySQL estricto | Integración | abierto (xfail) |
| H-B26 desglose huérfano al borrar escenas | Integración | abierto (xfail) |
| H-B27 una invitación fallida rompe las siguientes | Ramas sin cubrir | abierto (xfail) |
| H-B16 la escena 10 se ordena antes que la 2 | API | abierto (xfail) |
| H-F10 un error de negocio (HTTP 200) se toma por éxito al crear proyecto | Componentes | abierto (`it.fails`) |

## 7. Evidencia individual

Capas por integrante: ver [matriz-rotacion.md](matriz-rotacion.md). Los commits de esta implementación (`test(semana-NN)`) se prepararon en una sola sesión; tras fusionarlos, `git shortlog -sn -- '*tests/*' '*.test.*' '*.spec.*' 'e2e/*'` mostrará la autoría real de cada quien.
