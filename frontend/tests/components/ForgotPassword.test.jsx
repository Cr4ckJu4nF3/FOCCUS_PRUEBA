import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ForgotPassword from '../../src/screen/ForgotPassword.jsx'
import { reply } from './helpers.js'

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal()),
  useNavigate: () => navigate,
}))
// Esta pantalla usa fetch directo (no apiFetch): se reemplaza fetch global.
// En la semana 5 las llamadas de red se prueban también con MSW.
const fetchMock = vi.fn()

beforeEach(() => {
  navigate.mockReset()
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

function renderPage() {
  const user = userEvent.setup()
  render(<MemoryRouter><ForgotPassword /></MemoryRouter>)
  return user
}

async function requestCode(user, mail = '  Ana@X.co ') {
  await user.type(screen.getByLabelText('Correo Electrónico'), mail)
  await user.click(screen.getByRole('button', { name: 'Enviar Código' }))
}

async function reachStep2(user) {
  fetchMock.mockResolvedValueOnce(reply({ success: true }))
  await requestCode(user)
  await screen.findByRole('heading', { name: 'Restablecer Contraseña' })
}

async function fillReset(user, { code = '123456', password = 'Foccus#2026', confirm = password } = {}) {
  await user.type(screen.getByLabelText('Código de Verificación'), code)
  await user.type(screen.getByLabelText('Nueva Contraseña'), password)
  await user.type(screen.getByLabelText('Confirmar Nueva Contraseña'), confirm)
}

describe('ForgotPassword: paso 1 (pedir el código)', () => {
  it('should ask for the registered email', () => {
    renderPage()

    expect(screen.getByRole('heading', { name: 'Recuperación de Acceso' })).toBeInTheDocument()
    expect(screen.getByLabelText('Correo Electrónico')).toBeRequired()
  })

  it('should send the normalized email and move to step 2 when the account exists', async () => {
    fetchMock.mockResolvedValueOnce(reply({ success: true }))
    const user = renderPage()

    await requestCode(user)

    expect(await screen.findByRole('heading', { name: 'Restablecer Contraseña' })).toBeInTheDocument()
    const [url, opciones] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/users\/recover-password$/)
    expect(JSON.parse(opciones.body)).toEqual({ mail: 'ana@x.co' })
  })

  it('should show the backend message when the email is not registered', async () => {
    fetchMock.mockResolvedValueOnce(reply({ success: false, message: 'Correo no registrado' }))
    const user = renderPage()

    await requestCode(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Correo no registrado')
    expect(screen.getByRole('heading', { name: 'Recuperación de Acceso' })).toBeInTheDocument()
  })

  it('should show a connection error when the server cannot be reached', async () => {
    fetchMock.mockRejectedValueOnce(new Error('network'))
    const user = renderPage()

    await requestCode(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })

  it('should go back to the login page', async () => {
    const user = renderPage()

    await user.click(screen.getByRole('button', { name: /volver al inicio de sesión/i }))

    expect(navigate).toHaveBeenCalledWith('/')
  })
})

describe('ForgotPassword: paso 2 (restablecer)', () => {
  it('should show the password rules while the new password is typed', async () => {
    const user = renderPage()
    await reachStep2(user)

    await user.type(screen.getByLabelText('Nueva Contraseña'), 'abc')

    expect(screen.getByText(/✓ Una letra minúscula/)).toBeInTheDocument()
    expect(screen.getByText(/○ Un número/)).toBeInTheDocument()
  })

  it('should reveal and hide each password field', async () => {
    const user = renderPage()
    await reachStep2(user)

    await user.click(screen.getByRole('button', { name: 'Mostrar nueva contraseña' }))
    expect(screen.getByLabelText('Nueva Contraseña')).toHaveAttribute('type', 'text')
    await user.click(screen.getByRole('button', { name: 'Mostrar confirmación de contraseña' }))
    expect(screen.getByLabelText('Confirmar Nueva Contraseña')).toHaveAttribute('type', 'text')
  })

  it('should not call the API when the two passwords differ', async () => {
    const user = renderPage()
    await reachStep2(user)
    fetchMock.mockClear()

    await fillReset(user, { confirm: 'Otra#2026xx' })
    await user.click(screen.getByRole('button', { name: 'Restablecer Contraseña' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Las contraseñas no coinciden')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('should list the missing rules when the new password is weak', async () => {
    const user = renderPage()
    await reachStep2(user)
    fetchMock.mockClear()

    await fillReset(user, { password: 'abc' })
    await user.click(screen.getByRole('button', { name: 'Restablecer Contraseña' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Mínimo 8 caracteres')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('should send mail, code and new password, then show the success page', async () => {
    const user = renderPage()
    await reachStep2(user)
    fetchMock.mockResolvedValueOnce(reply({ success: true }))

    await fillReset(user)
    await user.click(screen.getByRole('button', { name: 'Restablecer Contraseña' }))

    expect(await screen.findByRole('heading', { name: 'Contraseña Restablecida' })).toBeInTheDocument()
    const [url, opciones] = fetchMock.mock.calls.at(-1)
    expect(url).toMatch(/\/users\/reset-password$/)
    expect(JSON.parse(opciones.body)).toEqual({
      mail: 'ana@x.co',
      codigo: '123456',
      nueva_contrasena: 'Foccus#2026',
    })
  })

  it('should show the backend message when the code is invalid or expired', async () => {
    const user = renderPage()
    await reachStep2(user)
    fetchMock.mockResolvedValueOnce(reply({ success: false, message: 'Código inválido o expirado' }))

    await fillReset(user)
    await user.click(screen.getByRole('button', { name: 'Restablecer Contraseña' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Código inválido o expirado')
  })

  it('should show a connection error when the reset request fails', async () => {
    const user = renderPage()
    await reachStep2(user)
    fetchMock.mockRejectedValueOnce(new Error('network'))

    await fillReset(user)
    await user.click(screen.getByRole('button', { name: 'Restablecer Contraseña' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })

  it('should return to step 1 to change the email', async () => {
    const user = renderPage()
    await reachStep2(user)

    await user.click(screen.getByRole('button', { name: /cambiar correo/i }))

    expect(screen.getByRole('heading', { name: 'Recuperación de Acceso' })).toBeInTheDocument()
  })

  it('should request a new code with the "Reenviar código" button', async () => {
    const user = renderPage()
    await reachStep2(user)
    fetchMock.mockResolvedValueOnce(reply({ success: true }))

    await user.click(screen.getByRole('button', { name: 'Reenviar código' }))

    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('should go back to the login from the success page', async () => {
    const user = renderPage()
    await reachStep2(user)
    fetchMock.mockResolvedValueOnce(reply({ success: true }))
    await fillReset(user)
    await user.click(screen.getByRole('button', { name: 'Restablecer Contraseña' }))

    await user.click(await screen.findByRole('button', { name: 'Ir al Inicio de Sesión' }))

    expect(navigate).toHaveBeenCalledWith('/')
  })
})
