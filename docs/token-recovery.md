# Recuperación de token vencido — plan

> **Contexto:** un `moodle_token` puede morir en cualquier momento (expira por
> política del admin, el estudiante cambia su contraseña, la UNED lo resetea
> entre cuatrimestres…). Es **inevitable** y se vuelve frecuente al crecer.
> Hoy ya lo **detectamos** (ver `MoodleTokenError`), pero el usuario se entera
> de nada y no puede arreglarlo solo. Este doc planea cerrar ese ciclo.

Fecha de creación: 2026-07-01.
Actualizado: 2026-07-03 (resiliencia: umbral de fallos consecutivos + `decrypt()`
que no degrada en silencio, a raíz del incidente de falsa desactivación).
Relacionado: `docs/saas-multitenancy.md` (sección (b) seguridad del token).

---

## Decisión de arquitectura: el backend NUNCA maneja credenciales

El token de Moodle se genera con un POST directo a:

```
POST /login/token.php   (username, password, service=moodle_mobile_app)
```

Tentación: si el backend guardara `username`+`password`, podría regenerar el
token solo al morir → recuperación transparente. **Se descarta a propósito.**
Guardar la contraseña del estudiante es un riesgo de otra magnitud que guardar
el token: la contraseña abre **todo** (correo, matrícula, notas…), se reusa en
todos lados y no es revocable sin cambiarla en todas partes; el token es de
alcance acotado (solo web services) y el admin lo revoca. Un leak de tokens se
contiene; un leak de contraseñas es un incidente de identidad completo.

**Modelo elegido:**

- La generación del token (el POST a `token.php`) la hace **la web propia** (a
  desarrollar), del lado del usuario. Las credenciales **nunca** tocan este
  backend.
- La web le entrega al backend **solo el token** (llave), vía el endpoint de
  registro / re-vínculo.
- Recuperación = redirigir al usuario a esa web para regenerar la llave; el
  backend solo recibe el token nuevo. **No** se persiste ninguna contraseña en
  ninguna capa.

Consecuencia para este plan: A y B1 **no** piden credenciales ni regeneran
token; apuntan al usuario a la web y reciben la llave ya generada.

---

## El ciclo de vida de un token muerto

Cuatro capas. Una **Capa 0** (resistir) que amortigua antes de dar por muerto un
token, más las tres del ciclo detectar → avisar → recuperar.

| Capa | Qué hace | Estado |
|------|----------|--------|
| **0. Resistir** | No dar por muerto un token por un bache: umbral de N fallos consecutivos antes de desactivar, y un fallo de **descifrado** (clave nuestra) NO desactiva | ✅ **Hecho (2026-07-03)** |
| **1. Detectar** | El scan reconoce `invalidtoken`/`invalidtimedtoken` y desactiva al usuario | ✅ Hecho (commit `57ccd93`) |
| **2. Avisar** | Decirle al usuario, por Telegram, que su vínculo expiró | ✅ **Hecho (2026-07-03, A)** |
| **3. Recuperar** | Que el usuario re-vincule su token **sin intervención manual en la DB** | ✅ **B1 hecho (endpoint `POST /v1/guardian/relink`)**; B2 conversacional diferido |

> **Estado (2026-07-03):** Capa 0 + A + B1 implementados (`token_failure_count` +
> `TokenDecryptionError`, `RelinkGuardianUseCase`, `settings.web_relink_url`). Falta: la
> **web propia** que genera la llave y llama al endpoint, y setear `WEB_RELINK_URL` real
> en prod. B2 (`/vincular` en el bot) diferido.

Sin la capa 2, un usuario deja de recibir avisos **en silencio** → cree que la
app no sirve y se va (fuga invisible). Sin la capa 3, aunque quiera arreglarlo
**no puede**: `register` falla si el usuario ya existe, y reactivar es meter mano
en Postgres a mano.

Con 2 usuarios se aguanta manual. A 20–50, cada token muerto es un usuario
perdido que ni notamos.

