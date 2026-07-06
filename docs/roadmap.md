# Moodle Guardian — Rumbo del SaaS (roadmap vivo)

> Documento **vivo**: se actualiza a medida que surgen ideas. Es la fuente de
> verdad del rumbo del producto. Última actualización: 2026-07-02.

## Visión (1 línea)
Un asistente académico que vigila Moodle por vos y te avisa (por tu canal
preferido) lo que importa —entregas, anuncios, mensajes— y al que le podés
preguntar en lenguaje natural qué tenés pendiente.

## Principios
- **Clean architecture**: dominio agnóstico; canales/Moodle/LLM son adapters.
- **Señal, no ruido**: solo notificar lo accionable (ya lo aplicamos con foros/manuales).
- **Multi-canal y preferencias por usuario** como concepto central.
- **Seguridad primero**: guardamos credenciales de estudiantes; es sagrado.
- **Start-UNED-scale-later**: defaults globales hoy, seams marcados (ver `saas-multitenancy.md`).

## Estado actual (lo que ya existe)
- Scan periódico → snapshot → diff → notificación Telegram.
- Entidades: assignments, eventos, foros (evento), instrucciones (PDF) con absorción.
- Recordatorios y digest semanal. Endpoints de cron + debug.
- Puerto `NotifierGateway` (Telegram) → **base lista para multi-canal**.

---

## Iniciativas

Leyenda: **Valor** / **Esfuerzo** / **Riesgo** (Alto/Medio/Bajo).

### 1. Multi-canal: WhatsApp + Gmail (además de Telegram)
**Valor A · Esfuerzo M · Riesgo M**
- Encaja perfecto con el puerto `NotifierGateway`: un adapter por canal + **preferencia de canal por usuario**. Patrón Strategy.
- ⚠️ **Realidad WhatsApp**: la API de WhatsApp Business (Meta/Twilio) exige aprobación, **plantillas pre-aprobadas** para mensajes proactivos fuera de la ventana de 24 h, y **cuesta por mensaje**. No es "gratis como Telegram".
- 💰 **Decisión de negocio (definida):** WhatsApp es **feature premium**, su costo se cubre con **suscripción**. → habilita modelo **free (Telegram/email) vs premium (WhatsApp)**. Ver init. 11.
- ✅ **Email (Gmail/SMTP o SendGrid/SES/Resend)**: barato y fácil; ideal para digest/resumen. Cuidar deliverability (SPF/DKIM).
- **Mi recomendación de orden:** Email primero (rápido, sin fricción, canal free) → WhatsApp después (tier premium).
- **Depende de:** modelo de *preferencias por usuario* (canales + tipos de aviso).

### 2. Más fuentes de Moodle: anuncios, mensajes, foros
**Valor A · Esfuerzo A · Riesgo M**
- **Anuncios generales (foro Novedades/News)** → 🟢 alto valor. API probable: `mod_forum_get_forum_discussions`.
- **Mensajes privados de Aprende** → 🟢 alto valor. API probable: `core_message_get_conversations` / `core_message_get_messages`.
- **Foro de consultas (Q&A)** → 🟡 valor dudoso/ruidoso. Sugiero **opt-in** por usuario, no por defecto.
- ⚠️ **"Tiempo real" = avisar apenas el scan lo detecta** (no hay webhooks en Moodle; es polling). Para que *se sienta* inmediato en mensajes/anuncios hay que **bajar el intervalo** (hoy `scheduler_interval_hours=3`) para esas fuentes → sube carga de API y obliga a pensar la escala del scan (ver init. 8). 💡 Posible: intervalo corto solo para mensajes/anuncios, largo para el resto.
- **Esto generaliza el modelo**: hoy diff de assignments/eventos; hay que extenderlo a *posts* y *mensajes* (rastrear último id/fecha visto por usuario+fuente).
- 💡 **Sugerencia:** introducir un concepto unificado de **"fuente rastreable"** + diff genérico, para que agregar fuentes nuevas sea barato.

