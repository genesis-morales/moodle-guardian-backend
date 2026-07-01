# 🛡️ Moodle Guardian Backend

A powerful, production-ready backend service that monitors **Moodle** learning management system courses for changes and sends real-time notifications via **Telegram**. Built with **FastAPI**, **PostgreSQL**, and designed with clean architecture principles.

> **Moodle Guardian** keeps students informed about their courses by detecting and notifying them about new, updated, or removed assignments and calendar events in real-time.

---

## ✨ Features

- 🔔 **Real-time Change Detection** — Intelligent snapshot comparison to identify new, updated, and removed assignments and calendar events
- 📱 **Telegram Integration** — Direct notifications to users via Telegram bot with rich formatting
- ⏰ **Automatic Scheduling** — Background worker runs periodic scans at configurable intervals (default: every 3 hours)
- 🔄 **Manual Sync** — Trigger immediate synchronization through REST API
- 👥 **User Management** — Register users, manage Moodle tokens securely, and link Telegram accounts
- 📧 **Weekly Digests** — Aggregated summary of all changes sent every Monday
- 🔒 **Distributed Locking** — PostgreSQL advisory locks prevent concurrent scan conflicts
- 🗄️ **Database Migrations** — Alembic integration for schema versioning and easy deployment
- 🏗️ **Clean Architecture** — Separation of concerns: Domain → Application → Infrastructure layers
- ✅ **Comprehensive Testing** — Unit, integration, and fixture-based tests with pytest

---

## 🛠 Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | FastAPI | 0.115+ |
| **Runtime** | Python | 3.9+ |
| **Database** | PostgreSQL | 12+ (with async SQLAlchemy & asyncpg) |
| **Authentication** | JWT (python-jose) | — |
| **Notifications** | Telegram Bot API | — |
| **Scheduling** | APScheduler | — |
| **Migrations** | Alembic | — |
| **Testing** | Pytest | — |
| **Server** | Uvicorn / Gunicorn | ASGI |

### Key Dependencies

```
fastapi              # Web framework
sqlalchemy[asyncio]  # Async ORM
asyncpg              # PostgreSQL driver
pydantic             # Data validation
python-jose          # JWT tokens
alembic              # Database migrations
pytest               # Testing framework
aiohttp              # Async HTTP client
apscheduler          # Task scheduling
```

See [`requirements.txt`](requirements.txt) for the complete list.

---

## 📁 Project Structure

