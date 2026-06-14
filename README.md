# Moodle Guardian Backend

A powerful backend service that monitors Moodle learning management system courses for changes and sends real-time notifications via Telegram. Built with FastAPI, PostgreSQL, and designed with clean architecture principles.

## 🎯 Overview

**Moodle Guardian** is a monitoring solution for Moodle users that:
- Captures periodic snapshots of course data (assignments, calendar events)
- Detects changes and differences between snapshots
- Sends real-time Telegram notifications about new/updated/removed assignments and events
- Provides a weekly digest of all changes
- Implements a scheduler to run automated scans at configured intervals

## ✨ Features

- **Real-time Change Detection**: Compares course data snapshots to identify new, updated, and removed assignments and calendar events
- **Telegram Integration**: Send notifications directly to users via Telegram bot
- **Automatic Scheduling**: Background worker that runs periodic scans (configurable interval)
- **Manual Sync**: Trigger manual syncs through REST API
- **User Management**: Register users, manage Moodle tokens, and link Telegram accounts
- **Weekly Digests**: Aggregated summary of all changes sent on Mondays
- **Distributed Locking**: Prevents concurrent scans using PostgreSQL advisory locks
- **Database Migrations**: Alembic integration for schema versioning
- **Clean Architecture**: Separation of concerns with domain, application, and infrastructure layers

## 🛠 Tech Stack

- **Framework**: FastAPI 0.115+ (async Python web framework)
- **Database**: PostgreSQL with async SQLAlchemy and asyncpg
- **Authentication**: JWT tokens (python-jose)
- **Notifications**: Telegram Bot API
- **Scheduling**: APScheduler (background jobs)
- **Migration Tool**: Alembic
- **Testing**: Pytest
- **Server**: Uvicorn (ASGI) / Gunicorn

### Dependencies

See [`requirements.txt`](requirements.txt) for all dependencies. Key packages:
- `fastapi` - Web framework
- `sqlalchemy[asyncio]` - ORM
- `asyncpg` - PostgreSQL async driver
- `pydantic` - Data validation
- `python-jose` - JWT handling
- `alembic` - Database migrations
- `pytest` - Testing framework

## 📁 Project Structure

```
src/
├── main.py                           # FastAPI app, lifespan, middlewares, routers
│
├── config/
│   ├── settings.py                   # Environment variables, URLs, tokens, flags
│   └── logging.py                    # Logging configuration
│
├── domain/                           # Pure business logic (no external deps)
│   ├── entities/
│   │   ├── user.py                   # User/Guardian user entity
│   │   ├── course.py                 # Course entity
│   │   ├── assignment.py             # Assignment/activity entity
│   │   ├── calendar_event.py         # Calendar event entity
│   │   ├── snapshot.py               # Captured Moodle state
│   │   └── diff_result.py            # Diff computation result
│   │
│   ├── value_objects/
│   │   ├── telegram_chat_id.py
│   │   ├── moodle_token.py
│   │   └── course_id.py
│   │
│   ├── services/
│   │   ├── diff_service.py           # Snapshot comparison logic
│   │   ├── digest_service.py         # Weekly summary building
│   │   └── normalization_service.py  # Stable hashing for diff
│   │
│   ├── ports/                        # Interface contracts
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
├── application/                      # Use cases & orchestration
│   ├── dto/
│   │   ├── guardian_dto.py
│   │   ├── sync_dto.py
│   │   └── digest_dto.py
│   │
│   ├── use_cases/
│   │   ├── register_guardian.py        # Register user from extension
│   │   ├── link_telegram_chat.py       # Link Telegram chat ID
│   │   ├── sync_user_courses.py        # Download user courses
│   │   ├── fetch_course_snapshot.py    # Fetch current snapshot from Moodle
│   │   ├── detect_course_changes.py    # Run diff for a course
│   │   ├── notify_user_changes.py      # Send individual alerts
│   │   ├── build_weekly_digest.py      # Prepare weekly summary
│   │   ├── send_weekly_digest.py       # Send digest message
│   │   └── run_guardian_scan.py        # Central scan use case
│   │
│   └── services/
│       └── guardian_orchestrator.py    # Complex workflow coordination
│
├── infrastructure/                   # Concrete implementations
│   ├── db/
│   │   ├── database.py               # Engine/session setup (async)
│   │   ├── models.py                 # ORM models
│   │   ├── mappings.py               # ORM ↔ domain mappings
│   │   └── migrations/               # Alembic migrations
│   │
│   ├── repositories/
│   │   ├── postgres_user_repository.py
│   │   ├── postgres_snapshot_repository.py
│   │   └── postgres_subscription_repository.py
│   │
│   ├── external/
│   │   ├── moodle/
│   │   │   ├── http_client.py        # Base HTTP client
│   │   │   ├── moodle_client.py      # Moodle Web Services calls
│   │   │   ├── parsers.py            # Response parsing
│   │   │   └── endpoints.py          # Endpoint helpers
│   │   │
│   │   └── telegram/
│   │       ├── telegram_bot.py       # Telegram API client
│   │       ├── message_builder.py    # Message formatting
│   │       └── keyboards.py          # Inline buttons
│   │
│   └── locks/
│       └── postgres_advisory_lock.py # Distributed locking
│
├── api/
│   ├── dependencies.py               # Dependency injection
│   ├── exception_handlers.py        # HTTP error handlers
│   ├── schemas/
│   │   ├── guardian.py              # Registration schemas
│   │   ├── telegram.py              # Telegram linking schemas
│   │   ├── health.py                # Health check schemas
│   │   └── sync.py                  # Sync endpoint schemas
│   │
│   └── v1/
│       ├── guardian.py              # User registration endpoints
│       ├── telegram.py              # Telegram linking endpoints
│       ├── sync.py                  # Manual sync endpoints
│       ├── health.py                # Health check endpoint
│       └── webhooks.py              # Webhook handlers
│
├── workers/
│   ├── scheduler.py                 # APScheduler setup
│   ├── jobs/
│   │   ├── scan_all_users.py        # Periodic scan job (every 3 hours)
│   │   ├── send_monday_digest.py    # Monday digest job
│   │   └── cleanup_old_snapshots.py # Cleanup job
│   │
│   └── runner.py                    # Worker entry point
│
├── utils/
│   ├── datetime.py
│   ├── hashing.py                   # Stable keys for diff
│   └── ids.py
│
└── tests/
    ├── unit/
    │   ├── domain/
    │   ├── application/
    │   └── infrastructure/
    ├── integration/
    └── fixtures/
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Telegram Bot API token

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/genesis-morales/moodle-guardian-backend.git
   cd moodle-guardian-backend
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # Application
   APP_NAME=Moodle Guardian API
   APP_VERSION=1.0.0
   
   # Database
   DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/moodle_guardian
   
   # Moodle Configuration
   MOODLE_BASE_URL=https://aprende.uned.ac.cr/webservice/rest/server.php
   MOODLE_SITE_INFO_FUNCTION=core_webservice_get_site_info
   MOODLE_COURSES_FUNCTION=core_enrol_get_users_courses
   MOODLE_CALENDAR_EVENTS_FUNCTION=core_calendar_get_calendar_events
   MOODLE_ASSIGNMENTS_FUNCTION=mod_assign_get_assignments
   
   # Telegram
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_API_BASE_URL=https://api.telegram.org
   REQUEST_TIMEOUT_SECONDS=30
   
   # Scheduler
   SCHEDULER_INTERVAL_HOURS=3
   SCHEDULER_RUN_IMMEDIATELY_ON_START=false
   ```

