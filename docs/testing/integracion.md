# Pruebas de integración (BD real)

Las pruebas de API usan SQLite en memoria (rápidas, sin instalar nada). Las de `backend/api_usuarios/tests/integration/` usan **MySQL/MariaDB real** y comprueban lo que SQLite no puede mostrar.

## Qué diferencia a SQLite de MySQL aquí

| Tema | SQLite (pruebas de API) | MySQL/MariaDB (integración) | Hallazgo |
|---|---|---|---|
| Mayúsculas en comparaciones | distingue | **no** distingue (`utf8mb4_general_ci`) | H-B10 (latente) |
| Texto más largo que la columna | lo acepta | error 1406 → **500** | H-B25 |
| `ON DELETE CASCADE` | solo con `PRAGMA foreign_keys=ON` | siempre | H-B26 |
| `LONGTEXT` | alias de TEXT | tipo real (>64 KB) | probado |
| Orden de `NULL` | `NULLS LAST` válido | no existe: se usa `CASE WHEN` | regresión cubierta |

## Cómo ejecutarlas

```bash
# 1. Base de datos solo para pruebas (opción A: Docker)
docker compose -f docker-compose.test.yml up -d
export TEST_DATABASE_URL="mysql+pymysql://foccus_test:foccus_test@127.0.0.1:3307/foccus_test"

#    (opción B: tu MySQL/XAMPP local)
#    CREATE DATABASE foccus_test; y un usuario con permisos sobre ella
#    export TEST_DATABASE_URL="mysql+pymysql://root:@127.0.0.1:3306/foccus_test"

# 2. Ejecutar
cd backend/api_usuarios
pytest tests/integration
```

En PowerShell: `$env:TEST_DATABASE_URL="mysql+pymysql://..."`.

- Sin `TEST_DATABASE_URL` el directorio se **omite** (no falla).
- **Se niegan a correr** si el nombre de la base no contiene `test`: vacían todas las tablas en cada test.
- Cada test arranca con las tablas vacías; el esquema se recrea una vez por ejecución con `create_all`.

## Trampa conocida: transacciones y `REPEATABLE READ`

Una sesión con una transacción abierta ve una "foto" antigua de la BD. Si un test llama a la API (que usa otra sesión) y luego cuenta filas con la sesión del test, puede ver datos viejos. Por eso el helper `contar()` hace `commit()` antes de consultar.
