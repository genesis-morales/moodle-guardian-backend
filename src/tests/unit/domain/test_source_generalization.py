"""Prueba que feat 1a cumplió su objetivo: agregar una fuente rastreable nueva
NO exige tocar el motor de diff ni reimplementar maquinaria.

- El motor `_diff_source` es agnóstico al tipo: opera sobre cualquier objeto que
  cumpla el contrato `TrackableItem` (stable_key + changed_fields).
- `Snapshot.items` almacena fuentes arbitrarias por `source_type`.
- `to_dict`/`from_dict` de las entidades reales hacen round-trip idéntico
  (la serialización que antes vivía suelta en el repo).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.instruction import Instruction
from src.domain.entities.snapshot import Snapshot
from src.domain.services.diff_service import DiffService

NOW = datetime(2026, 6, 17, 12, 0, tzinfo=UTC)


# --- una fuente FICTICIA que solo cumple el contrato TrackableItem ---

@dataclass
class FakeItem:
    source_type = "fake"
    fake_id: int
    label: str
    version: int = 0

    def stable_key(self) -> str:
        return f"fake:{self.fake_id}"

    def changed_fields(self, other: "FakeItem") -> list[str]:
        return ["version"] if self.version != other.version else []

    def to_dict(self) -> dict:
        return {"fake_id": self.fake_id, "label": self.label, "version": self.version}


@dataclass
class FakeChanged:
    previous: FakeItem
    current: FakeItem
    changed_fields: list = field(default_factory=list)


def test_generic_engine_handles_a_brand_new_source_type():
    previous = [FakeItem(1, "a", version=0), FakeItem(2, "b", version=0)]
    current = [FakeItem(1, "a", version=1), FakeItem(3, "c", version=0)]  # 1 cambió, 3 nuevo, 2 removido

    new, updated, removed = DiffService()._diff_source(
        previous, current, changed_cls=FakeChanged
    )

    assert [i.fake_id for i in new] == [3]
    assert [c.current.fake_id for c in updated] == [1]
    assert updated[0].changed_fields == ["version"]
    assert [i.fake_id for i in removed] == [2]


def test_snapshot_stores_arbitrary_source_types():
    snap = Snapshot(
        user_id=1,
        moodle_user_id=1,
        captured_at=NOW,
        items={"fake": [FakeItem(1, "a")]},
    )
    assert [i.fake_id for i in snap.items_of("fake")] == [1]
    assert not snap.is_empty()
    # y no colisiona con las propiedades compat
    assert snap.assignments == []


# --- round-trip de serialización de las entidades reales ---

def test_assignment_dict_round_trip():
    a = Assignment(
        moodle_assignment_id=10,
        moodle_course_id=100,
        name="Tarea 1",
        due_date=NOW,
        cutoff_date=NOW,
        course_name="Mate",
    )
    assert Assignment.from_dict(a.to_dict()) == a


def test_event_dict_round_trip():
    e = CalendarEvent(
        moodle_event_id=20,
        course_id=200,
        name="Foro 1",
        event_type="due",
        due_date=NOW,
        module="forum",
        course_name="Física",
    )
    assert CalendarEvent.from_dict(e.to_dict()) == e


def test_instruction_dict_round_trip():
    i = Instruction(
        moodle_id=30,
        course_id=300,
        name="Instrucciones Tarea 1",
        content_fingerprint="12345",
        kind="folder",
        course_name="Química",
    )
    assert Instruction.from_dict(i.to_dict()) == i
