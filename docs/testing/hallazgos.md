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
| H-F07 | 3 | `ForgotPassword` llama a `fetch` directo y no a `apiFetch`: no comparte el manejo de 401 ni el header de autorización. | 📝 |
