import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  clearSession,
  getDeviceId,
  getToken,
  isTokenValid,
  setToken,
} from '../src/api.js'

// JWT de mentira: el frontend solo lee el payload (la firma la verifica el backend)
function fakeJwt(payload) {
  return `cabecera.${btoa(JSON.stringify(payload))}.firma`
}

describe('sesión en localStorage', () => {
  it('should return null when there is no token', () => {
    expect(getToken()).toBeNull()
  })

  it('should store and return the token', () => {
    setToken('abc')

    expect(getToken()).toBe('abc')
  })

  it.each([undefined, null, ''])('should not overwrite the token when the new one is %j', (vacio) => {
    setToken('vigente')

    setToken(vacio)

    expect(getToken()).toBe('vigente')
  })

  it('should remove the whole session when clearSession is called', () => {
    localStorage.setItem('access_token', 'abc')
    localStorage.setItem('id_user', '7')

    clearSession()

    expect(getToken()).toBeNull()
    expect(localStorage.getItem('id_user')).toBeNull()
  })
})

describe('getDeviceId', () => {
  it('should create an id the first time and reuse it afterwards', () => {
    const primero = getDeviceId()
    const segundo = getDeviceId()

    expect(primero).toBeTruthy()
    expect(segundo).toBe(primero)
    expect(localStorage.getItem('device_id')).toBe(primero)
  })

  it('should keep an id that already exists', () => {
    localStorage.setItem('device_id', 'dispositivo-previo')

    expect(getDeviceId()).toBe('dispositivo-previo')
  })
})

describe('isTokenValid', () => {
  const AHORA = new Date('2026-06-01T12:00:00Z')
  const enSegundos = (fecha) => Math.floor(fecha.getTime() / 1000)

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(AHORA)
  })
  afterEach(() => vi.useRealTimers())

  it('should be false when there is no token', () => {
    expect(isTokenValid()).toBe(false)
  })

  it('should be true when the token expires in the future', () => {
    const token = fakeJwt({ id_user: 1, exp: enSegundos(AHORA) + 60 })

    expect(isTokenValid(token)).toBe(true)
  })

  it('should be false when the token already expired', () => {
    const token = fakeJwt({ id_user: 1, exp: enSegundos(AHORA) - 1 })

    expect(isTokenValid(token)).toBe(false)
  })

  // Valor límite: el token deja de valer justo en el instante de expiración
  it('should be false at the exact expiration second', () => {
    const token = fakeJwt({ id_user: 1, exp: enSegundos(AHORA) })

    expect(isTokenValid(token)).toBe(false)
  })

  it('should be true when the token carries no expiration', () => {
    expect(isTokenValid(fakeJwt({ id_user: 1 }))).toBe(true)
  })

  it.each(['no-es-un-jwt', 'a.b', 'a.%%%.c', 'a.bm8tZXMtanNvbg==.c'])(
    'should be false when the token is malformed (%s)',
    (token) => {
      expect(isTokenValid(token)).toBe(false)
    },
  )

  it('should read the token from localStorage when none is passed', () => {
    localStorage.setItem('access_token', fakeJwt({ exp: enSegundos(AHORA) + 60 }))

    expect(isTokenValid()).toBe(true)
  })
})
