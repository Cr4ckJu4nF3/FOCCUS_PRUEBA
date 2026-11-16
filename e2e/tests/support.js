// Ayudas compartidas por los E2E. Las aserciones se quedan en cada test.

// El frontend tiene la URL del API escrita en src/api.js (127.0.0.1:8000).
export const API_URL = process.env.API_URL ?? 'http://127.0.0.1:8000';

// Contraseña que cumple las reglas del formulario (8+, mayúscula, minúscula, número, símbolo).
export const VALID_PASSWORD = 'Foccus#2026';

// Datos únicos: la BD conserva lo que crean los tests entre ejecuciones y
// el correo y el documento son únicos en el backend.
export function uniqueUser(prefix = 'e2e') {
  const id = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  return {
    razon_social: `Productora ${prefix} ${id}`,
    representante_legal: 'Laura Test',
    email_empresa: `empresa.${prefix}.${id}@foccus.test`,
    address: 'Calle 1 # 2-3',
    telephone: '6010000',
    number_cellphone: '3000000000',
    document: 'NIT',
    id_document: id,
    nombre: 'Camila',
    apellido: 'Prueba',
    mail: `${prefix}.${id}@foccus.test`,
    msisdn: '3001112233',
    contrasena: VALID_PASSWORD,
  };
}

// Arrange por API: crea empresa + usuario sin pasar por la interfaz.
export async function registerUserViaApi(request, user = uniqueUser()) {
  const response = await request.post(`${API_URL}/register`, { data: user });
  const body = await response.json();
  if (!body.success) {
    throw new Error(`No se pudo preparar el usuario de prueba: ${body.message} (${body.error})`);
  }
  return user;
}
