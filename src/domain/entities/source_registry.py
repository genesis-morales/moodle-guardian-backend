"""Mapa `source_type` -> clase de entidad rastreable.

Único punto donde se declara qué clase reconstruye cada fuente. La persistencia lo
usa para deserializar genéricamente (`cls.from_dict(...)`) sin un `if` por tipo, y
agregar una fuente futura (anuncios, mensajes) es añadir una línea aquí.
"""

from src.domain.entities.announcement import Announcement
from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.instruction import Instruction
from src.domain.entities.message import Message
from src.domain.entities.source_type import SourceType

SOURCE_CLASSES: dict[str, type] = {
    SourceType.ASSIGNMENT: Assignment,
    SourceType.EVENT: CalendarEvent,
    SourceType.INSTRUCTION: Instruction,
    SourceType.ANNOUNCEMENT: Announcement,
    SourceType.MESSAGE: Message,
}
