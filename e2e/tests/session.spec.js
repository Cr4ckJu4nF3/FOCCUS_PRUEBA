import { test, expect } from './fixtures.js';
import { API_URL } from './support.js';

const base64 = (obj) => Buffer.from(JSON.stringify(obj)).toString('base64');
const jwtFalso = (payload) => `cabecera.${base64(payload)}.firma`;
const enUnaHora = () => Math.floor(Date.now() / 1000) + 3600;

test.describe('Protección de rutas y sesión', () => {
  test('should send a visitor without session to the home page', async ({ page }) => {
    await page.goto('/seleccion-proyecto');

    await expect(page).toHaveURL(/localhost:\d+\/$/);
  });

  test('should send a person with an expired token to the home page', async ({ page }) => {
    await page.addInitScript(
      (token) => localStorage.setItem('access_token', token),
      jwtFalso({ id_user: 1, exp: 1 }),
    );

    await page.goto('/dashboard');

    await expect(page).toHaveURL(/localhost:\d+\/$/);
  });

  test('should open the private page when the session is valid', async ({ page, usuario, iniciarSesion }) => {
    await iniciarSesion(usuario.mail);

    await page.goto('/seleccion-proyecto');

    await expect(page.getByRole('heading', { name: 'Gestión de Proyectos' })).toBeVisible();
  });

  test('should clear the session and go home when the backend rejects the token with 401', async ({ page }) => {
    // El frontend cree que el token sirve (no ha vencido) pero la firma es falsa: el backend responde 401
    await page.addInitScript((token) => {
      if (sessionStorage.getItem('__e2e_sesion_sembrada')) return; // una sola vez por pestaña
      sessionStorage.setItem('__e2e_sesion_sembrada', '1');
      localStorage.setItem('access_token', token);
      localStorage.setItem('id_user', '1');
      localStorage.setItem('id_rol', '1001');
    }, jwtFalso({ id_user: 1, id_rol: 1001, exp: enUnaHora() }));

    await page.goto('/seleccion-proyecto');
    await page.getByRole('button', { name: /Escoger Proyecto/ }).click();

    await expect(page).toHaveURL(/localhost:\d+\/$/);
    expect(await page.evaluate(() => localStorage.getItem('access_token'))).toBeNull();
  });

  test('should end the session with the logout button', async ({ page, usuario, iniciarSesion }) => {
    await iniciarSesion(usuario.mail);
    await page.goto('/seleccion-proyecto');

    await page.getByRole('button', { name: 'Cerrar sesión' }).click();

    await expect(page).toHaveURL(/localhost:\d+\/$/);
    expect(await page.evaluate(() => localStorage.getItem('access_token'))).toBeNull();
    // y volver atrás no reabre el área privada
    await page.goto('/seleccion-proyecto');
    await expect(page).toHaveURL(/localhost:\d+\/$/);
  });

  test('the API itself rejects a request without token', async ({ request }) => {
    const response = await request.get(`${API_URL}/users`);

    expect(response.status()).toBe(401);
  });
});
