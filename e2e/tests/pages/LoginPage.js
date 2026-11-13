import { expect } from '@playwright/test';

// Page Object de /login: sabe CÓMO se usa la pantalla; las aserciones quedan en cada test.
export class LoginPage {
  constructor(page) {
    this.page = page;
    this.email = page.getByLabel('E-mail');
    this.password = page.getByLabel('Contraseña', { exact: true });
    this.submit = page.getByRole('button', { name: 'Ingresar' });
    this.registerTab = page.getByRole('tab', { name: 'Registrar' });
    this.alert = page.getByRole('alert');
    this.status = page.getByRole('status');
    this.forgotPassword = page.getByRole('button', { name: /olvidaste tu contraseña/i });
  }

  async goto() {
    await this.page.goto('/login');
    await expect(this.submit).toBeVisible();
  }

  async login(mail, password) {
    await this.email.fill(mail);
    await this.password.fill(password);
    await this.submit.click();
  }
}
