import { test, expect } from './fixtures.js';
import { uniqueUser } from './support.js';

// Igual que el 2FA: el correo con el código es la única parte interceptada.
test.describe('Recuperación de contraseña', () => {
  test('should report an email that is not registered (real backend)', async ({ page }) => {
    await page.goto('/recuperar-acceso');

    await page.getByLabel('Correo Electrónico').fill(uniqueUser('nadie').mail);
    await page.getByRole('button', { name: 'Enviar Código' }).click();

    await expect(page.getByRole('alert')).toHaveText('Correo no registrado');
  });

  test('should move to the reset step when the code is sent', async ({ page, usuario }) => {
    await page.route('**/users/recover-password', (route) => route.fulfill({ json: { success: true } }));
    await page.goto('/recuperar-acceso');

    await page.getByLabel('Correo Electrónico').fill(usuario.mail);
    await page.getByRole('button', { name: 'Enviar Código' }).click();

    await expect(page.getByRole('heading', { name: 'Restablecer Contraseña' })).toBeVisible();
  });

  test('should reject a wrong code with the real backend', async ({ page, usuario }) => {
    await page.route('**/users/recover-password', (route) => route.fulfill({ json: { success: true } }));
    await page.goto('/recuperar-acceso');
    await page.getByLabel('Correo Electrónico').fill(usuario.mail);
    await page.getByRole('button', { name: 'Enviar Código' }).click();

    await page.getByLabel('Código de Verificación').fill('000000');
    await page.getByLabel('Nueva Contraseña', { exact: true }).fill('Nueva#2026x');
    await page.getByLabel('Confirmar Nueva Contraseña', { exact: true }).fill('Nueva#2026x');
    await page.getByRole('button', { name: 'Restablecer Contraseña' }).click();

    // el envío fue interceptado: el backend no tiene ninguna solicitud pendiente
    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Contraseña Restablecida' })).toHaveCount(0);
  });

  test('should validate the new password in the browser before calling the API', async ({ page, usuario }) => {
    await page.route('**/users/recover-password', (route) => route.fulfill({ json: { success: true } }));
    let llamadasAReset = 0;
    await page.route('**/users/reset-password', (route) => {
      llamadasAReset += 1;
      return route.fulfill({ json: { success: true } });
    });
    await page.goto('/recuperar-acceso');
    await page.getByLabel('Correo Electrónico').fill(usuario.mail);
    await page.getByRole('button', { name: 'Enviar Código' }).click();

    await page.getByLabel('Código de Verificación').fill('123456');
    await page.getByLabel('Nueva Contraseña', { exact: true }).fill('Nueva#2026x');
    await page.getByLabel('Confirmar Nueva Contraseña', { exact: true }).fill('Distinta#2026');
    await page.getByRole('button', { name: 'Restablecer Contraseña' }).click();

    await expect(page.getByRole('alert')).toHaveText('Las contraseñas no coinciden');
    expect(llamadasAReset).toBe(0);
  });
});