### 3. Bot conversacional ("¿qué tengo pendiente?", "¿tengo mensajes?")
**Valor A · Esfuerzo M · Riesgo M**
- Es una **capa de consulta** sobre datos que ya recolectamos. Entrada por webhook (ya hay `webhooks.py`).
- **Dos niveles:**
  - (a) **Comandos** (`/pendientes`, `/mensajes`, `/nuevo`): determinista, barato, confiable. **Empezar acá.**
  - (b) **Lenguaje natural con LLM (Claude)**: flexible pero cuesta tokens y necesita parseo de intención. Capa encima de (a).
- 💡 Con Claude se puede usar **tool-use**: el modelo llama "herramientas" que consultan los datos del usuario. Cuidar costo/latencia. (Usar el modelo más capaz vigente al construirlo.)
- **Depende de:** init. 2 (para que haya "mensajes/foros" que consultar).

### 4. Web sencilla para registro
**Valor M · Esfuerzo M · Riesgo M**
- Hoy el registro es API + vínculo Telegram. Una web suaviza el onboarding.
- ⚠️ **Punto sensible:** ¿cómo obtiene el usuario su **token de Moodle**? Si lo pega a mano → fricción + superficie de seguridad + el token expira (problema de retención).
- 💡 **Investigar SSO/OAuth de la Moodle de UNED** en vez de pegar token: mejor UX y seguridad. Si no existe, al menos flujo guiado + manejo cuidadoso (HTTPS, no loguear, cifrar).
- **Mantenerlo simple**: página estática/SPA mínima contra la API actual. No meter framework pesado.

### 5. Seguridad (transversal, siempre presente)
**Valor A · Esfuerzo M · Riesgo A**
- Ya hay base en `saas-multitenancy.md` (cifrado del token). Ampliar a checklist permanente:
  - [x] `moodle_token` **cifrado at-rest** (Fernet/`MultiFernet`) + rotación de clave. ✅ 2026-07-02 — ver `docs/security.md`.
  - [ ] Tokens nunca en logs ni en endpoints de debug.
  - [ ] HTTPS en todo; auth/rate-limit en endpoints públicos.
  - [ ] PII (chat_id, nombres, datos Moodle): retención, borrado a pedido, consentimiento.
  - [ ] Manejo de secretos (env/secret manager), no en repo.
  - [x] Detección de token **muerto** (expirado `invalidtimedtoken` / revocado `invalidtoken`) → avisar + relink. ✅ 2026-07-03 (A + B1). Falta la web que genera la llave. Ver `docs/token-recovery.md`.
  - [x] **Resiliencia (Capa 0)**: no falsa-desactivación. Umbral de N fallos consecutivos (`token_failure_count`) + `decrypt()` que lanza `TokenDecryptionError` en vez de mandar basura a Moodle. ✅ 2026-07-03 — ver `docs/token-recovery.md`.
  - [ ] **Guardia anti-caída-masiva**: si en una corrida falla > X% de usuarios, no desactivar a nadie y alertar (outage global / clave rota). Pendiente.
- ⚠️ El token **vence ~12 semanas**: si se filtra, sigue siendo válido hasta que caduque, y una fuga de la DB expone los de **todos los usuarios a la vez** → el cifrado at-rest y el no-loguearlo son **críticos**.
- 💡 Hacer un **threat-model lite** y un `docs/security.md` dedicado.

### 6. Factory para entornos (local/dev/prod)
**Valor M · Esfuerzo B · Riesgo B**
- Composition root por entorno: en local, **fake notifier** y **fake Moodle**; en prod, los reales. Basado en `settings.environment`.
- ✅ Barato y alto valor para velocidad de desarrollo y tests (no pegarle a UNED en dev).
- **Hacerlo temprano**: desbloquea testear todo lo demás sin fricción. Apóyate en `dependencies.py` que ya existe.

---

## 💡 Sugerencias propias (no estaban en tu lista)

### 7. Modelo de **preferencias por usuario** (fundacional)
Canales activos, tipos de aviso (entregas/foros/mensajes/anuncios), horario de
silencio, idioma, zona horaria. **Habilita** init. 1 y 2 y conecta con los seams
multi-tenant. Probablemente lo primero a diseñar en datos.

### 8. **Escala del scan** (cola de trabajos)
Con más usuarios + polling más frecuente (init. 2), el loop único `scan_all_users`
no alcanza. Pensar en **cola de tareas** (Arq/Celery/RQ) con job por usuario,
aislamiento de fallos y rate-limit. Decisión arquitectónica con peso.

