from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ScanFailure:
    """Un usuario que falló durante una corrida del scan y por qué."""

    moodle_user_id: int
    error: str


@dataclass
class ScanRun:
    """Resumen persistido de una corrida de un job (observabilidad).

    Convierte los logs efímeros del runner en historial consultable: cuándo
    corrió, cuánto tardó, cuántos usuarios, y quién falló con qué error.
    """

    job_name: str
    started_at: datetime
    finished_at: datetime
    total_users: int
    success_count: int
    failure_count: int
    failures: List[ScanFailure] = field(default_factory=list)
    id: Optional[int] = None

    @property
    def duration_ms(self) -> int:
        return int((self.finished_at - self.started_at).total_seconds() * 1000)

    @property
    def status(self) -> str:
        """ok = sin fallos; partial = algunos; failed = todos fallaron."""
        if self.failure_count == 0:
            return "ok"
        if self.success_count == 0:
            return "failed"
        return "partial"
