# Hallazgos de las pruebas

Defectos y riesgos que salieron al escribir los tests. Estado: ✅ corregido · 🔒 documentado con un test `xfail` (la suite sigue en verde y el test pasará a verde cuando se corrija) · 📝 anotado.

## Frontend

| ID | Semana | Hallazgo | Estado |
|---|:---:|---|:---:|
| H-F01 | 1 | Las `<label>` de Login no estaban asociadas a su `<input>` (sin `htmlFor`/`id`): `getByLabel` de Playwright no las encontraba y un lector de pantalla tampoco las anunciaba. Los mensajes de error/éxito no tenían `role`. | ✅ `Login.jsx` |
| H-F02 | 2 | `componentes/Carruselista.jsx` y `componentes/Menu.jsx` no se importan en ningún lado. Carruselista referencia imágenes que no existen (`claqueta.jpg`, `elementos.jpeg`, `rodaje.png`) y Menu es la plantilla sin modificar de React-Bootstrap. Si alguien los usa, el build falla o aparece texto de ejemplo. Fuera del alcance de cobertura. | 📝 |
| H-F03 | 2 | `validarContrasena` estaba copiada tres veces (Login, ForgotPassword, Profile). | ✅ `utils/validarContrasena.js` |
| H-F04 | 3 | Los botones de mostrar/ocultar contraseña solo tenían un icono: sin nombre accesible (lector de pantalla y Testing Library no podían encontrarlos). | ✅ `aria-label` en Login y ForgotPassword |
| H-F05 | 3 | En Login, la pestaña «Ingresar» y el botón de envío «Ingresar» tenían el mismo nombre y las pestañas no eran `role="tab"`. | ✅ `role="tablist"/"tab"` + `aria-selected` |
| H-F06 | 3 | ForgotPassword/TwoFactor: etiquetas desasociadas y errores sin `role="alert"` (igual que H-F01). | ✅ |
| H-F08 | 5 | Cualquier fallo de `fetch` o de lectura del JSON muestra «No se pudo conectar con el servidor», también cuando el servidor sí respondió (p. ej. un 500 en texto plano). Engañoso para soporte. | 📝 |
| H-F09 | 7 | `index.css`: los `@import` de Google Fonts (Montserrat, Courier Prime) quedan **después** del `@import "tailwindcss"` (que se expande a capas). Los navegadores ignoran un `@import` que no va primero: las fuentes nunca se cargan. Vite lo avisa en cada arranque («@import must precede all other statements»). | 📝 |
| H-F10 | 7 | `ProjectSelection`: como el backend responde HTTP 200 con `success:false` ante errores de negocio, `handleCreateProject` lo toma por éxito: cierra el modal y navega al dashboard con `projectId` indefinido. Consecuencia directa de H-B18. | 🔒 `ProjectSelection.test.jsx` (`it.fails`) |
| H-F11 | 7 | `ProjectSelection` repite el error en dos sitios (banner de página y modal) con `role="alert"`: con el modal abierto hay dos alertas. | 📝 |
| H-F12 | 8 | El botón «X» que cierra el modal «Crear Proyecto» solo tenía un icono: sin nombre accesible. | ✅ `aria-label="Cerrar"` |
| H-F07 | 3 | `ForgotPassword` llama a `fetch` directo y no a `apiFetch`: no comparte el manejo de 401 ni el header de autorización. | 📝 |

## Backend

Los marcados 🔒 están en `backend/api_usuarios/tests/api/test_known_defects_api.py` como `xfail(strict=True)`: la suite está en verde hoy y el test **falla** el día que el defecto se corrija, para que se quite la marca.

### Seguridad

| ID | Sem | Hallazgo | Estado |
|---|:---:|---|:---:|
| H-B01 | 4 | `/users/login` devuelve un `access_token` válido **antes** del 2FA. Quien conozca la contraseña llama a la API directamente y nunca verifica el código; el 2FA solo se aplica en la interfaz. | 🔒 |
| H-B02 | 4 | `PATCH /users/{id}` solo exige estar autenticado: un usuario puede ponerse `id_rol: 1001` (administrador). | 🔒 |
| H-B03 | 4 | Misma ruta (y `PUT`): cualquier usuario edita (correo, contraseña) a cualquier otro. | 🔒 |
| H-B04 | 4 | `POST /users/invite` no exige administrador y toma `id_rol` (y `id_client`) del cuerpo: se puede invitar a alguien como administrador de cualquier proyecto. | 🔒 |
| H-B05 | 4 | `POST /projects/create` toma `id_user` del cuerpo y lo vincula como administrador (1001): se puede dar acceso de admin a otro usuario. | 🔒 |
| H-B06 / H-B07 | 4 | No hay aislamiento entre empresas: cualquier usuario autenticado lee usuarios y proyectos de otras empresas por id. | 🔒 |
| H-B08 | 4 | `/register` devuelve en `error` la sentencia SQL completa **con el hash bcrypt** cuando el INSERT falla. | 🔒 |
| H-B19 | 4 | Códigos 2FA, de recuperación y contraseñas temporales usan `random` (predecible) en lugar de `secrets`. | 📝 |
| H-B20 | 4 | Sin límite de intentos para el código 2FA/recuperación (6 dígitos, 10 min). `verified_devices` se llena pero nunca se consulta: `/users/2fa/check` siempre exige verificación. | 📝 |
| H-B21 | 4 | `POST /contact` es público y sin límite de frecuencia ni captcha: permite enviar correo masivo a `CONTACT_EMAIL`. | 📝 |

