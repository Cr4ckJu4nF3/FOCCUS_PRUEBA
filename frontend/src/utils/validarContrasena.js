// Reglas de contraseña del registro, la recuperación y el perfil.
// Devuelve la lista de reglas que NO se cumplen (vacía = contraseña válida).
// Función pura: mismos datos de entrada, mismo resultado, sin React ni DOM.
export function validarContrasena(password) {
  const reglas = [];
  if (password.length < 8) reglas.push("Mínimo 8 caracteres");
  if (!/[a-z]/.test(password)) reglas.push("Una letra minúscula");
  if (!/[A-Z]/.test(password)) reglas.push("Una letra mayúscula");
  if (!/[0-9]/.test(password)) reglas.push("Un número");
  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) reglas.push("Un carácter especial");
  return reglas;
}