5. **Initialize the database**
   ```bash
   alembic upgrade head
   ```

6. **Run the development server**
   ```bash
   uvicorn src.main:app --reload
   ```

   The API will be available at `http://localhost:8000`

### Running the Worker

In a separate terminal:
```bash
python -m src.workers.runner
```

## 📚 API Endpoints

### Guardian (User Registration)
- `POST /v1/guardian/register` - Register a new user
- `GET /v1/guardian/{user_id}` - Get user info
- `DELETE /v1/guardian/{user_id}` - Deactivate user

### Telegram
- `POST /v1/telegram/link` - Link Telegram chat ID to user
- `POST /v1/telegram/verify` - Verify Telegram connection

### Sync
- `POST /v1/sync/manual` - Trigger manual sync for a user
- `POST /v1/sync/run/{moodle_user_id}` - Run guardian scan

### Health
- `GET /health` - Health check endpoint

## 🔄 How It Works

1. **User Registration**: Users register through a browser extension, providing their Moodle token
2. **Course Subscription**: The system fetches and stores the user's courses
3. **Periodic Scanning**: Background worker scans all active users every 3 hours
4. **Snapshot Capture**: For each user, creates a snapshot of current assignments and events
5. **Change Detection**: Compares new snapshot with previous one using `DiffService`
6. **Notifications**: Sends Telegram messages for any changes detected
7. **Weekly Digest**: Sends a summary every Monday of all changes during the week

## 🧪 Testing

Run tests with pytest:
```bash
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest src/tests/unit    # Run only unit tests
pytest src/tests/integration  # Run only integration tests
pytest --cov=src         # With coverage report
```

## 🏗 Architecture Principles

This project follows **Clean Architecture** principles:

- **Domain Layer**: Pure business logic, no external dependencies
- **Application Layer**: Use cases that orchestrate domain logic
- **Infrastructure Layer**: External integrations (databases, APIs, external services)
- **API Layer**: HTTP endpoints and request/response handling

Benefits:
- ✅ Easy to test (domain logic has no dependencies)
- ✅ Framework agnostic (could swap FastAPI for another)
- ✅ Clear separation of concerns
- ✅ Scalable and maintainable

## 🔒 Security Considerations

- Moodle tokens are stored securely and encrypted
- JWT tokens are used for API authentication
- PostgreSQL advisory locks prevent race conditions
- Input validation using Pydantic models
- Environment variables for sensitive configuration

## 📊 Database Schema

The system uses the following main entities:

- **Users**: Stores user info, Moodle token, Telegram chat ID
- **Courses**: Course data (ID, name, etc.)
- **Subscriptions**: User-to-Course relationships
- **Snapshots**: Point-in-time captures of user's assignments and events
- **Assignments**: Assignment/activity data
- **Calendar Events**: Event data

## 🐛 Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Ensure the database exists and migrations are applied

### Moodle Integration Issues
- Verify `MOODLE_BASE_URL` is correct
- Check that the Moodle user token is valid
- Ensure the Moodle Web Services are enabled

### Telegram Notifications Not Working
- Verify `TELEGRAM_BOT_TOKEN` is valid
- Ensure the user has started a conversation with the bot
- Check network connectivity to Telegram API

## 📝 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | - | PostgreSQL connection string |
| `MOODLE_BASE_URL` | ✅ | - | Moodle instance web services URL |
| `TELEGRAM_BOT_TOKEN` | ✅ | - | Telegram bot token |
| `SCHEDULER_INTERVAL_HOURS` | ❌ | 3 | Scan interval in hours |
| `SCHEDULER_RUN_IMMEDIATELY_ON_START` | ❌ | false | Run scan on worker startup |
| `REQUEST_TIMEOUT_SECONDS` | ❌ | 30 | HTTP request timeout |

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the MIT License.

## 📞 Support

For issues, questions, or suggestions, please open a GitHub issue or contact the maintainers.

---

Built with ❤️ to keep Moodle students informed about their courses.
