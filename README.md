```
src/
├── core/                  # Capa Central: Reglas de negocio puras
│   ├── models.py          # Modelos de dominio (Usuario, Curso, Tarea)
│   └── services.py        # Lógica del Diffing (Comparar histórico vs actual)
│
├── adapters/              # Capa Externa: Conexiones con el mundo exterior
│   ├── database.py        # Configuración de SQLAlchemy / Tortoise ORM
│   ├── repository.py      # Operaciones CRUD puras en PostgreSQL
│   ├── moodle_client.py   # El cliente HTTP (httpx) que habla con la UNED
│   └── telegram_bot.py    # El cliente que dispara los mensajes al Bot
│
├── api/                   # Capa de Entrada: Rutas y Endpoints
│   ├── v1/
│   │   ├── guardian.py    # Endpoint donde la extensión registra al usuario
│   │   └── webhooks.py    # Opcional: Si el bot de Telegram usa webhooks
│   └── schemas.py         # Validaciones de datos de entrada con Pydantic
│
├── cron/                  # Tareas de fondo (Background Tasks / Cron)
│   └── scheduler.py       # El script que corre cada 3 horas para el barrido
│
└── main.py                # Punto de entrada de la aplicación FastAPI
```
