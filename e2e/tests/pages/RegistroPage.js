import { LoginPage } from './LoginPage.js';

// Formulario de registro de empresa + usuario (3 pasos dentro de /login).
export class RegistroPage extends LoginPage {
  constructor(page) {
    super(page);
    this.continuar = page.getByRole('button', { name: 'Continuar' });
    this.crearCuenta = page.getByRole('button', { name: 'Crear cuenta' });
    this.confirmPassword = page.getByLabel('Confirmar Contraseña');
    this.terms = page.getByRole('checkbox');
  }

  async open() {
    await this.goto();
    await this.registerTab.click();
  }

  async fillCompany(u) {
    await this.page.getByLabel('Razón Social').fill(u.razon_social);
    await this.page.getByLabel('Representante Legal').fill(u.representante_legal);
    await this.page.getByLabel('Documento', { exact: true }).selectOption(u.document);
    await this.page.getByLabel('Nº Documento').fill(u.id_document);
    await this.page.getByLabel('Email Empresa').fill(u.email_empresa);
    await this.continuar.click();
  }

  async fillUser(u) {
    await this.page.getByLabel('Nombres').fill(u.nombre);
    await this.page.getByLabel('Apellidos').fill(u.apellido);
    await this.page.getByLabel('Email Personal').fill(u.mail);
    await this.page.getByLabel('Celular', { exact: true }).fill(u.msisdn);
    await this.continuar.click();
  }

  async fillSecurity(password, confirm = password, { acceptTerms = true } = {}) {
    await this.password.fill(password);
    await this.confirmPassword.fill(confirm);
    if (acceptTerms) await this.terms.check();
  }

  async untilSecurityStep(user) {
    await this.open();
    await this.fillCompany(user);
    await this.fillUser(user);
  }
}
