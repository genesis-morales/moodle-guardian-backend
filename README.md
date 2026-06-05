```
OK, comencemos. mira que pensé en algo mas robusto: 

src/
├── main.py                         # Crea la app FastAPI, lifespan, middlewares, routers
│
├── config/
│   ├── settings.py                 # Variables de entorno, URLs, tokens, flags
│   └── logging.py                  # Configuración de logs
│
├── domain/                         # Negocio puro, sin FastAPI/SQLAlchemy/httpx
│   ├── entities/
│   │   ├── user.py                 # Usuario/GUardianUser
│   │   ├── course.py               # Curso
│   │   ├── assignment.py           # Tarea / actividad evaluable
│   │   ├── calendar_event.py       # Evento de calendario
│   │   ├── snapshot.py             # Estado capturado de Moodle
│   │   └── diff_result.py          # Resultado del diff
│   │
│   ├── value_objects/
│   │   ├── telegram_chat_id.py
│   │   ├── moodle_token.py
│   │   └── course_id.py
│   │
│   ├── services/
│   │   ├── diff_service.py         # Comparación de snapshot anterior vs actual
│   │   ├── digest_service.py       # Arma el resumen semanal/lunes
│   │   └── normalization_service.py# Normaliza nombres, fechas, claves estables
│   │
│   ├── ports/                      # Interfaces/contratos
│   │   ├── user_repository.py
│   │   ├── snapshot_repository.py
│   │   ├── subscription_repository.py
│   │   ├── moodle_gateway.py
│   │   ├── notifier_gateway.py
│   │   └── scheduler_lock.py
│   │
│   └── exceptions/
│       ├── domain_errors.py
│       ├── moodle_errors.py
│       └── registration_errors.py
│
├── application/                    # Casos de uso/orquestación
│   ├── dto/
│   │   ├── guardian_dto.py
│   │   ├── sync_dto.py
│   │   └── digest_dto.py
│   │
│   ├── use_cases/
│   │   ├── register_guardian.py        # Registrar usuario desde extensión
│   │   ├── link_telegram_chat.py       # Vincular chat ID
│   │   ├── sync_user_courses.py        # Descargar cursos del usuario
│   │   ├── fetch_course_snapshot.py    # Traer snapshot actual desde Moodle
│   │   ├── detect_course_changes.py    # Ejecuta diff para un curso
│   │   ├── notify_user_changes.py      # Envía alertas individuales
│   │   ├── build_weekly_digest.py      # Prepara resumen semanal
│   │   ├── send_weekly_digest.py       # Dispara mensaje resumen
│   │   └── run_guardian_scan.py        # Caso de uso central del barrido
│   │
│   └── services/
│       └── guardian_orchestrator.py    # Coordina casos complejos si hace falta
│
├── infrastructure/                 # Implementaciones concretas
│   ├── db/
│   │   ├── database.py             # Engine/session async
│   │   ├── models.py               # Modelos ORM
│   │   ├── mappings.py             # Mapeos ORM ↔ dominio (opcional)
│   │   └── migrations/             # Si no usas alembic aparte
│   │
│   ├── repositories/
│   │   ├── postgres_user_repository.py
│   │   ├── postgres_snapshot_repository.py
│   │   └── postgres_subscription_repository.py
│   │
│   ├── external/
│   │   ├── moodle/
│   │   │   ├── http_client.py          # Cliente base httpx
│   │   │   ├── moodle_client.py        # Llamadas a Web Services UNED
│   │   │   ├── parsers.py              # Convierte respuestas Moodle → dominio
│   │   │   └── endpoints.py            # Nombres wsfunction / helpers
│   │   │
│   │   └── telegram/
│   │       ├── telegram_bot.py         # Cliente Telegram
│   │       ├── message_builder.py      # Formato de mensajes
│   │       └── keyboards.py            # Botones inline si luego los usas
│   │
│   └── locks/
│       └── postgres_advisory_lock.py   # Evita doble scheduler/escaneo
│
├── api/
│   ├── dependencies.py             # DI de repos, gateways, settings
│   ├── exception_handlers.py       # Traduce errores a HTTP responses
│   ├── schemas/
│   │   ├── guardian.py             # Request/response de registro
│   │   ├── telegram.py             # Vinculación Telegram
│   │   ├── health.py
│   │   └── sync.py
│   │
│   └── v1/
│       ├── guardian.py             # Alta de usuario/extensión
│       ├── telegram.py             # Vincular/verificar chat
│       ├── sync.py                 # Disparar sync manual
│       ├── health.py               # Healthcheck
│       └── webhooks.py             # Si luego Telegram usa webhook
│
├── workers/
│   ├── scheduler.py                # APScheduler separado del API web
│   ├── jobs/
│   │   ├── scan_all_users.py       # Barrido cada 3 horas
│   │   ├── send_monday_digest.py   # Resumen del lunes
│   │   └── cleanup_old_snapshots.py
│   │
│   └── runner.py                   # Entry point del worker
│
├── utils/
│   ├── datetime.py
│   ├── hashing.py                  # Claves estables para diff
│   └── ids.py
│
└── tests/
    ├── unit/
    │   ├── domain/
    │   │   ├── test_diff_service.py
    │   │   └── test_digest_service.py
    │   ├── application/
    │   │   ├── test_register_guardian.py
    │   │   └── test_run_guardian_scan.py
    │   └── infrastructure/
    │       └── test_moodle_client.py
    │
    ├── integration/
    │   ├── test_guardian_api.py
    │   ├── test_sync_flow.py
    │   └── test_telegram_notifications.py
    │
    └── fixtures/
        └── moodle_payloads.py
```
