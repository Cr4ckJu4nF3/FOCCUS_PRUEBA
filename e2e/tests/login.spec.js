import { expect, test } from '@playwright/test';
import { registerUserViaApi, uniqueUser } from './support.js';

test.describe('Inicio de sesión', () => {
  test('should show an error when the password is wrong', async ({ page, request }) => {
    // Arrange: el usuario existe (se crea por API); el test prueba solo el login
    const user = await registerUserViaApi(request);
    await page.goto('/login');

    // Act
    await page.getByLabel('E-mail').fill(user.mail);
    await page.getByLabel('Contraseña').fill('Incorrecta#1');
    await page.locator('form').getByRole('button', { name: 'Ingresar' }).click();

    // Assert: el backend responde 200 con success:false y el front muestra el mensaje
    await expect(page.getByRole('alert')).toHaveText('Contraseña incorrecta');
    await expect(page).toHaveURL(/\/login$/);
  });

  test('should show an error when the email is not registered', async ({ page }) => {
    // Arrange
    const { mail } = uniqueUser('fantasma');
    await page.goto('/login');

    // Act
    await page.getByLabel('E-mail').fill(mail);
    await page.getByLabel('Contraseña').fill('Cualquiera#1');
    await page.locator('form').getByRole('button', { name: 'Ingresar' }).click();

    // Assert
    await expect(page.getByRole('alert')).toHaveText('Correo no registrado');
  });
});
