import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TwoFactor from '../../src/screen/TwoFactor.jsx'
import { apiFetch, setToken } from '../../src/api.js'
import { reply } from './helpers.js'

const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal()),
  useNavigate: () => navigate,
}))
vi.mock('../../src/api.js', () => ({
  apiFetch: vi.fn(),
  getDeviceId: vi.fn(() => 'dispositivo-1'),
  setToken: vi.fn(),
}))

function renderPage(mail = 'ana@x.co') {
  const user = userEvent.setup()
  render(
    <MemoryRouter initialEntries={[{ pathname: '/verificacion', state: { mail } }]}>
      <TwoFactor />
    </MemoryRouter>,
  )
  return user
}

async function submitCode(user, code = '123456') {
  await user.type(screen.getByLabelText('Código de Verificación'), code)
  await user.click(screen.getByRole('button', { name: 'Verificar' }))
}

beforeEach(() => {
  vi.resetAllMocks()
  navigate.mockReset()
})

describe('TwoFactor', () => {
  it('should tell the person which email received the code', () => {
    renderPage('ana@x.co')

    expect(screen.getByText('ana@x.co')).toBeInTheDocument()
  })

  it('should limit the code input to 6 characters', async () => {
    const user = renderPage()

    await user.type(screen.getByLabelText('Código de Verificación'), '1234567890')

    expect(screen.getByLabelText('Código de Verificación')).toHaveValue('123456')
  })

  it('should send mail, code and device id to verify', async () => {
    apiFetch.mockResolvedValue(reply({ success: false, message: 'x' }))
    const user = renderPage()

    await submitCode(user)

    expect(apiFetch).toHaveBeenCalledWith('/users/2fa/verify', {
      method: 'POST',
      body: JSON.stringify({ mail: 'ana@x.co', codigo: '123456', device_id: 'dispositivo-1' }),
    })
  })

  it('should store the renewed token and continue to the project selection', async () => {
    apiFetch.mockResolvedValue(reply({ success: true, data: { access_token: 'nuevo-jwt' } }))
    const user = renderPage()

    await submitCode(user)

    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/seleccion-proyecto'))
    expect(setToken).toHaveBeenCalledWith('nuevo-jwt')
  })

  it('should continue even when the backend does not return a new token', async () => {
    apiFetch.mockResolvedValue(reply({ success: true }))
    const user = renderPage()

    await submitCode(user)

    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/seleccion-proyecto'))
    expect(setToken).not.toHaveBeenCalled()
  })

  it('should show the backend message when the code is wrong or expired', async () => {
    apiFetch.mockResolvedValue(reply({ success: false, message: 'Código incorrecto' }))
    const user = renderPage()

    await submitCode(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Código incorrecto')
    expect(navigate).not.toHaveBeenCalled()
  })

  it('should show a default message when the error has no detail', async () => {
    apiFetch.mockResolvedValue(reply({}, false))
    const user = renderPage()

    await submitCode(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Código incorrecto o expirado')
  })

  it('should show a connection error when the server cannot be reached', async () => {
    apiFetch.mockRejectedValue(new Error('network'))
    const user = renderPage()

    await submitCode(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })

  it('should confirm that the code was sent again', async () => {
    apiFetch.mockResolvedValue(reply({ success: true }))
    const user = renderPage()

    await user.click(screen.getByRole('button', { name: 'Reenviar código' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Código reenviado exitosamente')
    expect(apiFetch).toHaveBeenCalledWith('/users/2fa/send', {
      method: 'POST',
      body: JSON.stringify({ mail: 'ana@x.co', device_id: 'dispositivo-1' }),
    })
  })

  it('should show an error when the code cannot be sent again', async () => {
    apiFetch.mockResolvedValue(reply({ success: false, message: 'Error al enviar código' }))
    const user = renderPage()

    await user.click(screen.getByRole('button', { name: 'Reenviar código' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Error al enviar código')
  })

  it('should show a connection error when resending fails', async () => {
    apiFetch.mockRejectedValue(new Error('network'))
    const user = renderPage()

    await user.click(screen.getByRole('button', { name: 'Reenviar código' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })

  it('should go back to the login page', async () => {
    const user = renderPage()

    await user.click(screen.getByRole('button', { name: /volver al login/i }))

    expect(navigate).toHaveBeenCalledWith('/')
  })

  it('should show a default message when resending fails without a reason', async () => {
    apiFetch.mockResolvedValue(reply({ success: false }))
    const user = renderPage()

    await user.click(screen.getByRole('button', { name: 'Reenviar código' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Error al reenviar el código')
  })

  it('should not crash when the page is opened without the email in the navigation state', () => {
    render(<MemoryRouter><TwoFactor /></MemoryRouter>)

    expect(screen.getByLabelText('Código de Verificación')).toBeInTheDocument()
  })

  it('should hide the "code sent again" confirmation after 3 seconds', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    apiFetch.mockResolvedValue(reply({ success: true }))
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(
      <MemoryRouter initialEntries={[{ pathname: '/verificacion', state: { mail: 'ana@x.co' } }]}>
        <TwoFactor />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: 'Reenviar código' }))
    expect(await screen.findByRole('status')).toBeInTheDocument()
    await vi.advanceTimersByTimeAsync(3100)

    await waitFor(() => expect(screen.queryByRole('status')).not.toBeInTheDocument())
    vi.useRealTimers()
  })
})

