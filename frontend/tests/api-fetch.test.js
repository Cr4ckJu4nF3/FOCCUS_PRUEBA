import { http, HttpResponse } from 'msw'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, getToken } from '../src/api.js'
import { API, server } from './server.js'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// Captura las cabeceras que realmente llegaron al "servidor"
function capturarCabeceras(ruta = '/echo') {
  const recibidas = {}
  server.use(
    http.get(`${API}${ruta}`, ({ request }) => {
      recibidas.authorization = request.headers.get('authorization')
      recibidas.contentType = request.headers.get('content-type')
      recibidas.custom = request.headers.get('x-custom')
      return HttpResponse.json({ ok: true })
    }),
  )
  return recibidas
}

describe('apiFetch', () => {
  it('should send the Bearer token when there is an active session', async () => {
    localStorage.setItem('access_token', 'jwt-123')
    const recibidas = capturarCabeceras()

    await apiFetch('/echo')

    expect(recibidas.authorization).toBe('Bearer jwt-123')
  })

  it('should not send an Authorization header when there is no session', async () => {
    const recibidas = capturarCabeceras()

    await apiFetch('/echo')

    expect(recibidas.authorization).toBeNull()
  })

  it('should default to JSON and keep the extra headers the caller adds', async () => {
    const recibidas = capturarCabeceras()

    await apiFetch('/echo', { headers: { 'X-Custom': 'valor' } })

    expect(recibidas.contentType).toBe('application/json')
    expect(recibidas.custom).toBe('valor')
  })

  it('should post the body and return the parsed response to the caller', async () => {
    let cuerpoRecibido
    server.use(
      http.post(`${API}/users/login`, async ({ request }) => {
        cuerpoRecibido = await request.json()
        return HttpResponse.json({ success: true, data: { id_user: 7 } })
      }),
    )

    const respuesta = await apiFetch('/users/login', {
      method: 'POST',
      body: JSON.stringify({ mail: 'a@x.co', contrasena: 'x' }),
    })

    expect(cuerpoRecibido).toEqual({ mail: 'a@x.co', contrasena: 'x' })
    expect(respuesta.ok).toBe(true)
    expect((await respuesta.json()).data.id_user).toBe(7)
  })

  it('should hand back business errors (HTTP 200 with success:false) without touching the session', async () => {
    localStorage.setItem('access_token', 'jwt-123')
    server.use(http.get(`${API}/x`, () => HttpResponse.json({ success: false, message: 'Rol no encontrado' })))

    const respuesta = await apiFetch('/x')

    expect((await respuesta.json()).success).toBe(false)
    expect(getToken()).toBe('jwt-123')
  })

  describe('when the backend answers 401', () => {
    let ubicacion

    beforeEach(() => {
      // jsdom no navega: se sustituye window.location para observar la redirección
      ubicacion = { href: 'http://localhost/dashboard' }
      vi.stubGlobal('location', ubicacion)
      localStorage.setItem('access_token', 'vencido')
      localStorage.setItem('id_user', '7')
      server.use(http.get(`${API}/privado`, () => new HttpResponse(null, { status: 401 })))
    })
    afterEach(() => vi.unstubAllGlobals())

    it('should clear the whole session', async () => {
      await apiFetch('/privado')

      expect(getToken()).toBeNull()
      expect(localStorage.getItem('id_user')).toBeNull()
    })

    it('should send the person back to the login page', async () => {
      await apiFetch('/privado')

      expect(ubicacion.href).toBe('/')
    })

    it('should still return the response to the caller', async () => {
      const respuesta = await apiFetch('/privado')

      expect(respuesta.status).toBe(401)
    })
  })

  it('should not clear the session on other HTTP errors such as 500', async () => {
    localStorage.setItem('access_token', 'jwt-123')
    server.use(http.get(`${API}/roto`, () => new HttpResponse(null, { status: 500 })))

    const respuesta = await apiFetch('/roto')

    expect(respuesta.status).toBe(500)
    expect(getToken()).toBe('jwt-123')
  })

  it('should reject when the server cannot be reached', async () => {
    server.use(http.get(`${API}/caido`, () => HttpResponse.error()))

    await expect(apiFetch('/caido')).rejects.toThrow()
  })
})
