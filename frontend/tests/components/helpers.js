// Respuesta falsa de fetch/apiFetch: { ok, json() }
export const reply = (body, ok = true) => ({ ok, json: async () => body })
