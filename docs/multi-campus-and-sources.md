# Multi-campus + Fuentes rastreables — diseño

> **Estado:** PROPUESTA de arquitectura (a confirmar). Documenta la dirección para
> tres cosas que llegaron juntas y tocan el mismo modelo de datos:
> 1. **2º campus de UNED** (`educa U`, además de `aprende U`) → un usuario puede
>    tener **2 tokens** distintos.
> 2. **Foros y anuncios** como fuentes nuevas (init. 2 del roadmap).
> 3. **Google Calendar / Notion** como destinos de sincronización (sinks).
>
> El objetivo de este doc es **diseñar los ejes juntos** aunque se **construyan** en
> secuencia, para no rehacer el modelo de datos dos veces.

Fecha de creación: 2026-07-05.
Relacionado: `docs/roadmap.md` (init. 1, 2, 7), `docs/saas-multitenancy.md` (seam #1),
`docs/token-recovery.md` (relink pasa a ser por conexión).

---

## El problema en una línea

Hoy el modelo asume **1 usuario = 1 token = 1 campus**. Los tres pedidos rompen ese
supuesto por dos ejes distintos que conviene no confundir:

| Eje | Pregunta | Hoy | Futuro |
|-----|----------|-----|--------|
| **A — QUÉ se rastrea** | ¿qué tipos de ítem vigilo? | assignments, eventos | + posts de foro, anuncios, mensajes |
| **B — DE DÓNDE** | ¿de qué campus/cuenta? | 1 campus (aprende, URL global) | N campus por usuario (aprende + educa) |
| **C — HACIA DÓNDE** | ¿a qué destinos sincronizo? | Telegram (notificación) | + Google Calendar, Notion (sinks) |

**Regla de oro del diseño:** la llave de un snapshot/ítem debe ser
`(connection_id, source_type, item_id)` **desde el día uno**. Con eso, agregar
fuentes (eje A) o campus (eje B) no obliga a reescribir lo ya hecho.

---

## Eje B — Multi-campus: la entidad `MoodleConnection`

**El anti-patrón a evitar:** meter `moodle_token_2`, `moodle_url_2` en `User`. Se
pudre al tercer campo y no generaliza.

**El modelo correcto:** extraer una entidad nueva. `User` queda como **identidad +
preferencias + canal** (telegram); los tokens/campus se van a **1..N conexiones**.

```
User
  id, telegram_chat_id, is_active, (futuras prefs: timezone, language, canales)
  └── 1..N MoodleConnection
        id, user_id (FK)
        moodle_site       -- REFERENCIA a un sitio Moodle (institución+campus), NO un enum fijo.
                          --   arranca con aprende/educa de UNED, pero agregar una universidad
                          --   nueva debe ser DATO (fila en un catálogo de sitios), no código.
        moodle_url        -- reemplaza el settings.moodle_base_url global (seam #1). Puede
                          --   derivarse del catálogo de sitios en vez de guardarse por conexión.
        moodle_token      -- cifrado at-rest (ya existe el cipher)
        moodle_user_id    -- el userid DENTRO de ese sitio (difiere entre sitios/campus)
        is_active
        token_failure_count   -- token-recovery pasa a ser POR CONEXIÓN
        last_scan_at
        created_at, updated_at
```

> **Objetivo explícito (2026-07-05): multi-UNIVERSIDAD, no solo multi-campus.** El usuario
> quiere abarcar varias universidades, no únicamente los 2 campus de UNED. Consecuencia de
> diseño: **NO** hardcodear un enum `'aprende' | 'educa'` ni asumir la URL de UNED. Modelar
> un **catálogo de sitios Moodle** (institución, campus, `moodle_url`, quizá `moodle_user_id`
> function overrides) al que la conexión referencia. Agregar una universidad = **insertar una
> fila**, no tocar código. Esto cierra por completo el seam #1 de `saas-multitenancy.md`
> (deja de ser "start-UNED-scale-later" especulativo y pasa a ser requisito).

**Todo lo que hoy cuelga del token se mueve a la conexión:**

- **Scan:** itera **conexiones activas**, no usuarios. Un usuario con 2 campus = 2 iteraciones.
- **Token-recovery (ya hecho):** el contador de fallos, el relink y el aviso pasan a ser
  **por conexión**. El token de `aprende` puede morir mientras el de `educa` sigue vivo →
  el aviso debe decir **cuál** campus re-vincular. `RelinkGuardianUseCase` recibe
  `(connection_id | campus)` además del token.
- **Snapshots/diff:** se llavean por `connection_id` (dentro, por `source_type`).
- **Registro/web:** la web genera **una llave por campus**; el onboarding permite vincular
  uno o ambos. `WEB_RELINK_URL` puede llevar el campus como parámetro.

**Notificación:** sigue siendo **un** Telegram por usuario (el chat es del `User`, no de la
conexión). Cada ítem se **etiqueta por campus**: `[Aprende] …` / `[Educa] …`, o se agrupan
en secciones. No se manda un mensaje por campus salvo que el usuario lo prefiera.

**Migración de datos:** los 2 usuarios actuales tienen su token en `users.moodle_token`.
La migración crea `moodle_connections`, inserta una fila `campus='aprende'` por cada usuario
con su token/moodle_user_id actuales, y (fase siguiente) se puede dejar de leer la columna
vieja. No destructivo si se hace en dos pasos (crear tabla + backfill; luego dropear columna).

---

## Eje A — Fuentes rastreables: generalizar el diff

Hoy el diff está cableado a assignments/eventos. Foros/anuncios/mensajes piden un
concepto unificado de **fuente rastreable** para que agregar una nueva sea barato.

**Concepto:** un `source_type` (enum) + un rastreo genérico de "qué ítems ya vi".

| `source_type` | Función Moodle probable | Notas |
|---------------|-------------------------|-------|
| `assignment` | `mod_assign_get_assignments` | ya existe |
| `event` | `core_calendar_get_calendar_events` | ya existe (incluye `[Foro]` con fecha) |
| `announcement` | `mod_forum_get_forum_discussions` (foro Novedades/News) | **alto valor, bajo ruido** → empezar acá |
| `forum_post` | `mod_forum_get_forum_discussions` (foros de discusión/Q&A) | ruidoso → **opt-in** por usuario/foro |
| `message` | `core_message_get_conversations` / `_get_messages` | privado; alto valor; cadencia corta |

**Diff genérico:** por `(connection_id, source_type)` se guarda el "último visto"
(último `id`/`timemodified`/fecha) y se emiten como novedad los ítems posteriores. Esto
generaliza lo que hoy hace el diff de assignments a cualquier fuente nueva.

⚠️ **Cuidado (decisión previa vigente):** los **PDF-instrucción de foro** NO se notifican
como entregable (`"foro"` fuera de `_DELIVERABLE_KEYWORDS`: son ruido sin fecha). Y los
foros **con fecha** ya se avisan como evento `[Foro] … — <fecha>`. Por eso "foros/anuncios"
aquí = **posts/discusiones nuevas** (Novedades y, opt-in, discusión), NO el evento-con-fecha
ni el PDF-instrucción. No re-notificar lo que ya se notifica.

---

## Eje C — Sinks: Google Calendar y Notion

Distinción importante: foros/anuncios son **fuentes** (leo de Moodle). GCal y Notion son
**destinos** (escribo mis entregables hacia afuera). No son "canal de notificación" ni
"fuente": son **sincronización de estado**.

- **Puerto nuevo** tipo `DeliverableSyncPort.sync(user, deliverables)` (paralelo a
  `NotifierGateway`, pero "sincroniza estado" en vez de "manda aviso puntual").
- **Dependen de OAuth por usuario** (token de Google / Notion) → **otro secreto por usuario
  a cifrar y gestionar**. Reusa el cipher; encaja con preferencias (#7) y seguridad (#5).
- **Aditivos e independientes:** no bloquean nada y nada los bloquea. Consumen los
  entregables estructurados que ya existen.
- **Ubicación:** Fase 2, cuando exista el modelo de preferencias/OAuth por usuario.

💡 Tentación a resistir por ahora: unificar "conexión Moodle", "cuenta Google", "cuenta
Notion" en una sola abstracción `ExternalAccount`. Es elegante pero es YAGNI hasta tener
los tres; hoy `MoodleConnection` alcanza.

---

## Secuencia de construcción propuesta (a confirmar)

Los ejes A y B son independientes en **construcción** pero acoplados en **diseño**. La
llave `(connection_id, source_type, item_id)` los une. Orden recomendado:

1. **Diseño (este doc)** — fijar `MoodleConnection`, `source_type` y la llave de snapshot.
   Barato; evita rehacer.
2. **Foros/anuncios (eje A)** sobre el modelo genérico, empezando por **`announcement`
   (Novedades/News)** — alto valor, bajo ruido. Se construye con **una sola conexión** por
   usuario por ahora, pero los registros ya llevan `connection_id`. Entrega valor visible ya.
3. **Multi-campus (eje B)** — introducir `MoodleConnection` de verdad (tabla + backfill),
   scan por conexión, relink por conexión, etiquetas por campus. Como las fuentes ya llevan
   `connection_id`, agregar `educa` no reescribe foros.
4. **Preferencias por usuario (#7)** — habilita opt-in de foros Q&A, elección de campus,
   selección de canal. Necesario antes de los sinks.
5. **Sinks (eje C)** — Google Calendar / Notion, sobre OAuth por usuario.

**Alternativa descartada por defecto:** hacer multi-campus **antes** que foros. Es el
modelo 100% correcto desde el inicio, pero es un refactor grande y riesgoso (toca auth,
scan, snapshots, migraciones y el token-recovery recién hecho) **sin valor visible nuevo**
hasta terminarlo. Preferimos valor incremental con el modelo ya campus-ready.

---

## Decisiones abiertas

- **Orden foros vs. multi-campus** (ver secuencia; propuesta: foros primero, modelo campus-ready).
- **Alcance de foros:** ¿solo Novedades/News, o también foros de discusión (opt-in)?
- **`moodle_user_id` por campus:** confirmar que educa-U puede tener un userid distinto al de
  aprende para el mismo estudiante (afecta el onboarding y el matching).
- **Cadencia por fuente:** ¿mensajes/anuncios en intervalo corto (15–30 min) y el resto a 3h?
  (init. 2 del roadmap; sube carga de API).
- **Etiqueta vs. mensajes separados por campus** en la notificación (default: etiqueta).
