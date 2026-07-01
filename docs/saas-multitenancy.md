# SaaS / Multi-tenancy — plan de la semana

> **Estrategia:** MVP enfocado en **UNED** (una institución, muchos estudiantes),
> diseñado para escalar a multi-institución **sin reescribir**. Defaults globales
> OK por ahora; **no** convertir a config por-tenant todavía (YAGNI + evita acoplar
> `domain → config`). Objetivo de esta semana: **marcar/aislar los seams** y
> **endurecer** lo que ya importa con un solo tenant.

Fecha de creación: 2026-06-28.

---

## Prioridad sugerida

1. **(b) Seguridad del `moodle_token`** — riesgo real, crece con cada usuario.
2. **(a) Marcadores de seams en código** — barato, deja todo greppable.
3. **(c) Endurecer `scan_all_users`** — cuando empiece a haber volumen.

---

## (b) Seguridad del token  🔒  — `[ ]`

Guardamos el `moodle_token` de cada estudiante. Para un SaaS hay que tratarlo como secreto.

- [ ] Revisar cómo se persiste (`UserModel` / repo / columna en DB): ¿texto plano?
- [ ] Definir cifrado at-rest (p. ej. Fernet/`cryptography` con clave en env `TOKEN_ENCRYPTION_KEY`, o pgcrypto).
- [ ] Cifrar al guardar / descifrar al usar (en el repositorio, no en el dominio).
- [ ] Plan de rotación de clave y migración de tokens existentes.
- [ ] Confirmar que el token **no** se loguea ni se expone en endpoints de debug.

**Archivos probables:** `src/infrastructure/db/models/user_model.py`,
`src/infrastructure/repositories/postgres_user_repository.py`, `src/config/settings.py`.

---

## (a) Marcar los seams por-tenant  🏷️  — `[ ]`

Agregar un comentario greppable `# PER-TENANT SEAM:` en cada punto + nota de migración.
**No** cambiar comportamiento todavía; solo marcar.

| # | Seam | Hoy (global) | Ubicación | Migración futura |
|---|------|--------------|-----------|------------------|
| 1 | URL de Moodle | `moodle_base_url` default UNED | `src/config/settings.py` | `User.moodle_url` (fallback global); `MoodleHttpClient` la recibe por usuario |
| 2 | Zona horaria | `timezone = America/Costa_Rica` | `settings.py`, `message_builder.py` | `User.timezone`; builder/recordatorios usan tz del usuario (hoy se lee 1 vez en `__init__`) |
| 3 | Idioma de mensajes | Español hardcodeado | `message_builder.py` | i18n + `User.language` |
| 4 | Política de notificación | `_DELIVERABLE_KEYWORDS`, `_NOISE_KEYWORDS`, exclusión de "foro" | `src/domain/entities/instruction.py` | **Inyectar** la política en `is_deliverable` (NO importar config desde el dominio) |
| 5 | Recordatorios/digest | `reminder_*`, `digest_*` | `settings.py` | preferencias por `User` |
| 6 | Modelo `User` | sin `moodle_url`/`timezone`/`language`/prefs | `src/domain/entities/user.py` | columnas nullable con fallback global |

- [ ] Marcadores `# PER-TENANT SEAM:` en los 6 puntos.

---

## (c) Endurecer `scan_all_users`  ⚙️  — `[ ]`

Con pocos usuarios da igual; con cientos, no.

- [ ] **Aislamiento de fallos por-usuario:** un token muerto / error de un usuario no debe abortar el lote (try/except por usuario + log + métrica).
- [ ] **Concurrencia controlada** (semáforo / batch) en vez de secuencial puro.
- [ ] **Rate-limit / backoff** contra la API de Moodle (evitar baneos).
- [ ] Marcar usuarios con token inválido (`is_active=False` o estado) para no reintentar infinito.
- [ ] Observabilidad: contador de éxitos/fallos por corrida.

**Archivos probables:** `src/workers/jobs/scan_all_users.py`,
`src/application/use_cases/run_guardian_scan.py`.

---

## Ya es SaaS-friendly (no tocar)

Absorción / `deliverable_refs`, token-matching, diff, snapshots por `user_id`.
Son agnósticos a institución/idioma/zona y escalan bien.

---

## Fuera de alcance esta semana (anotado, no construir)

- Config por-tenant real (esperar al 2º tenant).
- i18n completo.
- Panel de administración multi-tenant.
