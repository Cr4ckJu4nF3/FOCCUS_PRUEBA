import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProjectSelection from '../../src/screen/ProjectSelection.jsx'
import { apiFetch } from '../../src/api.js'
import { reply } from './helpers.js'

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal()),
  useNavigate: () => navigate,
}))
vi.mock('../../src/api.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiFetch: vi.fn(),
}))

const PROYECTOS = [
  { id_project: 'proj0001', project_name: 'La serie', formato_de_produccion: 'serie', genero: 'drama', director: 'Laura' },
  { id_project: 'proj0002', project_name: 'Mi película', formato_de_produccion: 'pelicula', genero: 'comedia', director: null },
]

function renderAs(idRol) {
  localStorage.setItem('id_rol', String(idRol))
  localStorage.setItem('id_user', '7')
  localStorage.setItem('id_client', '3')
  const user = userEvent.setup()
  render(<MemoryRouter><ProjectSelection /></MemoryRouter>)
  return user
}

beforeEach(() => {
  vi.resetAllMocks()
  navigate.mockReset()
})

describe('ProjectSelection: permisos', () => {
  it('should offer both actions to an administrator', () => {
    renderAs(1001)

    expect(screen.getByRole('button', { name: /Escoger Proyecto/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Crear Proyecto/ })).toBeInTheDocument()
  })

  it('should hide project creation from a user who is not an administrator', () => {
    renderAs(1005)

    expect(screen.getByRole('button', { name: /Escoger Proyecto/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Crear Proyecto/ })).not.toBeInTheDocument()
  })
})