### 9. **Observabilidad**
Logging estructurado, error tracking (Sentry), métricas (scan ok/fallo, entregas
de notificación), health checks. En un SaaS necesitás enterarte cuando se rompe
para *un* usuario.

### 10. **Ciclo de vida del token de Moodle**
**Corregido (2026-07-02):** el token de Moodle **sí expira** (~12 semanas; error
`invalidtimedtoken`), además de poder ser **revocado** (`invalidtoken`; ej. cambio de
contraseña). Ambos casos ya se detectan en `http_client.py` y marcan al usuario. → El
re-onboarding por vencimiento **es necesario** (avisar por Telegram + relink por web;
ver `docs/token-recovery.md`). ⚠️ Un token válido filtrado da acceso hasta que caduca,
y una fuga de DB expone los de todos a la vez → refuerza init. 5 (cifrado at-rest, ✅ hecho).

**Resiliencia añadida (2026-07-03):** tras un incidente de **falsa desactivación** (un
`invalidtoken` transitorio bajó a dos usuarios con tokens sanos), se agregó una **Capa 0**:
umbral de fallos consecutivos antes de desactivar (`token_failure_count`) y `decrypt()` que
grita (`TokenDecryptionError`) en vez de mandar ciphertext a Moodle. Pendiente: guardia
anti-caída-masiva y aviso **proactivo** pre-expiración (necesita `token_issued_at` +
`tokenduration` real de la UNED). Ver `docs/token-recovery.md`.

> Nota histórica: una versión previa afirmaba "el token no expira"; la investigación
> posterior lo desmintió. El código (`_INVALID_TOKEN_ERRORCODES`) ya lo contemplaba.

### 11. **Modelo de negocio + economía unitaria**
**Definido:** modelo de **suscripción**. Tiers tentativos: **free** (Telegram/email) vs
**premium** (WhatsApp y, a futuro, bot NL / fuentes extra). El feature flag de tier
se conecta con init. 7 (preferencias por usuario).
- Costo por usuario a vigilar: mensajes WhatsApp (premium), tokens LLM del bot, email.
- Definir qué entra en cada tier y el precio que cubre el costo variable + margen.

### 12. **Multi-campus de UNED (`aprende U` + `educa U`)** 🆕
**Valor A · Esfuerzo A · Riesgo M**
- UNED tiene **dos campus** Moodle; un estudiante puede usar **ambos**, con **2 tokens
  distintos**. Rompe el supuesto actual *1 usuario = 1 token = 1 campus*.
- Solución: extraer una entidad **`MoodleConnection`** (1..N por usuario) — es la
  expansión concreta del **seam #1** (`moodle_url` por usuario) de `saas-multitenancy.md`,
  que deja de ser especulativo. Token-recovery, scan y snapshots pasan a ser **por conexión**.
- **Diseño detallado en `docs/multi-campus-and-sources.md`.** Se diseña junto con init. 2
  (fuentes) porque comparten la llave de snapshot `(connection_id, source_type, item_id)`.

### 13. **Sinks: Google Calendar + Notion** 🆕
**Valor A · Esfuerzo M · Riesgo M**
- **Destinos de sincronización**, no fuentes ni canales: escriben los entregables hacia
  afuera (el usuario los ve en su GCal/Notion). Puerto nuevo `DeliverableSyncPort`.
