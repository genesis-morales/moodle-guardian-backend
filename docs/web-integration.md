# Integración Web ↔ Backend

> **Para quién es este doc:** quien construya la **web propia** de Moodle Guardian
> (onboarding + re-vínculo). Es el **contrato** entre esa web y este backend: qué
> endpoints existen, qué se manda, qué se recibe y qué mostrarle al usuario en cada
> caso. Los otros docs (`roadmap.md`, `token-recovery.md`, `security.md`) explican el
> *porqué*; este explica el *cómo conectarse*.

Fecha de creación: 2026-07-05.
Relacionado: `docs/token-recovery.md` (por qué existe el re-vínculo), `docs/security.md`.

---

## Regla de oro (decisión durable, NO negociable)

**El backend NUNCA ve las credenciales del estudiante.** El usuario/contraseña de
Moodle **solo** viven en el navegador el tiempo de generar la llave, y se descartan.

```
  Navegador (la web)                        Backend (esta API)
  ─────────────────                         ──────────────────
  1. usuario mete user + password
  2. POST login/token.php  ──► Moodle       (el backend NO participa)
  3. Moodle devuelve el token
  4. (opcional) get_site_info ──► Moodle     para obtener el moodle_user_id
  5. manda SOLO el token + user_id ──────►  POST /v1/guardian/register  o  /relink
                                            (recibe la llave ya hecha, nunca la password)
```

Nunca mandes `username`/`password` a este backend. No hay endpoint que los reciba, y
no debe haberlo (ver `docs/token-recovery.md`, sección "el backend NUNCA maneja
credenciales"). Guardar la contraseña es un riesgo de identidad completo; el token es
de alcance acotado y revocable.

---

## Paso 1 (lado navegador): generar la llave de Moodle

La web hace estas llamadas **directo a Moodle** desde el navegador. El backend no interviene.

### 1a. Obtener el token

```
POST https://aprende.uned.ac.cr/login/token.php
Body (form-urlencoded):
  username = <lo que escribió el usuario>
  password = <lo que escribió el usuario>
  service  = moodle_mobile_app
```

Respuesta OK: `{ "token": "abc123..." }`
Respuesta error (credenciales malas): `{ "error": "Invalid login, please try again" }`
→ mostrar "usuario o contraseña incorrectos", **no** llamar al backend.

### 1b. Obtener el `moodle_user_id`

El token por sí solo no dice a qué usuario pertenece. Se obtiene con:

```
GET/POST https://aprende.uned.ac.cr/webservice/rest/server.php
  wstoken            = <el token del paso 1a>
  wsfunction         = core_webservice_get_site_info
  moodlewsrestformat = json
```

El campo `userid` de la respuesta es el `moodle_user_id` que pide el backend.

> ⚠️ Tras estos pasos, **descartar la contraseña** (no guardarla en variables globales,
> ni en `localStorage`, ni mandarla a ningún lado). Ver "Seguridad en el front" abajo.

---

## Paso 2 (lado backend): entregar la llave

Base URL del backend: la de Render (prod) o `http://localhost:8000` (dev).
Ambos endpoints reciben y devuelven **JSON** y viven bajo el prefijo `/v1/guardian`.

### `POST /v1/guardian/register` — alta de un usuario nuevo

**Request body:**
```json
{
  "moodle_user_id": 12345,          // int > 0  (del paso 1b)
  "moodle_token": "abc123...",      // string no vacío (del paso 1a)
  "telegram_chat_id": "987654321"   // opcional (string o null)
}
```

**Respuesta 201 Created** — usuario nuevo creado (`message: "Usuario registrado correctamente."`):
```json
{
  "user_id": 1,
  "moodle_user_id": 12345,
  "is_active": true,
  "telegram_linked": true,
  "courses_count": 6,
  "message": "Usuario registrado correctamente."
}
```

**Respuesta 200 OK** — el usuario ya existía (no se vuelve a crear; el `message` lo indica).

### `POST /v1/guardian/relink` — re-vincular un token muerto

Es a donde llega el usuario desde el **link del aviso de Telegram** (`WEB_RELINK_URL`)
cuando su token expiró o fue revocado. Actualiza el token y **reactiva** al usuario.

**Request body:**
```json
{
  "moodle_user_id": 12345,      // int > 0
  "moodle_token": "nueva..."    // string no vacío (llave recién generada)
}
```
(No lleva `telegram_chat_id`: el usuario ya existe, no se re-vincula el chat.)

**Respuesta 200 OK:**
```json
{
  "user_id": 1,
  "moodle_user_id": 12345,
  "is_active": true,
  "message": "Vínculo reactivado."
}
```

---

## Tabla de errores → qué mostrarle al usuario

| Endpoint | Status | Cuándo | Mensaje sugerido en la web |
|----------|--------|--------|----------------------------|
| ambos | **401** | El token no valida contra Moodle | "La llave no es válida. Volvé a generarla e intentá de nuevo." |
| `/relink` | **404** | El `moodle_user_id` no está registrado | "No encontramos tu cuenta. ¿Querés **registrarte** primero?" → mandar a onboarding |
| ambos | **422** | Body mal formado (falta un campo, `moodle_user_id ≤ 0`, token vacío) | Error de validación de tu form; no debería llegar si validás antes |
| ambos | **5xx** | Error del servidor | "Algo falló de nuestro lado. Reintentá en un momento." |

- El **cuerpo del error** viene como `{ "detail": "<texto>" }` (formato estándar de FastAPI).
- **Diferencia clave register vs relink:** `register` con un usuario que ya existe devuelve
  **200** (no error); `relink` con un usuario que **no** existe devuelve **404**. Elegí el
  endpoint según el flujo: onboarding → `register`, link del aviso → `relink`.

---

## Requisitos de infraestructura (para que la web pueda conectarse)

1. **CORS.** El backend solo acepta llamadas de navegador desde los orígenes listados en
   la env var `CORS_ALLOWED_ORIGINS` (coma-separada). En **prod hay que setear el dominio
   real de la web** ahí (p. ej. `CORS_ALLOWED_ORIGINS=https://guardian.tudominio.com`).
   El default cubre solo dev local (`http://localhost:5173`, `http://localhost:3000`).
   Si la web carga desde un origen no listado, el navegador **bloquea** la llamada.
2. **HTTPS.** Todo el tráfico (web→Moodle y web→backend) va sobre HTTPS. El token viaja en
   el body; sin TLS quedaría expuesto.
3. **`WEB_RELINK_URL`** (en el backend) debe apuntar a la página de **re-vínculo** de esta
   web, porque es el link que se manda en el aviso de Telegram cuando un token muere.

---

## Seguridad en el front (checklist)

- [ ] La **contraseña** solo existe en memoria durante los pasos 1a/1b; nunca en
      `localStorage`/`sessionStorage`, cookies, ni logs.
- [ ] El **token** se manda una vez al backend y se descarta; no persistirlo en el navegador
      salvo lo mínimo imprescindible para el flujo.
- [ ] Nada de tokens ni contraseñas en `console.log` ni en telemetría/analytics del front.
- [ ] Servir la web sobre **HTTPS** y con headers de seguridad razonables (CSP básica).

Ver `docs/security.md` para el modelo de amenazas del token del lado backend.
