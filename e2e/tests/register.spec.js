import { expect, test } from '@playwright/test';
import { uniqueUser, VALID_PASSWORD } from './support.js';

// Recorre los 3 pasos del formulario de registro hasta la pantalla de seguridad.
async function fillRegistrationUntilSecurityStep(page, user) {
  await page.goto('/login');
  await page.getByRole('tab', { name: 'Registrar' }).click();

  // Paso 1: empresa
  await page.getByLabel('Razón Social').fill(user.razon_social);
  await page.getByLabel('Representante Legal').fill(user.representante_legal);
  await page.getByLabel('Documento', { exact: true }).selectOption(user.document);
  await page.getByLabel('Nº Documento').fill(user.id_document);
  await page.getByLabel('Email Empresa').fill(user.email_empresa);
  await page.getByRole('button', { name: 'Continuar' }).click();

  // Paso 2: usuario
  await page.getByLabel('Nombres').fill(user.nombre);
  await page.getByLabel('Apellidos').fill(user.apellido);
  await page.getByLabel('Email Personal').fill(user.mail);
  await page.getByLabel('Celular', { exact: true }).fill(user.msisdn);
  await page.getByRole('button', { name: 'Continuar' }).click();
}

test.describe('Registro de empresa y usuario', () => {
  test('should show an error when the two passwords do not match', async ({ page }) => {
    // Arrange
    const user = uniqueUser('mismatch');
    await fillRegistrationUntilSecurityStep(page, user);

    // Act
    await page.getByLabel('Contraseña', { exact: true }).fill(VALID_PASSWORD);
    await page.getByLabel('Confirmar Contraseña').fill('Distinta#2026');
    await page.getByRole('button', { name: 'Crear cuenta' }).click();

    // Assert: validación del front, no llega al backend
    await expect(page.getByRole('alert')).toHaveText('Las contraseñas no coinciden');
  });

  test('should confirm the registration and go back to the login tab', async ({ page }) => {
    // Arrange
    const user = uniqueUser('registro');
    await fillRegistrationUntilSecurityStep(page, user);

    // Act
    await page.getByLabel('Contraseña', { exact: true }).fill(user.contrasena);
    await page.getByLabel('Confirmar Contraseña').fill(user.contrasena);
    await page.getByRole('checkbox').check();
    await page.getByRole('button', { name: 'Crear cuenta' }).click();

    // Assert
    await expect(page.getByRole('status')).toContainText('Registro completado');
    await expect(page.getByLabel('E-mail')).toHaveValue(user.mail);
  });
});