- Dependen de **OAuth por usuario** (otro secreto a cifrar) → se apoyan en preferencias
  (#7) y seguridad (#5). Aditivos e independientes. Ubicación: **Fase 2**.
- Ver `docs/multi-campus-and-sources.md` (eje C).

---

## Secuencia sugerida (fases)

**Fase 0 — Cimientos (habilitan todo lo demás)**
- (5) Seguridad: cifrado del token. ✅ **Hecho (2026-07-02)** — ver `docs/security.md`.
- (6) Factory de entornos + fake Moodle. ✅ **Hecho (2026-07-02)** — perfiles
  local/dev/prod en `dependencies.py`; fakes; branch dev en Neon. ⚠️ Render debe
  setear `ENVIRONMENT=prod`.
- (7) Modelo de preferencias por usuario. ⬜ pendiente (próximo).

**Fase 1 — Valor visible rápido**
- (0) **Fuente rastreable genérica** — cimiento del diff/persistencia para que agregar
  fuentes sea barato (ver `docs/multi-campus-and-sources.md` eje A). Prerequisito de lo demás.
- (2a) **Anuncios (foro Novedades/News) + Mensajes privados** — 1ª tanda de fuentes nuevas,
  alto valor. Ambas sobre el modelo genérico. (Mensajes movido desde Fase 2, 2026-07-05.)
- (12) **Multi-campus (`educa U`)** — entidad `MoodleConnection`, después de las fuentes
  para no reescribirlas (el modelo se diseña campus-ready desde ya).
- (1) Email como 2º canal.
- (3a) Bot por **comandos** (`/pendientes`, `/mensajes`, `/nuevo`).

**Fase 2 — Profundizar**
- (8) Cola de trabajos (cuando el volumen lo pida).
- (3b) Bot con lenguaje natural (LLM).
- (4) Web de registro (idealmente con SSO).
- (13) **Sinks: Google Calendar + Notion** (OAuth por usuario, sobre preferencias #7).
- (1) WhatsApp (si la economía cierra).
- (2) Foro de consultas Q&A (opt-in).

**Transversal y continuo:** (5) Seguridad, (9) Observabilidad, (10) Token lifecycle.

---

## Escala y costos (cron vs cómputo)

**Clave:** un cron trigger dispara `scan_all_users`, que adentro recorre a TODOS
los usuarios. **Más usuarios ≠ más cron jobs.**

**Presupuesto de cron (fijo, no escala con usuarios):**
| Job | Cadencia | Crece con usuarios |
|---|---|---|
| `scan` | 3h | ❌ |
| `reminders` | diario | ❌ |
| `digest` | semanal | ❌ |
| *(futuro)* `scan-messages` | 15-30 min | ❌ |

→ Hoy **3** cron jobs; con mensajes/anuncios en cadencia corta, **4**. Y se queda ahí.
cron-job.org/UptimeRobot cobran por *jobs + intervalo*, no por usuarios → tier barato/gratis alcanza.

**Lo que SÍ escala con usuarios:** cómputo (server/worker Render) + variable por-mensaje
(WhatsApp/email/LLM). No los cron.

**Gates de escala (cuándo meter más gente):**
- ✅ **Aislamiento de fallos por-usuario ya existe** (`scan_all_users.py`): un token muerto no rompe el lote. Bloqueante #1 ya resuelto.
- **Ahora → ~100-150 usuarios:** scan secuencial a 3h alcanza. Pre-requisito para gente real: **cifrar token + observabilidad básica** (Fase 0). No necesita colas.
- **~150 → ~500:** **concurrencia acotada** (`asyncio.Semaphore`, 5-10 en paralelo). ⚠️ respetar el pool de conexiones de Neon (scale-to-zero + límite).
- **~500+ o cadencias cortas:** colas/workers (init. 8).
- Orden de magnitud: ~8-11 llamadas Moodle por usuario → ~3-6s/usuario.

💡 Con colas (#8) el cron se simplifica a **encolar**; los workers (cómputo aparte) hacen el trabajo → escalás cómputo sin tocar el presupuesto de cron.

## Decisiones abiertas (para resolver)
- ¿La Moodle de UNED ofrece SSO/OAuth, o seguimos con token pegado?
- ¿Qué intervalo de scan para mensajes/anuncios? (p. ej. 15–30 min para "sentirse" inmediato vs 3h actual).
- ¿El bot NL desde el inicio o comandos primero? (costo vs flexibilidad).
- ¿Qué entra en free vs premium, y a qué precio? (define la economía).
- ¿Cola de tareas ahora o cuando el scan secuencial se quede corto?

## Decisiones ya tomadas
- ✅ WhatsApp = tier **premium**, cubierto por **suscripción** (no bloquea por costo).
- ✅ Token de Moodle **expira ~12 semanas** (+ revocable) → re-onboarding necesario por vencimiento y revocación; token cifrado at-rest (✅ 2026-07-02).
- ✅ "Tiempo real" = avisar apenas el scan detecta (polling, no push).

## Backlog / ideas futuras
- (anotar acá lo que vaya surgiendo)
