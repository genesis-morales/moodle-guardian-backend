"""Model registry.

Importing this package registers every ORM model on ``Base.metadata`` so that
``create_all`` sees the full schema without relying on transitive imports
(e.g. via the API dependency wiring).
"""

from src.infrastructure.db.models.snapshot_model import SnapshotModel
from src.infrastructure.db.models.user_model import UserModel

__all__ = ["SnapshotModel", "UserModel"]
