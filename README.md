# Obras API — CORS + Security Headers + aclaración de RBAC

## Sobre "activar Role Based Security"

Buena noticia: **ya está activo**, desde el bloque de Equipo — no es algo
nuevo que faltara encender. Repaso rápido de lo que ya cubre:

- `Usuario.rol` (`admin` / `inspector`)
- `require_admin`: bloquea con 403 cualquier endpoint reservado a admin
  (obras: crear/editar/estado; documentos; citas; visitas potenciales;
  perfil; dashboard; informes; equipo)
- `get_empresa_id`: todas las consultas de obras/visitas se filtran por
  "empresa" (el admin dueño), no por usuario individual — así admin e
  inspectores del mismo equipo ven las mismas obras
- Tabla completa de permisos por rol en el README del bloque de Equipo

Si te referías a algo más específico — por ejemplo, un tercer rol,
permisos más finos por acción (no solo admin/inspector), o vincular
inspectores a obras concretas en vez de a toda la empresa — dime
exactamente qué falta y lo construyo. Si no, considera este punto ya
resuelto.

## CORS

Antes: `allow_origins=["*"]` + `allow_credentials=True` — una
combinación que en realidad los navegadores rechazan (la spec de CORS no
permite origen comodín junto con credenciales). Ahora:

- Orígenes configurables vía `.env` → `ALLOWED_ORIGINS` (coma-separado).
  Por defecto `*` para no romperte el desarrollo actual.
- `allow_credentials=False` — correcto para tu caso, porque la
  autenticación va por `Authorization: Bearer <token>` manual, no por
  cookies de navegador. No perdemos nada quitándolo.
- Métodos y headers ya no son comodín (`*`), sino la lista concreta que
  la API realmente usa.

**Antes de publicar en producción**, cambia `ALLOWED_ORIGINS` en tu
`.env` a la URL real de cualquier panel web que construyas (esto no
afecta a la app móvil — CORS es un mecanismo de navegador, un cliente
HTTP nativo como Dio en Flutter no lo aplica).

## Security Headers

Nuevo middleware (`app/core/security_headers.py`) que añade a toda
respuesta:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (bloquea geolocalización/micro/cámara por defecto
  a nivel de navegador — no afecta a la app móvil nativa)
- `Strict-Transport-Security` **solo si `DEBUG=False`** (con HTTPS real
  detrás; en local por HTTP no tiene sentido y rompería las pruebas)

## Instalar

No hay migración ni tablas nuevas — solo código. Reinicia la API.
Opcional: añade `ALLOWED_ORIGINS` a tu `.env` si quieres restringirlo ya
(si no lo pones, sigue siendo `*` como hasta ahora).