---

## Capa 0 — Resistir: que un bache no se disfrace de token muerto (2026-07-03)

**Incidente que la motivó.** Dos usuarios aparecieron desactivados y pareció que "el
cifrado se comió los tokens". El diagnóstico (`scripts/diagnose_prod_tokens.py`) probó lo
contrario: los tokens **descifraban bien** y seguían **vivos en Moodle**. Fue una **falsa
desactivación** disparada por un `invalidtoken` transitorio de la UNED (los dos usuarios
cayeron en la misma corrida), agravada por dos debilidades del código:

1. El scan desactivaba al **primer** `MoodleTokenError`, sin margen para un bache.
2. `TokenCipher.decrypt` devolvía el ciphertext **tal cual** ante un fallo de clave (lo
   trataba como "texto plano legacy") → ese ciphertext viajaba a Moodle → falso
   `invalidtoken`. Un problema de config nuestro se disfrazaba de token muerto.

**Fixes aplicados:**

- **Umbral de fallos consecutivos.** Nueva columna `users.token_failure_count`. El scan
  solo avisa+desactiva tras `settings.token_failure_threshold` (default **3**) corridas
  **consecutivas** con `MoodleTokenError`; un scan exitoso **resetea** el contador (con un
  `UPDATE` dirigido, sin re-cifrar el token ni pisar `last_scan_at`). Un bache no sobrevive
  a un ciclo completo de 3h, así que ya no baja a nadie. Un token muerto de verdad se avisa
  tras ~N×3h (~9h con default 3) — aceptable para tokens que viven ~12 semanas.
- **`decrypt()` deja de degradar en silencio.** Distingue tres casos: texto plano legacy
  real (devuelve tal cual), ciphertext Fernet que **ninguna clave abre** (fallo de clave →
  lanza `TokenDecryptionError`), y doble-cifrado (también `TokenDecryptionError`). Esa
  excepción **no** hereda de `MoodleTokenError`, así que el scan **no** desactiva por un
  problema de clave nuestro: cae en el handler genérico → evento en Sentry (ruidoso, para
  que lo arreglemos nosotros) en vez de matar usuarios en silencio.

> **Hallazgo colateral (no es código):** el incidente destapó un **mis-wiring de branches
> Neon** — `Render`/`.env` apuntaban al branch **dev vacío** (`ep-broad-thunder`) en vez
> del de datos reales (`ep-calm-surf`). Corregir la `DATABASE_URL` de Render a `calm-surf`
> es parte del cierre. Ver memoria del proyecto (`neon-branches-and-token-deactivation-incident`).

---

## Restricción importante descubierta al planear

**El bot de Telegram hoy solo ENVÍA; no recibe comandos.** No hay webhook ni
handlers de `/comando` (`TelegramBotNotifier` solo hace `sendMessage`). El alta
de usuarios ocurre 100% por API: `POST /v1/guardian/register`.

Esto parte la capa 3 (Recuperar) en dos niveles de esfuerzo:

- **B1 — endpoint de re-vinculación (API).** Reusa exactamente la infra actual.
  La **web propia** genera la llave y la re-envía al backend por HTTP.
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
      mensaje claro y accionable que **enlaza a la web** para regenerar la llave,
      p. ej.:
      *"🔴 Tu conexión con Moodle expiró. Guardian dejó de revisar tu campus.
      Regenerá tu llave acá para reactivar los avisos: &lt;URL de la web&gt;"*.
      La URL sale de settings (nuevo `web_relink_url` o similar), no hardcodeada.
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

**Quién lo llama:** la **web propia**, después de generar la llave con el POST a
`token.php` del lado del usuario. El backend recibe la llave ya hecha; nunca ve
credenciales.

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

## Canales de notificación (WhatsApp) — DIFERIDO

