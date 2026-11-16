import { test, expect } from './fixtures.js';
import { LoginPage } from './pages/LoginPage.js';
import { VerificacionPage } from './pages/VerificacionPage.js';

// El código 2FA solo existe en el correo del usuario (SMTP real). Los E2E interceptan
// SOLO las rutas que dependen del correo; el login y la validación de códigos van contra
// el backend de verdad.
const stubEnvioDeCodigo = (page) =>
  page.route('**/users/2fa/send', (route) => route.fulfill({ json: { success: true, message: 'Código enviado' } }));

async function loginHastaVerificacion(page, usuario) {
  await stubEnvioDeCodigo(page);
  const login = new LoginPage(page);
  await login.goto();
  await login.login(usuario.mail, usuario.contrasena);
  await expect(page).toHaveURL(/\/verificacion$/);
}

test.describe('Verificación en dos pasos', () => {
  test('should ask for the code after a valid login and show where it was sent', async ({ page, usuario }) => {
    await loginHastaVerificacion(page, usuario);

    await expect(page.getByText(usuario.mail)).toBeVisible();
  });

  test('should reject a code when none was requested (real backend)', async ({ page, usuario }) => {
    await loginHastaVerificacion(page, usuario);
    const verificacion = new VerificacionPage(page);

    await verificacion.submitCode('000000');

    // el envío fue interceptado, así que el backend no tiene un código pendiente
    await expect(verificacion.alert).toHaveText('No hay código de verificación pendiente');
    await expect(page).toHaveURL(/\/verificacion$/);
  });

  test('should continue to the project selection when the code is accepted', async ({ page, usuario }) => {
    await loginHastaVerificacion(page, usuario);
    await page.route('**/users/2fa/verify', (route) => route.fulfill({ json: { success: true, data: {} } }));
    const verificacion = new VerificacionPage(page);

    await verificacion.submitCode('123456');

    await expect(page).toHaveURL(/\/seleccion-proyecto$/);
  });

  test('should confirm that the code was sent again', async ({ page, usuario }) => {
    await loginHastaVerificacion(page, usuario);
    const verificacion = new VerificacionPage(page);

    await verificacion.resend.click();

    await expect(verificacion.status).toHaveText('Código reenviado exitosamente');
  });

  test('should only accept 6 characters in the code field', async ({ page, usuario }) => {
    await loginHastaVerificacion(page, usuario);
    const verificacion = new VerificacionPage(page);

    await verificacion.code.fill('123456789');

    await expect(verificacion.code).toHaveValue('123456');
  });
});
