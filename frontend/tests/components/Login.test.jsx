import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Login from '../../src/screen/Login.jsx'
import { apiFetch, setToken } from '../../src/api.js'
import { reply } from './helpers.js'

// useNavigate se reemplaza para verificar a dónde manda la pantalla sin un router real
const navigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal()),
  useNavigate: () => navigate,
}))
// El módulo de red completo se reemplaza: estos tests no tocan el backend
vi.mock('../../src/api.js', () => ({
  apiFetch: vi.fn(),
  getDeviceId: vi.fn(() => 'dispositivo-1'),
  setToken: vi.fn(),
}))

const LOGIN_OK = {
  success: true,
  data: {
    id_user: 7, nombre: 'Ana', apellido: 'Ruiz', mail: 'ana@x.co',
    id_rol: 1001, id_client: 3, access_token: 'jwt-123',
  },
}

function renderLogin() {
  const user = userEvent.setup()
  render(<MemoryRouter><Login /></MemoryRouter>)
  return user
}

async function submitLogin(user, mail = 'ana@x.co', password = 'Foccus#2026') {
  await user.type(screen.getByLabelText('E-mail'), mail)
  await user.type(screen.getByLabelText('Contraseña'), password)
  await user.click(screen.getByRole('button', { name: 'Ingresar' }))
}

beforeEach(() => {
  vi.resetAllMocks()
  navigate.mockReset()
})