El seam ya existe: `NotifierGateway` (Protocol de dominio con `send_message` /
`send_changes` / `send_weekly_digest`). Seis use cases dependen de la interfaz,
no de Telegram. Añadir un canal = un `WhatsAppNotifier` que implemente el
Protocol + wiring en `dependencies.py`. **No se toca lógica de negocio.**

Pero WhatsApp **no** es como Telegram (que es gratis y manda texto libre a
voluntad). WhatsApp Business API tiene fricción operativa real:

- Cuenta Meta Business + número verificado + aprobación; se paga por conversación.
- Mensajes de texto libre **solo dentro de 24h** desde que el usuario te escribe.
- Fuera de esa ventana → **solo plantillas pre-aprobadas** por Meta. Los avisos
  de Guardian son proactivos y en momentos impredecibles → caerían casi siempre
  en "fuera de ventana" → habría que modelar cada aviso como plantilla aprobada
  (los mensajes ricos con formato de cursos no mapean directo).

**Decisión:** Telegram es el canal principal del MVP. WhatsApp queda como
canal #2 **cuando haya tracción** (encaja con "multi-canal" del roadmap). No es
trabajo de este plan; se documenta acá solo para dejar claro el seam y el costo.

---

## Causa raíz — INVESTIGADO (2026-07-01)

Por qué mueren los tokens de `moodle_mobile_app` (generados con `login/token.php`).
Resultó haber **dos** disparadores, no uno, y ambos importan:

1. **Expiración por tiempo (la más común).** Estos tokens **sí expiran solos**:
   por defecto a las **12 semanas (~3 meses)**, timestamp guardado en
   `validuntil` de la tabla `external_tokens`. El admin puede cambiarlo con el
   setting `tokenduration` (Security → Site policies). Al vencer, Moodle borra
   el token y las llamadas fallan con errorcode **`invalidtimedtoken`**
   ("token expired").
2. **Cambio de contraseña.** Desde 2016 (CVE-2016-7038), cambiar la contraseña
   **invalida (borra) los tokens** del usuario. Falla con **`invalidtoken`**
   ("token not found").

> ⚠️ **Corrección a nuestra hipótesis previa:** habíamos supuesto que estos
> tokens "no expiran solos". **Falso.** Expiran a los ~3 meses. Y el fix inicial
> (commit `57ccd93`) solo capturaba `invalidtoken`, así que **se le escapaba la
> muerte más común** (expiración → `invalidtimedtoken`): ese token habría
> seguido reintentando para siempre. Corregido: ahora `_INVALID_TOKEN_ERRORCODES`
> cubre **ambos** códigos.

**¿Se puede avisar ANTES de que expire (proactivo)?** En teoría sí, pero con
fricción: `validuntil` **no** lo expone `core_webservice_get_site_info` (vive
solo en la tabla `external_tokens`, no hay función WS estándar que lo lea). Para
un enfoque proactivo habría que **predecir** el vencimiento = (momento en que se
emitió la llave) + (tokenduration de la UNED). Eso requiere:
  - Confirmar el `tokenduration` real de la UNED (¿los 12 semanas por defecto o
    un valor propio?). Pendiente — necesita acceso admin o prueba empírica.
  - Guardar el `token_issued_at` al vincular/re-vincular (hoy no lo trackeamos).

**Decisión:** el enfoque **reactivo** (avisar + relink por la web) sigue siendo
la base correcta — cubre los dos disparadores, incluido el impredecible (cambio
de contraseña). Lo **proactivo** queda como mejora futura opcional *solo si*
confirmamos el `tokenduration` y trackeamos `token_issued_at`; con eso podríamos
avisar ~1 semana antes del vencimiento por tiempo (no ayuda con password change).

Relacionado con cifrado at-rest del token en `docs/saas-multitenancy.md` (b).

---

## Escenarios futuros / qué nos falta

Checklist vivo — qué queda para cerrar el ciclo con calidad de lanzamiento, por impacto.

**Bloqueantes para que el ciclo funcione end-to-end:**

