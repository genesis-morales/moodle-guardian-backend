from dataclasses import dataclass, field
from typing import List

from src.domain.entities.source_type import SourceType


@dataclass
class Change:
    """Un ítem que cambió entre dos snapshots: la versión previa, la actual y los
    campos que difieren. Es genérico (sirve para cualquier `source_type`); el
    consumidor (message builder) lee `current` y `changed_fields` sin importar el
    tipo concreto."""

    previous: object
    current: object
    changed_fields: List[str] = field(default_factory=list)


# Alias por compatibilidad: antes había una dataclass por tipo. Se conservan porque
# los tests (y algún caller) las importan/instancian; todas comparten la forma de
# `Change`, así que el message builder las trata igual (duck typing).
ChangedAssignment = Change
ChangedEvent = Change
ChangedInstruction = Change


@dataclass
class SourceChanges:
    """Los tres cubos de cambios de una fuente: nuevos, actualizados, removidos."""

    new: list = field(default_factory=list)
    updated: List[Change] = field(default_factory=list)
    removed: list = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.new or self.updated or self.removed)


class DiffResult:
    """Resultado del diff, agnóstico al tipo de fuente.

    Internamente guarda `changes: {source_type: SourceChanges}`, de modo que
    agregar una fuente nueva no exige campos nuevos (mismo espíritu que
    `Snapshot.items`). Se conservan propiedades de compatibilidad
    (`new_assignments`, `updated_events`, ...) y un constructor que acepta tanto el
    dict `changes` como los kwargs legacy por tipo, para no romper a los ~12
    consumidores/tests existentes.
    """

    # source_type -> nombre singular usado en las propiedades de compat.
    _COMPAT = {
        SourceType.ASSIGNMENT: "assignments",
        SourceType.EVENT: "events",
        SourceType.INSTRUCTION: "instructions",
        SourceType.ANNOUNCEMENT: "announcements",
        SourceType.MESSAGE: "messages",
    }

    def __init__(
        self,
        changes: dict[str, SourceChanges] | None = None,
        **legacy: list,
    ) -> None:
        self.changes: dict[str, SourceChanges] = {}
        if changes:
            self.changes = {k: v for k, v in changes.items()}

        # Pliega kwargs legacy (new_assignments=..., updated_events=[Change...], ...)
        # sobre el dict `changes`, que es la fuente de verdad.
        for source_type, name in self._COMPAT.items():
            new = legacy.pop(f"new_{name}", None)
            updated = legacy.pop(f"updated_{name}", None)
            removed = legacy.pop(f"removed_{name}", None)
            if new or updated or removed:
                bucket = self.changes.setdefault(source_type, SourceChanges())
                if new:
                    bucket.new.extend(new)
                if updated:
                    bucket.updated.extend(updated)
                if removed:
                    bucket.removed.extend(removed)

        if legacy:
            raise TypeError(f"DiffResult: kwargs no reconocidos: {sorted(legacy)}")

    def of(self, source_type: str) -> SourceChanges:
        return self.changes.get(source_type, SourceChanges())

    # --- Propiedades de compatibilidad (una tripleta por tipo) ---
    @property
    def new_assignments(self) -> list:
        return self.of(SourceType.ASSIGNMENT).new

    @property
    def updated_assignments(self) -> List[Change]:
        return self.of(SourceType.ASSIGNMENT).updated

    @property
    def removed_assignments(self) -> list:
        return self.of(SourceType.ASSIGNMENT).removed

    @property
    def new_events(self) -> list:
        return self.of(SourceType.EVENT).new

    @property
    def updated_events(self) -> List[Change]:
        return self.of(SourceType.EVENT).updated

    @property
    def removed_events(self) -> list:
        return self.of(SourceType.EVENT).removed

    @property
    def new_instructions(self) -> list:
        return self.of(SourceType.INSTRUCTION).new

    @property
    def updated_instructions(self) -> List[Change]:
        return self.of(SourceType.INSTRUCTION).updated

    @property
    def removed_instructions(self) -> list:
        return self.of(SourceType.INSTRUCTION).removed

    @property
    def new_announcements(self) -> list:
        return self.of(SourceType.ANNOUNCEMENT).new

    @property
    def updated_announcements(self) -> List[Change]:
        return self.of(SourceType.ANNOUNCEMENT).updated

    @property
    def removed_announcements(self) -> list:
        return self.of(SourceType.ANNOUNCEMENT).removed

    @property
    def new_messages(self) -> list:
        return self.of(SourceType.MESSAGE).new

    @property
    def updated_messages(self) -> List[Change]:
        return self.of(SourceType.MESSAGE).updated

    @property
    def removed_messages(self) -> list:
        return self.of(SourceType.MESSAGE).removed

    @property
    def has_changes(self) -> bool:
        return any(bucket.has_changes for bucket in self.changes.values())