```
moodle-guardian-backend/
├── src/
│   ├── main.py                          # FastAPI app entry point
│   │
│   ├── config/
│   │   ├── settings.py                  # Environment vars & config
│   │   └── logging.py                   # Logging setup
│   │
│   ├── domain/                          # 🎯 Pure business logic (no external deps)
│   │   ├── entities/
│   │   │   ├── user.py
│   │   │   ├── course.py
│   │   │   ├── assignment.py
│   │   │   ├── calendar_event.py
│   │   │   ├── snapshot.py
│   │   │   └── diff_result.py
│   │   │
│   │   ├── value_objects/
│   │   │   ├── telegram_chat_id.py
│   │   │   ├── moodle_token.py
│   │   │   └── course_id.py
│   │   │
│   │   ├── services/
│   │   │   ├── diff_service.py          # Snapshot comparison logic
│   │   │   ├── digest_service.py        # Weekly summary building
│   │   │   └── normalization_service.py # Stable hashing for diff
│   │   │
│   │   ├── ports/                       # 🔌 Interface contracts
│   │   │   ├── user_repository.py
│   │   │   ├── snapshot_repository.py
│   │   │   ├── subscription_repository.py
│   │   │   ├── moodle_gateway.py
│   │   │   ├── notifier_gateway.py
│   │   │   └── scheduler_lock.py
│   │   │
│   │   └── exceptions/
│   │       ├── domain_errors.py
│   │       ├── moodle_errors.py
│   │       └── registration_errors.py
│   │
│   ├── application/                     # 🧩 Use cases & orchestration
│   │   ├── dto/
│   │   │   ├── guardian_dto.py
│   │   │   ├── sync_dto.py
│   │   │   └── digest_dto.py
│   │   │
│   │   ├── use_cases/
│   │   │   ├── register_guardian.py      # Register user from extension
│   │   │   ├── link_telegram_chat.py     # Link Telegram chat ID
│   │   │   ├── sync_user_courses.py      # Download user courses
│   │   │   ├── fetch_course_snapshot.py  # Fetch current snapshot from Moodle
│   │   │   ├── detect_course_changes.py  # Run diff for a course
│   │   │   ├── notify_user_changes.py    # Send individual alerts
│   │   │   ├── build_weekly_digest.py    # Prepare weekly summary
│   │   │   ├── send_weekly_digest.py     # Send digest message
│   │   │   └── run_guardian_scan.py      # Central scan use case
│   │   │
│   │   └── services/
│   │       └── guardian_orchestrator.py  # Complex workflow coordination
│   │
│   ├── infrastructure/                  # 🔌 Concrete implementations
│   │   ├── db/
│   │   │   ├── database.py              # Engine/session setup (async)
│   │   │   ├── models.py                # SQLAlchemy ORM models
│   │   │   ├── mappings.py              # Domain ↔ ORM mappings
│   │   │   └── migrations/              # Alembic versioning
│   │   │
│   │   ├── repositories/
│   │   │   ├── postgres_user_repository.py
│   │   │   ├── postgres_snapshot_repository.py
│   │   │   └── postgres_subscription_repository.py
│   │   │
│   │   ├── external/
│   │   │   ├── moodle/
│   │   │   │   ├── http_client.py       # Base HTTP client
│   │   │   │   ├── moodle_client.py     # Moodle Web Services calls
│   │   │   │   ├── parsers.py           # Response parsing
│   │   │   │   └── endpoints.py         # Endpoint helpers
│   │   │   │
│   │   │   └── telegram/
│   │   │       ├── telegram_bot.py      # Telegram Bot API client
│   │   │       ├── message_builder.py   # Message formatting
│   │   │       └── keyboards.py         # Inline buttons
│   │   │
│   │   └── locks/
│   │       └── postgres_advisory_lock.py # Distributed locking
│   │
│   ├── api/
│   │   ├── dependencies.py              # Dependency injection
│   │   ├── exception_handlers.py        # Global error handlers
│   │   ├── schemas/
│   │   │   ├── guardian.py              # Registration schemas
│   │   │   ├── telegram.py              # Telegram linking schemas
│   │   │   ├── health.py                # Health check schemas
│   │   │   └── sync.py                  # Sync endpoint schemas
│   │   │
│   │   └── v1/
│   │       ├── guardian.py              # User registration endpoints
│   │       ├── telegram.py              # Telegram linking endpoints
│   │       ├── sync.py                  # Manual sync endpoints
│   │       ├── health.py                # Health check endpoint
│   │       └── webhooks.py              # Webhook handlers
│   │
│   ├── workers/
│   │   ├── scheduler.py                 # APScheduler configuration
│   │   ├── jobs/
│   │   │   ├── scan_all_users.py        # Periodic scan job (every 3 hours)
│   │   │   ├── send_monday_digest.py    # Monday digest job
│   │   │   └── cleanup_old_snapshots.py # Data cleanup job
│   │   │
│   │   └── runner.py                    # Worker entry point
│   │
│   ├── utils/
│   │   ├── datetime.py
│   │   ├── hashing.py                   # Stable keys for diffing
│   │   └── ids.py
│   │
│   └── tests/
│       ├── unit/                        # Unit tests (domain, app)
│       ├── integration/                 # Integration tests
│       └── fixtures/                    # Shared test fixtures
│
├── alembic/                             # Database migration configs
├── docs/                                # Documentation
├── scripts/                             # Utility scripts
├── alembic.ini                          # Alembic configuration
├── requirements.txt                     # Python dependencies
├── pytest.ini                           # Pytest configuration
├── .env.example                         # Environment template
└── README.md                            # This file
```

### Architecture Flow