- [ ] **Web propia de re-vínculo.** El aviso (A) enlaza a `WEB_RELINK_URL`, hoy **vacía**
      → el mensaje degrada a una variante sin link. Sin esta web, el usuario sabe que se
      rompió pero **no puede arreglarlo solo**. La web genera la llave (POST a
      `login/token.php`, credenciales solo en el navegador) y llama a
      `POST /v1/guardian/relink` (B1, ya existe). **Es el hueco #1 del lanzamiento.**
- [ ] **Operativo — migración en prod.** Correr `alembic upgrade head` contra `calm-surf`
      para crear `token_failure_count` (migración `d2e3f4a5b6c7`, no destructiva). Sin eso
      el scan falla al leer la columna. Idealmente lo corre Render en el deploy.
- [ ] **Operativo — `ENVIRONMENT=prod` en Render** para que el notifier real (Telegram)
      mande de verdad (en `local`/`dev` usa el FakeNotifier y nadie recibe nada).

**Robustez — siguiente capa de resiliencia:**

- [ ] **Guardia anti-caída-masiva.** El umbral (Capa 0) protege corrida-a-corrida, pero si
      Moodle tiene un outage global (o **nuestra** clave se rompe), TODOS los usuarios
      fallan a la vez y, tras N ciclos, se desactivarían todos. Regla propuesta: si en una
      corrida falla > X% de los activos, **no desactivar a nadie** y alertar a ops (es señal
      de problema sistémico, no de N tokens muertos). Es exactamente el patrón del 2-jul
      (los dos a la vez).
- [ ] **Alerta operativa sobre `TokenDecryptionError`.** Ya cae en el handler genérico →
      Sentry. Falta confirmar que Sentry esté activo en prod y con alerta: este error =
      config de clave mal = urgencia (todos los tokens ilegibles).

**Proactivo — evitar la muerte, no solo reaccionar:**

- [ ] **Aviso pre-expiración.** Avisar ~1 semana antes del vencimiento por tiempo
      (`invalidtimedtoken`). Requiere (a) guardar `token_issued_at` al vincular/re-vincular
      y (b) confirmar el `tokenduration` real de la UNED. No ayuda con cambio de contraseña
      (impredecible), pero cubre la muerte más común. Ver "Causa raíz".

**Canales / UX — diferido, con tracción:**

- [ ] **B2 — `/vincular` conversacional en el bot.** Reusa `RelinkGuardianUseCase`;
      requiere webhook + parser de comandos (no existe). Ver sección B2.
- [ ] **WhatsApp como canal #2.** Seam listo (`NotifierGateway`); fricción operativa real
      (plantillas, ventana de 24h). Ver sección de canales.

---

## Orden de ejecución sugerido

> **Actualización 2026-07-03:** Capa 0 (resiliencia), A (avisar) y B1 (endpoint relink)
> ya están **hechos**. Lo que sigue vive en "Escenarios futuros / qué nos falta" arriba;
> el orden original se conserva como contexto histórico.

1. **A** (avisar) — cierra la fuga silenciosa. La más urgente y **100% en este
   backend**; solo necesita una URL de la web en settings (puede ser placeholder
   al inicio).
2. **B1** (endpoint relink) — elimina la intervención manual en DB. El **backend**
   es independiente (se prueba con `curl`); la **UX completa** depende de que la
   web genere la llave y llame al endpoint.
3. *(investigación de causa raíz)* — confirmar que es cambio de contraseña y no
   expiración temporal (define si el enfoque reactivo es suficiente).
4. **B2** (`/vincular`) — cuando haya infra de comandos del bot. Opcional si la
   web ya cubre bien el re-vínculo.

**Dependencia externa:** A y B1 asumen que existirá una **web propia** que
genera la llave (POST a `token.php`) sin exponer credenciales al backend. El
backend se puede construir y probar antes que la web; la experiencia end-to-end
se cierra cuando la web esté.
