// Login SIN mockear api.js: el componente usa el apiFetch real y MSW responde a nivel de red.
// Verifica el contrato componente → capa de red → HTTP (rutas, cuerpos y cabeceras reales).
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { MemoryRouter } from 'react-router-dom'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import Login from '../../src/screen/Login.jsx'
import { getToken } from '../../src/api.js'
import { API, server } from '../server.js'

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal()),
  useNavigate: () => navigate,
}))

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
beforeEach(() => navigate.mockReset())

const SESION = {
  success: true,
  data: { id_user: 7, nombre: 'Ana', apellido: 'Ruiz', mail: 'ana@x.co', id_rol: 1001, id_client: 3, access_token: 'jwt-real' },
}

async function iniciarSesion(user, password = 'Foccus#2026') {
  await user.type(screen.getByLabelText('E-mail'), 'ana@x.co')
  await user.type(screen.getByLabelText('Contraseña'), password)
  await user.click(screen.getByRole('button', { name: 'Ingresar' }))
}

describe('Login contra un servidor simulado', () => {
  it('should complete the full 2FA handshake and keep the token for later requests', async () => {
    const llamadas = []
    server.use(
      http.post(`${API}/users/login`, () => HttpResponse.json(SESION)),
      http.post(`${API}/users/2fa/check`, () => HttpResponse.json({ data: { requires_2fa: true } })),
      http.post(`${API}/users/2fa/send`, async ({ request }) => {
        llamadas.push({ authorization: request.headers.get('authorization'), cuerpo: await request.json() })
        return HttpResponse.json({ success: true })
      }),
    )
    const user = userEvent.setup()
    render(<MemoryRouter><Login /></MemoryRouter>)

    await iniciarSesion(user)

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/verificacion', { state: { mail: 'ana@x.co' }, replace: true }))
    expect(getToken()).toBe('jwt-real')
    // las llamadas posteriores al login ya viajan con el token recién guardado
    expect(llamadas[0].authorization).toBe('Bearer jwt-real')
    expect(llamadas[0].cuerpo.mail).toBe('ana@x.co')
    expect(llamadas[0].cuerpo.device_id).toBeTruthy()
  })

  it('should show the backend message when the password is wrong', async () => {
    server.use(
      http.post(`${API}/users/login`, () =>
        HttpResponse.json({ success: false, message: 'Contraseña incorrecta', error: 'INVALID_PASSWORD' }),
      ),
    )
    const user = userEvent.setup()
    render(<MemoryRouter><Login /></MemoryRouter>)

    await iniciarSesion(user, 'mala')

    expect(await screen.findByRole('alert')).toHaveTextContent('Contraseña incorrecta')
    expect(getToken()).toBeNull()
  })

  it('should show a readable message when the backend rejects the body with a 422 list', async () => {
    server.use(
      http.post(`${API}/users/login`, () =>
        HttpResponse.json({ detail: [{ msg: 'Field required' }] }, { status: 422 }),
      ),
    )
    const user = userEvent.setup()
    render(<MemoryRouter><Login /></MemoryRouter>)

    await iniciarSesion(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Field required')
  })

  it('should show a connection error when the network is down', async () => {
    server.use(http.post(`${API}/users/login`, () => HttpResponse.error()))
    const user = userEvent.setup()
    render(<MemoryRouter><Login /></MemoryRouter>)

    await iniciarSesion(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })

  it('should not leave the form stuck when the server answers with a 500 and no JSON', async () => {
    server.use(http.post(`${API}/users/login`, () => new HttpResponse('Internal Server Error', { status: 500 })))
    const user = userEvent.setup()
    render(<MemoryRouter><Login /></MemoryRouter>)

    await iniciarSesion(user)

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeEnabled()
  })
})
