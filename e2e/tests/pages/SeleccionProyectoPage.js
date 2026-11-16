// Pantalla posterior al login (/seleccion-proyecto).
export class SeleccionProyectoPage {
  constructor(page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: 'Gestión de Proyectos' });
    this.chooseButton = page.getByRole('button', { name: /Escoger Proyecto/ });
    // .first(): con el modal abierto también existe el botón de envío «Crear Proyecto»
    this.createButton = page.getByRole('button', { name: /Crear Proyecto/ }).first();
    this.logout = page.getByRole('button', { name: 'Cerrar sesión' });
    // modal «Crear Proyecto»
    this.name = page.getByLabel('Nombre del Proyecto');
    this.format = page.getByLabel('Formato');
    this.genre = page.getByLabel('Género');
    this.synopsis = page.getByLabel('Sinopsis');
    this.director = page.getByLabel('Director');
    // exact: la tarjeta «Crear Proyecto Registrar un nuevo proyecto» no coincide, solo el botón de envío
    this.submitCreate = page.getByRole('button', { name: 'Crear Proyecto', exact: true });
  }

  async goto() {
    await this.page.goto('/seleccion-proyecto');
  }

  async createProject({ name, format = 'serie', genre = 'drama', synopsis = '', director = '' }) {
    await this.createButton.click();
    await this.name.fill(name);
    await this.format.selectOption(format);
    await this.genre.selectOption(genre);
    if (synopsis) await this.synopsis.fill(synopsis);
    if (director) await this.director.fill(director);
    await this.submitCreate.click();
  }

  projectItem(name) {
    return this.page.getByRole('button', { name: new RegExp(name) });
  }
}