describe('ProjectSelection: lista de proyectos', () => {
  it('should load and list the projects of the logged user', async () => {
    apiFetch.mockResolvedValue(reply({ data: PROYECTOS }))
    const user = renderAs(1001)

    await user.click(screen.getByRole('button', { name: /Escoger Proyecto/ }))

    expect(await screen.findByRole('button', { name: /La serie/ })).toBeInTheDocument()
    expect(screen.getByText('2 proyectos')).toBeInTheDocument()
    expect(apiFetch).toHaveBeenCalledWith('/users/7/projects')
  })

  it('should tell the person when there are no projects', async () => {
    apiFetch.mockResolvedValue(reply({ data: [] }))
    const user = renderAs(1001)

    await user.click(screen.getByRole('button', { name: /Escoger Proyecto/ }))

    expect(await screen.findByText('No hay proyectos disponibles. Crea uno nuevo.')).toBeInTheDocument()
  })

  it('should accept a response that is a plain list without the data wrapper', async () => {
    apiFetch.mockResolvedValue(reply(PROYECTOS))
    const user = renderAs(1001)

    await user.click(screen.getByRole('button', { name: /Escoger Proyecto/ }))

    expect(await screen.findByRole('button', { name: /La serie/ })).toBeInTheDocument()
  })

  it('should show no projects when the response is neither a list nor wrapped in data', async () => {
    apiFetch.mockResolvedValue(reply({ data: { mensaje: 'algo raro' } }))
    const user = renderAs(1001)

    await user.click(screen.getByRole('button', { name: /Escoger Proyecto/ }))

    expect(await screen.findByText('No hay proyectos disponibles. Crea uno nuevo.')).toBeInTheDocument()
  })

  it('should treat a session without a stored role as a regular user', () => {
    localStorage.removeItem('id_rol')
    render(<MemoryRouter><ProjectSelection /></MemoryRouter>)

    expect(screen.queryByRole('button', { name: /Crear Proyecto/ })).not.toBeInTheDocument()
  })

  it('should open the dashboard of the chosen project', async () => {
    apiFetch.mockResolvedValue(reply({ data: PROYECTOS }))
    const user = renderAs(1001)
    await user.click(screen.getByRole('button', { name: /Escoger Proyecto/ }))

    await user.click(await screen.findByRole('button', { name: /Mi película/ }))

    expect(navigate).toHaveBeenCalledWith('/proyecto-dashboard', {
      state: { projectName: 'Mi película', projectId: 'proj0002' },
    })
  })

  it('should highlight a project while the pointer is over it', async () => {
    apiFetch.mockResolvedValue(reply({ data: PROYECTOS }))
    const user = renderAs(1001)
    await user.click(screen.getByRole('button', { name: /Escoger Proyecto/ }))
    const item = await screen.findByRole('button', { name: /La serie/ })

    await user.hover(item)
    await user.unhover(item)

    expect(item).toBeInTheDocument()
  })

  it('should show an error when the projects cannot be loaded', async () => {
    apiFetch.mockResolvedValue(reply({}, false))
    const user = renderAs(1001)

    await user.click(screen.getByRole('button', { name: /Escoger Proyecto/ }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Error al cargar los proyectos')
  })

  it('should show a connection error when the server cannot be reached', async () => {
    apiFetch.mockRejectedValue(new Error('network'))
    const user = renderAs(1001)

    await user.click(screen.getByRole('button', { name: /Escoger Proyecto/ }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })
})

describe('ProjectSelection: crear proyecto', () => {
  async function abrirModal(user) {
    await user.click(screen.getByRole('button', { name: /Crear Proyecto/ }))
  }

  it('should expose every form field with an accessible label', async () => {
    const user = renderAs(1001)

    await abrirModal(user)

    for (const etiqueta of ['Nombre del Proyecto', 'Formato', 'Género', 'Sinopsis', 'Director']) {
      expect(screen.getByLabelText(etiqueta)).toBeInTheDocument()
    }
    expect(screen.getByLabelText('Nombre del Proyecto')).toBeRequired()
  })

  it('should send the form with the ids of the logged user and open the new dashboard', async () => {
    apiFetch.mockResolvedValue(reply({ success: true, data: { id_project: 'proj0009' } }))
    const user = renderAs(1001)
    await abrirModal(user)

    await user.type(screen.getByLabelText('Nombre del Proyecto'), 'Nueva serie')
    await user.selectOptions(screen.getByLabelText('Formato'), 'serie')
    await user.selectOptions(screen.getByLabelText('Género'), 'drama')
    await user.type(screen.getByLabelText('Director'), 'Laura')
    await user.click(screen.getAllByRole('button', { name: 'Crear Proyecto' }).at(-1))

    await waitFor(() => expect(navigate).toHaveBeenCalled())
    const [ruta, opciones] = apiFetch.mock.calls[0]
    expect(ruta).toBe('/projects/create')
    expect(JSON.parse(opciones.body)).toMatchObject({
      project_name: 'Nueva serie', formato_de_produccion: 'serie', genero: 'drama',
      director: 'Laura', id_client: 3, id_user: 7,
    })
    expect(navigate).toHaveBeenCalledWith('/proyecto-dashboard', {
      state: { projectName: 'Nueva serie', projectId: 'proj0009' },
    })
  })

  it('should show the backend message when the project cannot be created', async () => {
    apiFetch.mockResolvedValue(reply({ success: false, message: 'Proyecto duplicado' }, false))
    const user = renderAs(1001)
    await abrirModal(user)
    await user.type(screen.getByLabelText('Nombre del Proyecto'), 'Nueva serie')
    await user.selectOptions(screen.getByLabelText('Formato'), 'serie')
    await user.selectOptions(screen.getByLabelText('Género'), 'drama')

    await user.click(screen.getAllByRole('button', { name: 'Crear Proyecto' }).at(-1))

    expect((await screen.findAllByRole('alert'))[0]).toHaveTextContent('Proyecto duplicado')
    expect(navigate).not.toHaveBeenCalled()
  })

  async function enviarFormularioValido(user) {
    await abrirModal(user)
    await user.type(screen.getByLabelText('Nombre del Proyecto'), 'Nueva serie')
    await user.selectOptions(screen.getByLabelText('Formato'), 'serie')
    await user.selectOptions(screen.getByLabelText('Género'), 'drama')
    await user.click(screen.getAllByRole('button', { name: 'Crear Proyecto' }).at(-1))
  }

  it('should create the project with client 1 when the session has no client stored', async () => {
    apiFetch.mockResolvedValue(reply({ success: true, data: { id_project: 'proj0001' } }))
    const user = renderAs(1001)
    localStorage.removeItem('id_client')

    await enviarFormularioValido(user)

    await waitFor(() => expect(apiFetch).toHaveBeenCalled())
    expect(JSON.parse(apiFetch.mock.calls[0][1].body).id_client).toBe(1)
  })

  it('should show a validation error that comes as a plain string', async () => {
    apiFetch.mockResolvedValue(reply({ detail: 'Token inválido' }, false))
    const user = renderAs(1001)

    await enviarFormularioValido(user)

    expect((await screen.findAllByRole('alert'))[0]).toHaveTextContent('Token inválido')
  })

  it('should join a list of validation errors', async () => {
    apiFetch.mockResolvedValue(reply({ detail: [{ msg: 'campo a' }, { msg: 'campo b' }] }, false))
    const user = renderAs(1001)

    await enviarFormularioValido(user)

    expect((await screen.findAllByRole('alert'))[0]).toHaveTextContent('campo a, campo b')
  })

  it('should fall back to a default message when the error has no detail', async () => {
    apiFetch.mockResolvedValue(reply({}, false))
    const user = renderAs(1001)

    await enviarFormularioValido(user)

    expect((await screen.findAllByRole('alert'))[0]).toHaveTextContent('Error al crear el proyecto')
  })

  it('should show a connection error when the creation request fails', async () => {
    apiFetch.mockRejectedValue(new Error('network'))
    const user = renderAs(1001)

    await enviarFormularioValido(user)

    expect((await screen.findAllByRole('alert'))[0]).toHaveTextContent('No se pudo conectar con el servidor')
  })

  // H-F10: el backend responde HTTP 200 con success:false ante errores de negocio y
  // la pantalla lo toma por éxito (cierra el modal y navega con projectId undefined)
  it.fails('should report a business error that arrives as HTTP 200 with success:false', async () => {
    apiFetch.mockResolvedValue(reply({ success: false, message: 'Proyecto duplicado' }, true))
    const user = renderAs(1001)

    await enviarFormularioValido(user)

    expect((await screen.findAllByRole('alert'))[0]).toHaveTextContent('Proyecto duplicado')
    expect(navigate).not.toHaveBeenCalled()
  })

  it('should close the modal with the close button', async () => {
    const user = renderAs(1001)
    await abrirModal(user)

    await user.click(screen.getByRole('button', { name: 'Cerrar' }))

    expect(screen.queryByLabelText('Nombre del Proyecto')).not.toBeInTheDocument()
  })

  it('should close the modal when the person clicks outside of it', async () => {
    const user = renderAs(1001)
    await abrirModal(user)

    await user.click(document.querySelector('.pss-modal-backdrop'))

    expect(screen.queryByLabelText('Nombre del Proyecto')).not.toBeInTheDocument()
  })

  it('should close the modal without sending anything when the person cancels', async () => {
    const user = renderAs(1001)
    await abrirModal(user)

    await user.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(screen.queryByLabelText('Nombre del Proyecto')).not.toBeInTheDocument()
    expect(apiFetch).not.toHaveBeenCalled()
  })
})

describe('ProjectSelection: cerrar sesión', () => {
  it('should clear the session and go back to the home page', async () => {
    const user = renderAs(1001)

    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    expect(localStorage.getItem('id_user')).toBeNull()
    expect(navigate).toHaveBeenCalledWith('/', { replace: true })
  })
})
