# Deploy — API + Worker en Render

Dos procesos, un repo:

| Servicio | Qué corre | Arranca | Free? |
|----------|-----------|---------|-------|
| **web** (`campusguardian-api`) | API FastAPI (`uvicorn src.main:app`). **No** corre el scheduler. | HTTP | ✅ sí |
| **worker** (`campusguardian-worker`) | Scheduler APScheduler (`python -m src.workers.runner`): scan (3h) + reminders (diario) + digest (semanal). | always-on | ❌ Starter (~$7/mes) |

> **Por qué un worker aparte y no el lifespan de la API:** `main.py` no levanta el
> scheduler a propósito. El web free se duerme por inactividad (mataría los cron) y
> podría correr multi-instancia (notificaciones duplicadas). El scheduler quiere **un**
> proceso único y always-on → Background Worker.

## Prerrequisito de código (ya resuelto)

- `APScheduler==3.11.2` está en `requirements.txt` (antes solo estaba en el venv local;
  sin esto el worker fallaba al importar).
- `runner.py` ya levanta el scheduler y se mantiene vivo. No hay más cambios de código.

## Camino A — adoptar el Blueprint (`render.yaml`)

1. En Render: **New → Blueprint**, apuntá al repo. Detecta `render.yaml` y crea los dos
   servicios.
2. Render pide los secrets (`sync:false`): cargá los **valores de prod** (ver checklist).
3. El web corre `alembic upgrade head` en su `preDeployCommand` (dueño del esquema); el
   worker asume el esquema migrado.

## Camino B — agregar solo el worker a mano (menos disruptivo)

Si ya tenés el web configurado a mano y no querés que el Blueprint lo reconcilie:

1. Render: **New → Background Worker**, mismo repo.
2. **Build command:** `pip install -r requirements.txt`
3. **Start command:** `python -m src.workers.runner`
4. Copiá las env vars de prod (checklist abajo).

## Checklist de env vars (worker)

| Var | Valor | Nota |
|-----|-------|------|
| `ENVIRONMENT` | `prod` | Sin esto → Moodle **y** notifier fake → no manda nada. |
| `DATABASE_URL` | (secret) | El branch de **datos reales** (`ep-calm-surf`), no el dev vacío. Ver docs/token-recovery.md. |
| `TELEGRAM_BOT_TOKEN` | (secret) | El notifier real lo exige o la app no arranca. |
| `TOKEN_ENCRYPTION_KEY` | (secret) | **La misma** clave de prod. Otra clave = tokens irrecuperables (docs/security.md). |
| `SENTRY_DSN` | (secret, opcional) | Observabilidad. |
| `SCHEDULER_RUN_IMMEDIATELY_ON_START` | `false` | Evita un scan extra en cada restart del worker. |

> **NO** setear `USE_FAKE_NOTIFIER` en prod: el default ya da Telegram real. Ese override
> es solo para local (Telegram real + Moodle fake al desarrollar).

## Verificar que quedó real (no fake)

En los logs del **worker** tras el deploy, al arrancar debe aparecer:

```
Scheduler configured: scan=interval 3h ... | reminders=15:00 ... | digest=mon 10:00 | tz=America/Costa_Rica
```

Y cuando dispare un envío, **NO** debe verse `[FakeNotifier]`. Si aparece `[FakeNotifier]`,
el worker está en `local`/`dev` (o con `USE_FAKE_NOTIFIER=true`) y nada llega a Telegram real.
