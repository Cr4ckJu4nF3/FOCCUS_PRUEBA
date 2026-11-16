import { test, expect } from './fixtures.js';
import { SeleccionProyectoPage } from './pages/SeleccionProyectoPage.js';
import { API_URL } from './support.js';

const nombreUnico = (prefijo) => `${prefijo} ${Date.now()}${Math.floor(Math.random() * 1000)}`;

test.describe('Gestión de proyectos', () => {
  test('should tell an administrator without projects that there is none yet', async ({ page, usuario, iniciarSesion }) => {
    await iniciarSesion(usuario.mail);
    const seleccion = new SeleccionProyectoPage(page);
    await seleccion.goto();

    await seleccion.chooseButton.click();

    await expect(page.getByText('No hay proyectos disponibles. Crea uno nuevo.')).toBeVisible();
  });

  test('should create a project and open its dashboard', async ({ page, request, usuario, iniciarSesion }) => {
    const sesion = await iniciarSesion(usuario.mail);
    const nombre = nombreUnico('La serie');
    const seleccion = new SeleccionProyectoPage(page);
    await seleccion.goto();

    await seleccion.createProject({ name: nombre, format: 'serie', genre: 'drama', director: 'Laura Gómez' });

    await expect(page).toHaveURL(/\/proyecto-dashboard$/);
    await expect(page.getByText(nombre).first()).toBeVisible();
    // la verdad está en el backend: el proyecto existe y el usuario es su administrador
    const respuesta = await request.get(`${API_URL}/users/${sesion.id_user}/projects`, {
      headers: { Authorization: `Bearer ${sesion.access_token}` },
    });
    const proyectos = (await respuesta.json()).data;
    expect(proyectos.map((p) => p.project_name)).toContain(nombre);
  });

  test('should list the created project so it can be chosen', async ({ page, usuario, iniciarSesion }) => {
    await iniciarSesion(usuario.mail);
    const nombre = nombreUnico('Mi película');
    const seleccion = new SeleccionProyectoPage(page);
    await seleccion.goto();
    await seleccion.createProject({ name: nombre, format: 'pelicula', genre: 'comedia' });
    await expect(page).toHaveURL(/\/proyecto-dashboard$/);

    await seleccion.goto();
    await seleccion.chooseButton.click();
    await seleccion.projectItem(nombre).click();

    await expect(page).toHaveURL(/\/proyecto-dashboard$/);
  });

  test('should not offer project creation to a user who is not an administrator', async ({
    page, usuario, crearMiembro, iniciarSesion,
  }) => {
    const miembro = await crearMiembro(usuario);
    await iniciarSesion(miembro.mail, miembro.contrasena);
    const seleccion = new SeleccionProyectoPage(page);

    await seleccion.goto();

    await expect(seleccion.chooseButton).toBeVisible();
    await expect(page.getByRole('button', { name: /Crear Proyecto/ })).toHaveCount(0);
  });

  test('should require the project name, format and genre', async ({ page, usuario, iniciarSesion }) => {
    await iniciarSesion(usuario.mail);
    const seleccion = new SeleccionProyectoPage(page);
    await seleccion.goto();
    await seleccion.createButton.click();

    await seleccion.submitCreate.click();

    // el formulario no se envía: sigue en la pantalla de selección
    await expect(page).toHaveURL(/\/seleccion-proyecto$/);
    await expect(seleccion.name).toBeFocused();
  });
});
