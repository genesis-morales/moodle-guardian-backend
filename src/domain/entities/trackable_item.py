from typing import Protocol, runtime_checkable


@runtime_checkable
class TrackableItem(Protocol):
    """Contrato común de todo ítem que el diff sabe rastrear entre scans.

    Es un Protocol *estructural* (no herencia) a propósito: las entidades tienen
    nombres de campo inconsistentes (`moodle_course_id` vs `course_id`, etc.) y no
    queremos renombrarlas ni acoplarlas a una base. Solo exigimos el mínimo que el
    motor genérico (`DiffService._diff_source`) y la persistencia necesitan:

    - `source_type`: a qué fuente pertenece (ver `SourceType`).
    - `stable_key()`: identidad estable del ítem entre capturas.
    - `changed_fields(other)`: qué campos cambiaron respecto a una versión previa
      (lista vacía = sin cambios relevantes).
    - `to_dict()`: forma serializable a JSONB (cada entidad trae su `from_dict`).

    Nota: el contrato NO incluye `course`. Los mensajes privados (fuente futura)
    son conversaciones sin curso; el agrupamiento por curso vive en el message
    builder, no en el ítem.
    """

    source_type: str

    def stable_key(self) -> str: ...

    def changed_fields(self, other: "TrackableItem") -> list[str]: ...

    def to_dict(self) -> dict: ...