describe('Login: pestaña Ingresar', () => {
  it('should render the email and password fields with accessible labels', () => {
    renderLogin()

    expect(screen.getByLabelText('E-mail')).toBeRequired()
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('type', 'password')
  })

  it('should reveal and hide the password with the eye button', async () => {
    const user = renderLogin()

    await user.click(screen.getByRole('button', { name: 'Mostrar contraseña' }))
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('type', 'text')

    await user.click(screen.getByRole('button', { name: 'Ocultar contraseña' }))
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('type', 'password')
  })

  it('should send the trimmed lowercase email and the password to the API', async () => {
    apiFetch.mockResolvedValue(reply({ success: false, message: 'x' }))
    const user = renderLogin()

    await submitLogin(user, '  ANA@X.CO ')

    expect(apiFetch).toHaveBeenCalledWith('/users/login', {
      method: 'POST',
      body: JSON.stringify({ mail: 'ana@x.co', contrasena: 'Foccus#2026' }),
    })
  })

  it('should show the backend message when the credentials are wrong', async () => {
    apiFetch.mockResolvedValue(reply({ success: false, message: 'Contraseña incorrecta' }))
    const user = renderLogin()

    await submitLogin(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Contraseña incorrecta')
    expect(navigate).not.toHaveBeenCalled()
  })

  it('should show a readable message when a validation error comes as a list', async () => {
    apiFetch.mockResolvedValue(
      reply({ detail: [{ msg: 'campo requerido' }, { msg: 'formato inválido' }] }, false),
    )
    const user = renderLogin()

    await submitLogin(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('campo requerido, formato inválido')
  })

  it('should show a default message when the error carries no detail', async () => {
    apiFetch.mockResolvedValue(reply({}, false))
    const user = renderLogin()

    await submitLogin(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Correo o contraseña incorrectos')
  })

  it('should show a connection error when the server cannot be reached', async () => {
    apiFetch.mockRejectedValue(new Error('network'))
    const user = renderLogin()

    await submitLogin(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })

  it('should disable the submit button while the request is in flight', async () => {
    let resolver
    apiFetch.mockReturnValue(new Promise((resolve) => { resolver = resolve }))
    const user = renderLogin()

    await submitLogin(user)

    expect(await screen.findByRole('button', { name: 'Ingresando...' })).toBeDisabled()
    resolver(reply({ success: false, message: 'x' }))
    expect(await screen.findByRole('button', { name: 'Ingresar' })).toBeEnabled()
  })

  it('should store the session, request the 2FA code and go to the verification page', async () => {
    apiFetch
      .mockResolvedValueOnce(reply(LOGIN_OK))
      .mockResolvedValueOnce(reply({ data: { requires_2fa: true } }))
      .mockResolvedValueOnce(reply({ success: true }))
    const user = renderLogin()

    await submitLogin(user)

    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith('/verificacion', {
        state: { mail: 'ana@x.co' },
        replace: true,
      }),
    )
    expect(setToken).toHaveBeenCalledWith('jwt-123')
    expect(localStorage.getItem('id_user')).toBe('7')
    expect(localStorage.getItem('id_rol')).toBe('1001')
    expect(localStorage.getItem('id_client')).toBe('3')
    expect(apiFetch).toHaveBeenNthCalledWith(3, '/users/2fa/send', {
      method: 'POST',
      body: JSON.stringify({ mail: 'ana@x.co', device_id: 'dispositivo-1' }),
    })
  })

  it('should stay on the page and show the message when the 2FA code cannot be sent', async () => {
    apiFetch
      .mockResolvedValueOnce(reply(LOGIN_OK))
      .mockResolvedValueOnce(reply({ data: { requires_2fa: true } }))
      .mockResolvedValueOnce(reply({ success: false, message: 'Error al enviar código' }))
    const user = renderLogin()

    await submitLogin(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Error al enviar código')
    expect(navigate).not.toHaveBeenCalled()
  })

  it('should go straight to the project selection when the device does not need 2FA', async () => {
    apiFetch
      .mockResolvedValueOnce(reply(LOGIN_OK))
      .mockResolvedValueOnce(reply({ data: { requires_2fa: false } }))
    const user = renderLogin()

    await submitLogin(user)

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/seleccion-proyecto', { replace: true }))
  })

  it('should go to the project selection when the 2FA check itself fails', async () => {
    apiFetch.mockResolvedValueOnce(reply(LOGIN_OK)).mockResolvedValueOnce(reply({}, false))
    const user = renderLogin()

    await submitLogin(user)

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/seleccion-proyecto', { replace: true }))
  })

  it('should open the password recovery page from the forgot-password link', async () => {
    const user = renderLogin()

    await user.click(screen.getByRole('button', { name: /olvidaste tu contraseña/i }))

    expect(navigate).toHaveBeenCalledWith('/recuperar-acceso')
  })
})

// ───────── Registro en 3 pasos ─────────

async function fillStep1(user) {
  await user.type(screen.getByLabelText('Razón Social'), 'Productora Sur')
  await user.type(screen.getByLabelText('Representante Legal'), 'Laura Gómez')
  await user.selectOptions(screen.getByLabelText('Documento'), 'NIT')
  await user.type(screen.getByLabelText('Nº Documento'), '900123')
  await user.type(screen.getByLabelText('Email Empresa'), 'contacto@sur.co')
}

async function fillStep2(user) {
  await user.type(screen.getByLabelText('Nombres'), 'Camila')
  await user.type(screen.getByLabelText('Apellidos'), 'Prueba')
  await user.type(screen.getByLabelText('Email Personal'), 'camila@sur.co')
  await user.type(screen.getByLabelText('Celular'), '3001112233')
}

async function goToStep3(user) {
  await user.click(screen.getByRole('tab', { name: 'Registrar' }))
  await fillStep1(user)
  await user.click(screen.getByRole('button', { name: 'Continuar' }))
  await fillStep2(user)
  await user.click(screen.getByRole('button', { name: 'Continuar' }))
}

async function fillStep3(user, { password = 'Foccus#2026', confirm = password, terms = true } = {}) {
  await user.type(screen.getByLabelText('Contraseña'), password)
  await user.type(screen.getByLabelText('Confirmar Contraseña'), confirm)
  if (terms) await user.click(screen.getByRole('checkbox'))
}

describe('Login: registro de empresa y usuario', () => {
  it('should start at step 1 and not advance while required fields are empty', async () => {
    const user = renderLogin()
    await user.click(screen.getByRole('tab', { name: 'Registrar' }))
    expect(screen.getByText('Paso 1 de 3')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Continuar' }))

    expect(screen.getByText('Paso 1 de 3')).toBeInTheDocument()
    expect(screen.queryByText('Paso 2 de 3')).not.toBeInTheDocument()
  })

  it('should advance to step 2 when the company data is complete and allow going back', async () => {
    const user = renderLogin()
    await user.click(screen.getByRole('tab', { name: 'Registrar' }))
    await fillStep1(user)

    await user.click(screen.getByRole('button', { name: 'Continuar' }))
    expect(screen.getByText('Paso 2 de 3')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Atrás' }))
    expect(screen.getByText('Paso 1 de 3')).toBeInTheDocument()
    expect(screen.getByLabelText('Razón Social')).toHaveValue('Productora Sur')
  })

  it('should show each password rule as met while the person types', async () => {
    const user = renderLogin()
    await goToStep3(user)

    expect(screen.getByText(/○ Un número/)).toBeInTheDocument()
    await user.type(screen.getByLabelText('Contraseña'), 'abc1')

    expect(screen.getByText(/✓ Una letra minúscula/)).toBeInTheDocument()
    expect(screen.getByText(/✓ Un número/)).toBeInTheDocument()
    expect(screen.getByText(/○ Una letra mayúscula/)).toBeInTheDocument()
  })

  it('should show an error when the passwords do not match', async () => {
    const user = renderLogin()
    await goToStep3(user)
    await fillStep3(user, { confirm: 'Otra#2026x' })

    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Las contraseñas no coinciden')
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('should list the missing rules when the password is too weak', async () => {
    const user = renderLogin()
    await goToStep3(user)
    await fillStep3(user, { password: 'abc' })

    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('La contraseña debe tener:')
    expect(alerta).toHaveTextContent('Mínimo 8 caracteres')
    expect(alerta).toHaveTextContent('Una letra mayúscula')
  })

  it('should require accepting the terms before sending the registration', async () => {
    const user = renderLogin()
    await goToStep3(user)
    await fillStep3(user, { terms: false })

    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Debes aceptar los términos y condiciones')
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('should send the registration without the confirmation field and return to the login tab', async () => {
    apiFetch.mockResolvedValue(reply({ success: true }))
    const user = renderLogin()
    await goToStep3(user)
    await fillStep3(user)

    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Registro completado')
    const [ruta, opciones] = apiFetch.mock.calls[0]
    expect(ruta).toBe('/register')
    const enviado = JSON.parse(opciones.body)
    expect(enviado).toMatchObject({ mail: 'camila@sur.co', razon_social: 'Productora Sur', document: 'NIT' })
    expect(enviado).not.toHaveProperty('confirmarContrasena')
    // vuelve a "Ingresar" con el correo ya escrito y la contraseña vacía
    expect(screen.getByLabelText('E-mail')).toHaveValue('camila@sur.co')
    expect(screen.getByLabelText('Contraseña')).toHaveValue('')
  })

  it('should show the backend error when the company is already registered', async () => {
    apiFetch.mockResolvedValue(reply({ success: false, message: 'La empresa ya está registrada' }))
    const user = renderLogin()
    await goToStep3(user)
    await fillStep3(user)

    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('La empresa ya está registrada')
  })

  it('should show a connection error when the registration request fails', async () => {
    apiFetch.mockRejectedValue(new Error('network'))
    const user = renderLogin()
    await goToStep3(user)
    await fillStep3(user)

    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor')
  })

  it('should clear a previous error when switching tabs', async () => {
    apiFetch.mockResolvedValue(reply({ success: false, message: 'Correo no registrado' }))
    const user = renderLogin()
    await submitLogin(user)
    await screen.findByRole('alert')

    await user.click(screen.getByRole('tab', { name: 'Registrar' }))

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('should reveal and hide both password fields of the registration form', async () => {
    const user = renderLogin()
    await goToStep3(user)

    await user.click(screen.getByRole('button', { name: 'Mostrar contraseña' }))
    await user.click(screen.getByRole('button', { name: 'Mostrar confirmación de contraseña' }))
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('type', 'text')
    expect(screen.getByLabelText('Confirmar Contraseña')).toHaveAttribute('type', 'text')

    await user.click(screen.getByRole('button', { name: 'Ocultar contraseña' }))
    await user.click(screen.getByRole('button', { name: 'Ocultar confirmación de contraseña' }))
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText('Confirmar Contraseña')).toHaveAttribute('type', 'password')
  })

  it('should go back to the login tab from the registration form', async () => {
    const user = renderLogin()
    await user.click(screen.getByRole('tab', { name: 'Registrar' }))

    await user.click(screen.getByRole('tab', { name: 'Ingresar' }))

    expect(screen.getByLabelText('E-mail')).toBeInTheDocument()
  })

  it.each([
    ['a plain string', { detail: 'Datos inválidos' }, 'Datos inválidos'],
    ['a list', { detail: [{ msg: 'campo a' }, { msg: 'campo b' }] }, 'campo a, campo b'],
  ])('should show a registration validation error that comes as %s', async (_forma, cuerpo, esperado) => {
    apiFetch.mockResolvedValue(reply(cuerpo, false))
    const user = renderLogin()
    await goToStep3(user)
    await fillStep3(user)

    await user.click(screen.getByRole('button', { name: 'Crear cuenta' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(esperado)
  })
})
