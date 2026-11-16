# Hallazgos de las pruebas

Defectos y riesgos que salieron al escribir los tests. Estado: ✅ corregido · 🔒 documentado con un test `xfail` (la suite sigue en verde y el test pasará a verde cuando se corrija) · 📝 anotado.

## Frontend

| ID | Semana | Hallazgo | Estado |
|---|:---:|---|:---:|
| H-F01 | 1 | Las `<label>` de Login no estaban asociadas a su `<input>` (sin `htmlFor`/`id`): `getByLabel` de Playwright no las encontraba y un lector de pantalla tampoco las anunciaba. Los mensajes de error/éxito no tenían `role`. | ✅ `Login.jsx` |
| H-F02 | 2 | `componentes/Carruselista.jsx` no se importa en ningún lado y referencia imágenes que no existen (`claqueta.jpg`, `elementos.jpeg`, `rodaje.png`). Si alguien lo usa, el build falla. | 📝 |
| H-F03 | 2 | `validarContrasena` estaba copiada tres veces (Login, ForgotPassword, Profile). | ✅ `utils/validarContrasena.js` |
