# Recuperación de token vencido — plan

> **Contexto:** un `moodle_token` puede morir en cualquier momento (expira por
> política del admin, el estudiante cambia su contraseña, la UNED lo resetea
> entre cuatrimestres…). Es **inevitable** y se vuelve frecuente al crecer.
> Hoy ya lo **detectamos** (ver `MoodleTokenError`), pero el usuario se entera
> de nada y no puede arreglarlo solo. Este doc planea cerrar ese ciclo.

Fecha de creación: 2026-07-01.
Relacionado: `docs/saas-multitenancy.md` (sección (b) seguridad del token).

---

## El ciclo de vida de un token muerto

Tres capas. Solo la primera existe hoy.

| Capa | Qué hace | Estado |
|------|----------|--------|
| **1. Detectar** | El scan reconoce `invalidtoken` y desactiva al usuario | ✅ Hecho (commit `57ccd93`) |
| **2. Avisar** | Decirle al usuario, por Telegram, que su vínculo expiró | ❌ **Este plan (A)** |
| **3. Recuperar** | Que el usuario re-vincule su token **sin intervención manual en la DB** | ❌ **Este plan (B)** |

Sin la capa 2, un usuario deja de recibir avisos **en silencio** → cree que la
app no sirve y se va (fuga invisible). Sin la capa 3, aunque quiera arreglarlo
**no puede**: `register` falla si el usuario ya existe, y reactivar es meter mano
en Postgres a mano.

Con 2 usuarios se aguanta manual. A 20–50, cada token muerto es un usuario
perdido que ni notamos.

---

## Restricción importante descubierta al planear

**El bot de Telegram hoy solo ENVÍA; no recibe comandos.** No hay webhook ni
handlers de `/comando` (`TelegramBotNotifier` solo hace `sendMessage`). El alta
de usuarios ocurre 100% por API: `POST /v1/guardian/register`.

Esto parte la capa 3 (Recuperar) en dos niveles de esfuerzo:

- **B1 — endpoint de re-vinculación (API).** Reusa exactamente la infra actual.
  El usuario (o el front que uses para registrar) re-envía token por HTTP.
  **Pequeño, sin infra nueva.**
- **B2 — re-vinculación conversacional (`/vincular` en el chat).** Verdadero
  self-service desde Telegram, pero **requiere construir primero todo el
  receptor de webhook + parser de comandos del bot**, que hoy no existe.
  **Grande; es un proyecto aparte.**

**Recomendación:** hacer **A + B1 ahora** (chicas, quitan el riesgo de fuga
silenciosa y la intervención manual en DB). Dejar **B2** para cuando exista la
infra de comandos del bot (o cuando el front de registro ya cubra el re-envío).

---

## A. Avisar por Telegram cuando el token muere

**Dónde:** en `scan_all_users_job`, justo en el `except MoodleTokenError`
que ya existe (donde hoy solo se desactiva).

**Qué cambia:**

- [ ] `NotificationMessageBuilder`: nuevo `build_token_expired_message()` →
      mensaje claro y accionable, p. ej.:
      *"🔴 Tu conexión con Moodle expiró. Guardian dejó de revisar tu campus.
      Volvé a vincular tu token para reactivar los avisos: <cómo>."*
      Implementarlo en `TelegramMessageBuilder` (HTML, mismo estilo que los demás).
- [ ] En el job: **antes** de desactivar, intentar enviar el aviso al
      `telegram_chat_id` del usuario. Envolver en `try/except` — un fallo de
      envío **no** debe impedir la desactivación ni tumbar el job (mismo criterio
      que el `save` del scan_run).
- [ ] Inyectar el notifier en el job (hoy solo tiene repos + scan use case).
      Vía `get_telegram_notifier()` / `get_telegram_message_builder()` de
      `dependencies.py`, consistente con el resto.

**Anti-spam (gratis):** al desactivar al usuario en la misma corrida, sale de
`list_active()` → las próximas corridas **no** lo vuelven a ver → **el aviso se
manda una sola vez**. No hace falta un flag "ya avisado".

