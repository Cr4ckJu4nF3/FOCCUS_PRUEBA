// Pantalla de verificación en dos pasos (/verificacion).
export class VerificacionPage {
  constructor(page) {
    this.page = page;
    this.code = page.getByLabel('Código de Verificación');
    this.verify = page.getByRole('button', { name: 'Verificar' });
    this.resend = page.getByRole('button', { name: 'Reenviar código' });
    this.alert = page.getByRole('alert');
    this.status = page.getByRole('status');
  }

  async submitCode(code) {
    await this.code.fill(code);
    await this.verify.click();
  }
}
