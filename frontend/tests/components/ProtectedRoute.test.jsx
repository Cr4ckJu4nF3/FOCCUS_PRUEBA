import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import ProtectedRoute from '../../src/screen/ProtectedRoute.jsx'

const fakeJwt = (payload) => `cabecera.${btoa(JSON.stringify(payload))}.firma`
const enUnaHora = () => Math.floor(Date.now() / 1000) + 3600
const haceUnaHora = () => Math.floor(Date.now() / 1000) - 3600

function renderAt(ruta) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route path="/" element={<h1>Página de inicio</h1>} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <h1>Panel privado</h1>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  it('should render the private page when the session token is valid', () => {
    // Arrange
    localStorage.setItem('access_token', fakeJwt({ id_user: 1, exp: enUnaHora() }))

    // Act
    renderAt('/dashboard')

    // Assert
    expect(screen.getByRole('heading', { name: 'Panel privado' })).toBeInTheDocument()
  })

  it('should redirect to the home page when there is no token', () => {
    renderAt('/dashboard')

    expect(screen.getByRole('heading', { name: 'Página de inicio' })).toBeInTheDocument()
    expect(screen.queryByText('Panel privado')).not.toBeInTheDocument()
  })

  it('should redirect to the home page when the token already expired', () => {
    localStorage.setItem('access_token', fakeJwt({ id_user: 1, exp: haceUnaHora() }))

    renderAt('/dashboard')

    expect(screen.getByRole('heading', { name: 'Página de inicio' })).toBeInTheDocument()
  })

  it('should redirect to the home page when the token is malformed', () => {
    localStorage.setItem('access_token', 'basura')

    renderAt('/dashboard')

    expect(screen.getByRole('heading', { name: 'Página de inicio' })).toBeInTheDocument()
  })
})
