import { test as base, expect } from '@playwright/test';
import { API_URL, registerUserViaApi, uniqueUser, VALID_PASSWORD } from './support.js';

async function loginViaApi(request, mail, password) {
  const response = await request.post(`${API_URL}/users/login`, { data: { mail, contrasena: password } });
  const body = await response.json();
  if (!body.success) throw new Error(`Login de preparación falló: ${body.message}`);
  return body.data;
}

// Escribe en localStorage la misma sesión que deja el formulario de login.
// addInitScript corre en CADA carga de página: la marca en sessionStorage hace que la
// sesión se siembre una sola vez por pestaña, así un cierre de sesión o un 401 no se deshacen.
function sessionScript(data) {
  return (d) => {
    if (sessionStorage.getItem('__e2e_sesion_sembrada')) return;
    sessionStorage.setItem('__e2e_sesion_sembrada', '1');
    localStorage.setItem('access_token', d.access_token);
    localStorage.setItem('id_user', d.id_user);
    localStorage.setItem('nombre', d.nombre);
    localStorage.setItem('apellido', d.apellido);
    localStorage.setItem('mail', d.mail);
    localStorage.setItem('id_rol', d.id_rol);
    localStorage.setItem('id_client', d.id_client);
  };
}

/**
 * Fixtures compartidas.
 *  - usuario:        empresa + administrador creados por API (Arrange sin pasar por la interfaz)
 *  - iniciarSesion:  deja a una persona "ya logueada" antes de abrir la página
 *  - crearMiembro:   usuario sin rol de administrador, creado por un admin
 */
export const test = base.extend({
  usuario: async ({ request }, use) => {
    await use(await registerUserViaApi(request, uniqueUser('fx')));
  },

  iniciarSesion: async ({ page, request }, use) => {
    await use(async (mail, password = VALID_PASSWORD) => {
      const data = await loginViaApi(request, mail, password);
      await page.context().addInitScript(sessionScript(data), data);
      return data;
    });
  },

  crearMiembro: async ({ request }, use) => {
    await use(async (admin) => {
      const sesion = await loginViaApi(request, admin.mail, admin.contrasena);
      const sufijo = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
      const miembro = {
        nombre: 'Marta', apellido: 'Miembro', identificacion: 'CC', id_identificacion: `m${sufijo}`,
        mail: `miembro.${sufijo}@foccus.test`, msisdn: '3000000000', direccion: 'Calle 3',
        fecha_de_nacimiento: '1995-01-01T00:00:00', estado: 'activo', contrasena: VALID_PASSWORD,
        id_departamento: 'ARTE', id_project: 'proj0001', id_rol: 1005,
      };
      const response = await request.post(`${API_URL}/users`, {
        data: miembro,
        headers: { Authorization: `Bearer ${sesion.access_token}` },
      });
      const body = await response.json();
      if (!body.success) throw new Error(`No se pudo crear el miembro: ${body.message}`);
      return { ...miembro };
    });
  },
});

export { expect };
