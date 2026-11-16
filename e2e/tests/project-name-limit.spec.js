import { test, expect } from './fixtures.js';
import { SeleccionProyectoPage } from './pages/SeleccionProyectoPage.js';
import { API_URL } from './support.js';

// Historia TDD (semana 10): escrito AL INICIO, en rojo hasta que backend y frontend terminen.
test.describe('Límite del nombre de proyecto (45 caracteres)', () => {
  test('should not let the person type more than 45 characters', async ({ page, usuario, iniciarSesion }) => {
    await iniciarSesion(usuario.mail);
    const seleccion = new SeleccionProyectoPage(page);
    await seleccion.goto();
    await seleccion.createButton.click();

    // pressSequentially teclea como una persona (fill() ignora maxlength)
    await seleccion.name.pressSequentially('x'.repeat(60));

    await expect(seleccion.name).toHaveValue('x'.repeat(45));
  });

  test('should show how many characters the name has', async ({ page, usuario, iniciarSesion }) => {
    await iniciarSesion(usuario.mail);
    const seleccion = new SeleccionProyectoPage(page);
    await seleccion.goto();
    await seleccion.createButton.click();

    await seleccion.name.pressSequentially('Mi serie');

    await expect(page.getByText('8/45')).toBeVisible();
  });

  test('the API rejects a 46-character name with 422', async ({ request, usuario, iniciarSesion, page }) => {
    const sesion = await iniciarSesion(usuario.mail);

    const response = await request.post(`${API_URL}/projects`, {
      headers: { Authorization: `Bearer ${sesion.access_token}` },
      data: {
        project_name: 'x'.repeat(46),
        formato_de_produccion: 'serie',
        genero: 'drama',
        id_client: sesion.id_client,
      },
    });

    expect(response.status()).toBe(422);
    expect(JSON.stringify(await response.json())).toContain('project_name');
  });
});
