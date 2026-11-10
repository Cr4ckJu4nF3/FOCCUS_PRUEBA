import { describe, expect, it } from 'vitest'
import { validarContrasena } from '../src/utils/validarContrasena.js'

describe('validarContrasena', () => {
  it('should return an empty list when the password meets every rule', () => {
    // Arrange
    const password = 'Foccus#2026'

    // Act
    const faltantes = validarContrasena(password)

    // Assert
    expect(faltantes).toEqual([])
  })

  it('should list every rule when the password is empty', () => {
    expect(validarContrasena('')).toEqual([
      'Mínimo 8 caracteres',
      'Una letra minúscula',
      'Una letra mayúscula',
      'Un número',
      'Un carácter especial',
    ])
  })

  it.each([
    ['sin minúscula', 'FOCCUS#2026', 'Una letra minúscula'],
    ['sin mayúscula', 'foccus#2026', 'Una letra mayúscula'],
    ['sin número', 'Foccus#Pass', 'Un número'],
    ['sin carácter especial', 'Foccus2026', 'Un carácter especial'],
    ['muy corta', 'Fo#1', 'Mínimo 8 caracteres'],
  ])('should report only the missing rule when the password is %s', (_caso, password, regla) => {
    expect(validarContrasena(password)).toEqual([regla])
  })

  // Valor límite de la regla de longitud: 7 falla, 8 pasa
  it('should reject a 7-character password and accept an 8-character one', () => {
    expect(validarContrasena('Abcde#1')).toContain('Mínimo 8 caracteres')
    expect(validarContrasena('Abcdef#1')).not.toContain('Mínimo 8 caracteres')
  })

  it.each(['!', '@', '#', '$', '%', '&', '*', '-', '_', '.', ',', '?', '/', '\\', '|'])(
    'should accept %s as a special character',
    (simbolo) => {
      expect(validarContrasena(`Abcdef1${simbolo}`)).toEqual([])
    },
  )

  it('should not treat a space or an accented letter as a special character', () => {
    expect(validarContrasena('Abcdef1 ñ')).toContain('Un carácter especial')
  })
})
