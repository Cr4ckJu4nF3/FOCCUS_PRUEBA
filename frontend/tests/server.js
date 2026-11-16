// Servidor MSW compartido: intercepta fetch a nivel de red (sin tocar el código de la app).
import { setupServer } from 'msw/node'

export const API = 'http://127.0.0.1:8000'
export const server = setupServer()
