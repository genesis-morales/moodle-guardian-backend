"""Model registry.

Importing this package registers every ORM model on ``Base.metadata`` so that
Alembic autogenerate (``env.py`` uses ``Base.metadata`` as target_metadata) sees
the full schema without relying on transitive imports.
"""

from src.infrastructure.db.models.moodle_connection_model import MoodleConnectionModel
from src.infrastructure.db.models.scan_run_model import ScanRunModel
from src.infrastructure.db.models.sent_reminder_model import SentReminderModel
from src.infrastructure.db.models.snapshot_model import SnapshotModel
from src.infrastructure.db.models.user_model import UserModel

__all__ = [
    "MoodleConnectionModel",
    "ScanRunModel",
    "SentReminderModel",
    "SnapshotModel",
    "UserModel",
]
