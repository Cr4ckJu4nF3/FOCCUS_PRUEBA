import { test, expect } from './fixtures.js';
import { LoginPage } from './pages/LoginPage.js';
import { uniqueUser } from './support.js';

test.describe('Inicio de sesión', () => {
  test('should show an error when the password is wrong', async ({ page, usuario }) => {
    const login = new LoginPage(page);
    await login.goto();

    await login.login(usuario.mail, 'Incorrecta#1');

    // el backend responde 200 con success:false y el front muestra el mensaje
    await expect(login.alert).toHaveText('Contraseña incorrecta');
    await expect(page).toHaveURL(/\/login$/);
  });

  test('should show an error when the email is not registered', async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();

    await login.login(uniqueUser('fantasma').mail, 'Cualquiera#1');

    await expect(login.alert).toHaveText('Correo no registrado');
  });

  test('should accept the email in uppercase and with surrounding spaces', async ({ page, usuario }) => {
    await page.route('**/users/2fa/send', (route) => route.fulfill({ json: { success: true } }));
    const login = new LoginPage(page);
    await login.goto();

    await login.login(`  ${usuario.mail.toUpperCase()} `, usuario.contrasena);

    await expect(page).toHaveURL(/\/verificacion$/);
  });

  test('should hide the password until the eye button is pressed', async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.password.fill('Secreta#1');

    await expect(login.password).toHaveAttribute('type', 'password');
    await page.getByRole('button', { name: 'Mostrar contraseña' }).click();
    await expect(login.password).toHaveAttribute('type', 'text');
  });

  test('should open the password recovery page from the login', async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();

    await login.forgotPassword.click();

    await expect(page).toHaveURL(/\/recuperar-acceso$/);
  });
});
