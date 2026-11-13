import { test, expect } from './fixtures.js';
import { RegistroPage } from './pages/RegistroPage.js';
import { registerUserViaApi, uniqueUser } from './support.js';

test.describe('Registro de empresa y usuario', () => {
  test('should not leave step 1 while the required fields are empty', async ({ page }) => {
    const registro = new RegistroPage(page);
    await registro.open();

    await registro.continuar.click();

    await expect(page.getByText('Paso 1 de 3')).toBeVisible();
  });

  test('should show an error when the two passwords do not match', async ({ page }) => {
    const registro = new RegistroPage(page);
    await registro.untilSecurityStep(uniqueUser('mismatch'));

    await registro.fillSecurity('Foccus#2026', 'Distinta#2026');
    await registro.crearCuenta.click();

    // validación del front, no llega al backend
    await expect(registro.alert).toHaveText('Las contraseñas no coinciden');
  });

  test('should list the missing rules when the password is weak', async ({ page }) => {
    const registro = new RegistroPage(page);
    await registro.untilSecurityStep(uniqueUser('weak'));

    await registro.fillSecurity('abc');
    await registro.crearCuenta.click();

    await expect(registro.alert).toContainText('Mínimo 8 caracteres');
  });

  test('should require accepting the terms', async ({ page }) => {
    const registro = new RegistroPage(page);
    await registro.untilSecurityStep(uniqueUser('terms'));

    await registro.fillSecurity('Foccus#2026', 'Foccus#2026', { acceptTerms: false });
    await registro.crearCuenta.click();

    await expect(registro.alert).toHaveText('Debes aceptar los términos y condiciones');
  });

  test('should confirm the registration and go back to the login tab with the email filled', async ({ page }) => {
    const user = uniqueUser('registro');
    const registro = new RegistroPage(page);
    await registro.untilSecurityStep(user);

    await registro.fillSecurity(user.contrasena);
    await registro.crearCuenta.click();

    await expect(registro.status).toContainText('Registro completado');
    await expect(registro.email).toHaveValue(user.mail);
  });

  test('should show the backend message when the company is already registered', async ({ page, request }) => {
    const existente = await registerUserViaApi(request, uniqueUser('dup'));
    const repetido = { ...uniqueUser('dup2'), email_empresa: existente.email_empresa };
    const registro = new RegistroPage(page);
    await registro.untilSecurityStep(repetido);

    await registro.fillSecurity(repetido.contrasena);
    await registro.crearCuenta.click();

    await expect(registro.alert).toBeVisible();
    await expect(registro.status).toHaveCount(0);
  });
});