```
User Registration → Sync Courses → Periodic Scan
                                        ↓
                            Fetch Moodle Snapshot
                                        ↓
                            Compare with Last Snapshot
                                        ↓
                        Detect Changes (New/Updated/Removed)
                                        ↓
                            Send Telegram Notifications
                                        ↓
                        Aggregate for Weekly Digest (Mondays)
```

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.9 or higher
- **PostgreSQL** 12 or higher (with async support)
- **Telegram** Bot token (from [@BotFather](https://t.me/botfather))
- **Moodle** instance with Web Services enabled

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/genesis-morales/moodle-guardian-backend.git
cd moodle-guardian-backend
```

#### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Application
APP_NAME=Moodle Guardian API
APP_VERSION=1.0.0
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/moodle_guardian

# Moodle Configuration
MOODLE_BASE_URL=https://aprende.uned.ac.cr/webservice/rest/server.php
MOODLE_SITE_INFO_FUNCTION=core_webservice_get_site_info
MOODLE_COURSES_FUNCTION=core_enrol_get_users_courses
MOODLE_CALENDAR_EVENTS_FUNCTION=core_calendar_get_calendar_events
MOODLE_ASSIGNMENTS_FUNCTION=mod_assign_get_assignments

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_API_BASE_URL=https://api.telegram.org
REQUEST_TIMEOUT_SECONDS=30

# Scheduler Configuration
SCHEDULER_INTERVAL_HOURS=3
SCHEDULER_RUN_IMMEDIATELY_ON_START=false
SCHEDULER_TIMEZONE=UTC
```

#### 5. Initialize Database

```bash
# Apply all migrations
alembic upgrade head

# Or create from scratch (dev only)
python -c "from src.infrastructure.db.database import create_all; create_all()"
```

#### 6. Run Development Server

```bash
# Terminal 1: API Server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Background Worker
python -m src.workers.runner
```

The API will be available at `http://localhost:8000`

---

## 📚 API Endpoints

### Guardian (User Registration)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/guardian/register` | Register a new user with Moodle token |
| `GET` | `/v1/guardian/{user_id}` | Get user profile information |
| `PUT` | `/v1/guardian/{user_id}` | Update user settings |
| `DELETE` | `/v1/guardian/{user_id}` | Deactivate user account |

### Telegram

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/telegram/link` | Link Telegram chat ID to user account |
| `POST` | `/v1/telegram/verify` | Verify Telegram connection with verification code |
| `DELETE` | `/v1/telegram/unlink/{user_id}` | Unlink Telegram account |

### Sync

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/sync/manual` | Trigger manual sync for authenticated user |
| `POST` | `/v1/sync/run/{moodle_user_id}` | Run guardian scan for specific user |

### Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | API health check |
| `GET` | `/health/ready` | Readiness probe (DB connection check) |

---

## 🔄 How It Works

### User Journey

```
1. User Registration
   └─ User provides Moodle token via browser extension
      └─ Backend validates token and creates user account

2. Course Subscription
   └─ System fetches user's enrolled courses from Moodle
      └─ Stores courses and creates subscriptions

3. Continuous Monitoring
   └─ Background worker runs scan every 3 hours
      └─ For each user:
         ├─ Fetch current courses and assignments from Moodle
         ├─ Create snapshot of current state
         ├─ Compare with previous snapshot
         ├─ Detect changes (new, updated, removed)
         └─ Send Telegram notifications for changes

4. Weekly Summary
   └─ Every Monday, aggregates all week's changes
      └─ Sends comprehensive digest via Telegram
```

### Change Detection Algorithm

The system uses a robust diffing mechanism:

1. **Normalization** — Standardize data (dates, IDs) using stable hashing
2. **Comparison** — Compare current snapshot with previous snapshot
3. **Classification** — Categorize changes:
   - ✨ **New** — Appears in current but not in previous
   - 🔄 **Updated** — Present in both with differences
   - ❌ **Removed** — Present in previous but not in current
4. **Aggregation** — Group changes by course and type
5. **Notification** — Send formatted messages to Telegram

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only unit tests
pytest src/tests/unit

# Run only integration tests
pytest src/tests/integration

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest src/tests/unit/domain/test_diff_service.py

# Run tests matching pattern
pytest -k "test_diff" -v
```

### Test Structure

```
tests/
├── unit/
│   ├── domain/          # Domain logic tests (no deps)
│   ├── application/     # Use case tests
│   └── infrastructure/  # Repository & external service tests
├── integration/         # End-to-end API tests
├── conftest.py          # Shared fixtures
└── fixtures/
    ├── factories.py     # Test data factories
    └── mock_data.py     # Mock responses
```

---

## 🏗 Architecture Principles

This project follows **Clean Architecture** and **Domain-Driven Design (DDD)** principles:

### Layer Responsibilities

| Layer | Responsibility | Dependency |
|-------|-----------------|-----------|
| **Domain** | Pure business logic, no external deps | — |
| **Application** | Use cases, orchestration, DTOs | Domain |
| **Infrastructure** | Database, APIs, external services | Application, Domain |
| **API** | HTTP handlers, validation, serialization | Application |

### Key Benefits

✅ **Testability** — Domain logic has zero external dependencies
✅ **Framework Agnostic** — Could swap FastAPI for Flask/Starlette
✅ **Clear Separation** — Each layer has single responsibility
✅ **Scalability** — Easy to add features without affecting existing code
✅ **Maintainability** — Clear dependency flow and abstractions

---

## 🔒 Security Considerations

### Authentication & Authorization

- JWT tokens issued for API access
- Moodle tokens stored encrypted in database
- Environment variables for sensitive configuration
- Validated input using Pydantic models

### Data Protection

- Async operations prevent blocking
- PostgreSQL advisory locks prevent race conditions
- Connection pooling with timeout protection
- HTTPS recommended for production (reverse proxy)

### Best Practices for Production

```bash
# 1. Use environment variables (never commit secrets)
# 2. Enable HTTPS with reverse proxy (nginx, Caddy)
# 3. Use strong database passwords
# 4. Enable PostgreSQL audit logging
# 5. Rate limit API endpoints
# 6. Monitor logs and set up alerts
# 7. Regular security updates for dependencies
# 8. Backup database regularly
```

---

## 📊 Database Schema

### Key Entities

```
Users (1) ─────→ (N) Subscriptions ─────→ (N) Courses
  │
  └───→ (N) Snapshots
         │
         └───→ (N) Assignments
         │
         └───→ (N) Calendar Events
```

### Main Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts with Moodle token & Telegram chat ID |
| `courses` | Course information from Moodle |
| `subscriptions` | User-to-Course enrollment |
| `snapshots` | Point-in-time captures of assignments & events |
| `assignments` | Assignment/activity metadata |
| `calendar_events` | Course calendar events |
| `changes_log` | History of detected changes (for digest) |

---

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Issues

```
Error: could not connect to database
```

**Solution:**
- Verify PostgreSQL is running: `psql -U postgres`
- Check `DATABASE_URL` in `.env`
- Ensure database exists: `createdb moodle_guardian`
- Apply migrations: `alembic upgrade head`

#### Moodle Integration Issues

```
Error: Invalid Moodle token
```

**Solution:**
- Verify `MOODLE_BASE_URL` is correct
- Check Moodle user token is valid
- Ensure Moodle Web Services are enabled: Admin → Server → Web Services
- Check network connectivity to Moodle instance

#### Telegram Notifications Not Working

```
Error: Telegram chat ID not valid
```

**Solution:**
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Ensure user started conversation with bot
- Check network connectivity to Telegram API
- Verify chat ID is numeric and valid

#### Worker Not Running

```
Error: No module named 'src.workers.runner'
```

**Solution:**
- Ensure virtual environment is activated
- Check current directory is repository root
- Run: `python -m src.workers.runner`

---

## 📈 Performance & Scalability

### Optimization Tips

1. **Database** — Add indexes on frequently queried columns
   ```sql
   CREATE INDEX idx_snapshots_user_id ON snapshots(user_id);
   CREATE INDEX idx_changes_log_user_id ON changes_log(user_id);
   ```

2. **Connection Pooling** — Adjust in `settings.py`:
   ```python
   DB_POOL_SIZE=20
   DB_MAX_OVERFLOW=10
   DB_POOL_TIMEOUT=30
   ```

3. **Caching** — Implement Redis cache for frequently accessed data

4. **Async Operations** — Leverage FastAPI's async capabilities

5. **Monitoring** — Set up APM (e.g., New Relic, DataDog)

---

## 📝 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL async connection string |
| `MOODLE_BASE_URL` | ✅ | — | Moodle Web Services base URL |
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Telegram bot token |
| `APP_NAME` | ❌ | Moodle Guardian API | Application name |
| `APP_VERSION` | ❌ | 1.0.0 | Application version |
| `DEBUG` | ❌ | false | Debug mode (dev only) |
| `SCHEDULER_INTERVAL_HOURS` | ❌ | 3 | Scan interval in hours |
| `SCHEDULER_RUN_IMMEDIATELY_ON_START` | ❌ | false | Run scan on startup |
| `REQUEST_TIMEOUT_SECONDS` | ❌ | 30 | HTTP request timeout |
| `LOG_LEVEL` | ❌ | INFO | Logging level |

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests before committing
pytest -v

# Format code
black src/

# Check types
mypy src/

# Lint
flake8 src/
```

---

## 📄 License

This project is open source and available under the **MIT License**.

See the [LICENSE](LICENSE) file for details.

---

## 📞 Support & Contact

- **Issues** — Report bugs or request features via [GitHub Issues](https://github.com/genesis-morales/moodle-guardian-backend/issues)
- **Discussions** — Ask questions in [GitHub Discussions](https://github.com/genesis-morales/moodle-guardian-backend/discussions)
- **Email** — Contact maintainers at [support@example.com](mailto:support@example.com)

---

## 🙏 Acknowledgments

Built with ❤️ to keep Moodle students informed about their courses.

- Inspired by the need for better course notifications in Moodle
- Thanks to the FastAPI and SQLAlchemy communities
- Special thanks to all contributors

---

**Last Updated:** July 2026 | **Version:** 1.0.0