**Tests:**
- [ ] Con token inválido y `telegram_chat_id` presente → se llama al notifier
      con el mensaje de token expirado **y** se desactiva al usuario.
- [ ] Si el envío del aviso lanza excepción → el usuario **igual** se desactiva
      (el fallo se traga y loguea).
- [ ] Usuario sin `telegram_chat_id` → no revienta; desactiva igual.

---

## B1. Endpoint de re-vinculación (API)

**Objetivo:** actualizar el token y **reactivar** al usuario en un solo paso,
sin pasar por el error "ya registrado" de `register`.

**Diseño (nuevo use case, no tocar `RegisterGuardianUseCase`):**

- [ ] `RelinkGuardianUseCase.execute(moodle_user_id, moodle_token)`:
      1. `validate_token(moodle_token)` contra Moodle → si inválido,
         `RegistrationError` (o `MoodleTokenError`) → 401/400.
      2. `get_by_moodle_user_id` → si no existe, 404 (re-vincular ≠ registrar).
      3. Setear `user.moodle_token = <nuevo>`, `user.is_active = True`,
         `user_repository.update(user)`.
      4. (Opcional) mandar un Telegram de confirmación ("✅ Vínculo reactivado").
- [ ] Endpoint `POST /v1/guardian/relink` con body
      `{ moodle_user_id, moodle_token }` (schema nuevo, análogo a
      `RegisterGuardianRequest` sin `telegram_chat_id`).
- [ ] Wiring en `dependencies.py`: `get_relink_guardian_use_case()`.

**Por qué use case aparte y no "register que hace upsert":** mezclar alta y
re-vínculo en un solo flujo enturbia las reglas (¿reactiva?, ¿pisa chat_id?,
¿qué status devuelve?). Separado, cada uno tiene una responsabilidad clara y
`register` sigue rechazando duplicados como hoy.

**Tests:**
- [ ] Token válido + usuario existente inactivo → token actualizado + `is_active=True`.
- [ ] Usuario inexistente → 404 (no crea).
- [ ] Token inválido → error de validación, no toca la DB.

---

## B2. Re-vinculación conversacional (`/vincular`) — DIFERIDO

Requiere infra que hoy no existe; se lista para dimensionar, **no** para ahora.

- [ ] Receptor de webhook de Telegram (`POST /telegram/webhook`) + `setWebhook`.
- [ ] Parser de comandos y máquina de estados mínima (`/vincular` → pedir token
      → validar → llamar a `RelinkGuardianUseCase`).
- [ ] Identidad: mapear `telegram_chat_id` → usuario (ya lo guardamos), para no
      pedir `moodle_user_id` en el chat.
- [ ] Seguridad del webhook (secret token de Telegram, validar origen).

Cuando exista esto, B2 reusa `RelinkGuardianUseCase` de B1 tal cual. Por eso
B1 primero: deja la lógica lista para ambos canales.

---

## Fuera de alcance de este plan (investigación siguiente)

Por qué mueren los tokens en la UNED y si se puede mitigar de raíz:

- ¿El token trae `validuntil` en `core_webservice_get_site_info`? Si sí, se
  puede **avisar antes** de que venza (proactivo, no reactivo).
- ¿Cómo obtiene hoy el token el estudiante? Si es pegado a mano, es frágil; si a
  futuro se usa login usuario/contraseña, el token se **regenera solo**.
- Encaja con `docs/saas-multitenancy.md` (b): cifrado at-rest del token.

Esto depende de cómo esté configurado el Moodle de la UNED → se decide con datos
tras investigar, no aquí.

---

## Orden de ejecución sugerido

1. **A** (avisar) — cierra la fuga silenciosa. La más urgente.
2. **B1** (endpoint relink) — elimina la intervención manual en DB.
3. *(investigación de causa raíz)* — decide si vale un enfoque proactivo.
4. **B2** (`/vincular`) — cuando haya infra de comandos del bot.