### Errores y validación

| ID | Sem | Hallazgo | Estado |
|---|:---:|---|:---:|
| H-B09 | 4 | `telephone` es opcional en `RegisterSchema` y en el formulario, pero `NOT NULL` en `clients`: registrar sin teléfono falla. | 🔒 |
| H-B10 | 4 | El chequeo de empresa duplicada no normaliza el correo. **Latente**: en MySQL (`utf8mb4_general_ci`) la comparación ignora mayúsculas y el defecto no se manifiesta (confirmado en `integration/TestCollation`); aparecería al cambiar de motor o de collation. | 🔒 |
| H-B11 | 4 | `POST /users` compara el correo sin `strip().lower()`; un duplicado con espacios o mayúsculas llega al INSERT y da 500. | 🔒 |
| H-B12 | 4 | `POST /clients` sin teléfono da 500 (mismo desajuste schema/tabla). | 🔒 |
| H-B13 | 4 | `verify_2fa_code` asume que el usuario existe: si se borró tras pedir el código, 500. | 🔒 |
| H-B14 | 4 | `POST /guiones` no valida que el proyecto exista: la FK revienta con 500. | 🔒 |
| H-B15 | 4 | Importar un plan de rodaje con una fecha imposible (31 de febrero) crea un día con `fecha_inicio = NULL` y da 500. | 🔒 |
| H-B18 | 4 | Contrato: los errores de negocio responden **HTTP 200** con `success:false`. Los clientes HTTP, caches y monitoreo no los distinguen de un éxito. Los tests actuales lo documentan. | 📝 |

### Lógica de negocio y código

| ID | Sem | Hallazgo | Estado |
|---|:---:|---|:---:|
| H-B16 | 4 | `numero_de_escena` es texto y se ordena alfabéticamente: la escena 10 aparece antes que la 2 (afecta lista de escenas, desglose y escenas disponibles). | 🔒 |
| H-B17 | 4 | El siguiente `id_project` se calcula con orden alfabético: tras `proj9999`/`proj10000` se repite el id. | 🔒 |
| H-B22 | 4 | `project_controller.py` define `create_project` y `create_project_and_link` dos veces (la segunda pisa a la primera); `ProjectSchema` también está duplicada en `project_schema.py`. Código muerto que confunde. | 📝 |
| H-B24 | 5 | Los campos del formulario público de contacto se insertan **sin escapar** en el HTML del correo a soporte (inyección de HTML/phishing). Probado con el SMTP simulado. | 🔒 `tests/doubles/test_mail_doubles.py` |
| H-B25 | 6 (parcial en 10) | **`project_name` corregido en la semana 10** (422, ver `tdd-nombre-de-proyecto.md`); el resto sigue abierto. La API no valida longitudes y MySQL en modo estricto rechaza el texto largo con un **500** (SQLite lo aceptaba, por eso las pruebas de API no lo vieron). Afecta `project_name` (45), `razon_social` (50), `roles.nombre` (50) y otros `String(n)`. El frontend tampoco limita lo que se escribe: un título de proyecto de 46 caracteres rompe. | 🔒 `integration/` |
| H-B26 | 6 | `escenas.id_desglose → desglose` tiene `ON DELETE CASCADE` en sentido inverso: borrar una escena (o un guion/proyecto) deja huérfanos `desglose` y `desglose_requerimientos`; y borrar un desglose borraría sus escenas. | 🔒 `integration/` |
| H-B27 | 8 | `POST /users/invite`: si el alta de un correo falla en `flush()` (p. ej. identificador temporal duplicado) la sesión queda con la transacción anulada y **todos los correos siguientes fallan** con `PendingRollbackError`; el `except` por correo no hace `rollback()`. | 🔒 `test_branches_api.py` |
| H-B28 | 8 | La lógica «siguiente id» (`esc0001`, `proj0001`, `rod0001`, `psj0001`, `loc0001`, `req0001`, `dsg0001`) está copiada en 8 sitios (una de ellas, `_generar_id_escena_local`, duplica la de `escena_controller`). Todas caen a `0001` si el último id no es numérico, lo que **repetiría** un id existente; y calcular el máximo con orden alfabético es la causa de H-B17. | 📝 |
| H-B23 | 4 | `DEPARTAMENTOS_DESGLOSE` existe pero no se usa: un requerimiento acepta cualquier texto como departamento. | 📝 |
