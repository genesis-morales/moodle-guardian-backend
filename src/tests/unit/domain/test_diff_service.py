from datetime import UTC, datetime, timedelta

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.instruction import Instruction
from src.domain.entities.snapshot import DeliverableRef, Snapshot
from src.domain.services.diff_service import DiffService

NOW = datetime(2026, 6, 17, 12, 0, tzinfo=UTC)


def event(event_id: int, name: str, due_date: datetime | None) -> CalendarEvent:
    return CalendarEvent(
        moodle_event_id=event_id,
        course_id=9621,
        name=name,
        event_type="due",
        due_date=due_date,
        module="forum",
    )


def snapshot(events: list[CalendarEvent]) -> Snapshot:
    return Snapshot(
        user_id=1,
        moodle_user_id=1,
        captured_at=NOW,
        assignments=[],
        events=events,
    )


def test_removed_event_already_expired_is_silenced():
    expired = event(1, "Foro vencido", NOW - timedelta(days=1))
    previous = snapshot([expired])
    current = snapshot([])

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.removed_events == []


def test_removed_event_still_future_is_reported():
    # Desapareció pero su fecha sigue en el futuro -> lo borró el profe: avisar.
    future = event(2, "Entrega futura borrada", NOW + timedelta(days=10))
    previous = snapshot([future])
    current = snapshot([])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [e.name for e in diff.removed_events] == ["Entrega futura borrada"]


def test_removed_event_without_date_is_reported():
    no_date = event(3, "Evento sin fecha", None)
    previous = snapshot([no_date])
    current = snapshot([])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [e.name for e in diff.removed_events] == ["Evento sin fecha"]


def test_new_event_is_detected():
    nuevo = event(4, "Foro nuevo", NOW + timedelta(days=5))
    previous = snapshot([])
    current = snapshot([nuevo])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [e.name for e in diff.new_events] == ["Foro nuevo"]


# --- INSTRUCTIONS (PDFs) ---

def instruction(moodle_id: int, name: str, fingerprint: str) -> Instruction:
    return Instruction(
        moodle_id=moodle_id,
        course_id=9460,
        name=name,
        url=f"https://moodle/{moodle_id}",
        content_fingerprint=fingerprint,
        kind="resource",
    )


def snapshot_with_instructions(
    instructions: list[Instruction],
    assignments: list[Assignment] | None = None,
    events: list[CalendarEvent] | None = None,
    deliverable_refs: list[DeliverableRef] | None = None,
) -> Snapshot:
    assignments = assignments or []
    events = events or []
    # Por defecto los refs se derivan de los entregables presentes (tareas +
    # foros), igual que hace `fetch_course_snapshot`. Para probar el caso de un
    # entregable VENCIDO (que no aparece en assignments/events pero sí debe
    # absorber su instrucción) se pasan `deliverable_refs` explícitos.
    if deliverable_refs is None:
        deliverable_refs = (
            [DeliverableRef(a.moodle_course_id, a.name) for a in assignments]
            + [DeliverableRef(e.course_id, e.name) for e in events if e.module == "forum"]
        )
    return Snapshot(
        user_id=1,
        moodle_user_id=1,
        captured_at=NOW,
        assignments=assignments,
        events=events,
        instructions=instructions,
        deliverable_refs=deliverable_refs,
    )


def assignment(name: str, course_id: int = 9460) -> Assignment:
    return Assignment(
        moodle_assignment_id=hash(name) & 0xFFFFFF,
        moodle_course_id=course_id,
        name=name,
    )


def forum(name: str, course_id: int = 9460) -> CalendarEvent:
    return CalendarEvent(
        moodle_event_id=hash(name) & 0xFFFFFF,
        course_id=course_id,
        name=name,
        event_type="due",
        due_date=NOW + timedelta(days=5),
        module="forum",
    )


def test_new_instruction_is_detected():
    nuevo = instruction(618295, "Guía nueva", "1773181058")
    previous = snapshot_with_instructions([])
    current = snapshot_with_instructions([nuevo])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [i.name for i in diff.new_instructions] == ["Guía nueva"]
    assert diff.has_changes is True


def test_removed_instruction_is_detected():
    viejo = instruction(618295, "Guía vieja", "1773181058")
    previous = snapshot_with_instructions([viejo])
    current = snapshot_with_instructions([])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [i.name for i in diff.removed_instructions] == ["Guía vieja"]


def test_changed_instruction_content_is_detected():
    # Mismo recurso (moodle_id + name), pero el timemodified cambió -> contenido
    # actualizado.
    antes = instruction(618295, "Guía", "1773181058")
    despues = instruction(618295, "Guía", "1780494018")
    previous = snapshot_with_instructions([antes])
    current = snapshot_with_instructions([despues])

    diff = DiffService().compare(previous, current, now=NOW)

    assert len(diff.updated_instructions) == 1
    change = diff.updated_instructions[0]
    assert change.changed_fields == ["content"]
    assert change.current.content_fingerprint == "1780494018"
    assert diff.new_instructions == []
    assert diff.removed_instructions == []


def test_unchanged_instruction_produces_no_diff():
    same = instruction(618295, "Guía", "1773181058")
    previous = snapshot_with_instructions([same])
    current = snapshot_with_instructions([instruction(618295, "Guía", "1773181058")])

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.has_changes is False


# --- INSTRUCTIONS absorbidas por su espacio de entrega (Assignment) ---

def test_new_instruction_with_matching_assignment_is_suppressed():
    # Aparecen a la vez el PDF y su espacio de entrega: solo notifica la tarea.
    pdf = instruction(618295, "Instrucciones Tarea 1", "1773181058")
    previous = snapshot_with_instructions([])
    current = snapshot_with_instructions([pdf], assignments=[assignment("Tarea 1")])

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.new_instructions == []
    assert [a.name for a in diff.new_assignments] == ["Tarea 1"]


def test_instruction_then_assignment_does_not_report_removal():
    # El PDF ya se había notificado; ahora aparece el espacio de entrega. El PDF
    # sigue presente pero queda absorbido: ni nuevo, ni actualizado, ni removido.
    pdf = instruction(618295, "Tarea No.1", "1773181058")
    previous = snapshot_with_instructions([pdf])
    current = snapshot_with_instructions([pdf], assignments=[assignment("Tarea 1")])

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.new_instructions == []
    assert diff.updated_instructions == []
    assert diff.removed_instructions == []


def test_absorbed_pdf_removal_is_silenced():
    # El espacio de entrega reemplazó al PDF y el profe quitó el PDF: no es noticia.
    pdf = instruction(618295, "Tarea No.1", "1773181058")
    previous = snapshot_with_instructions([pdf], assignments=[assignment("Tarea 1")])
    current = snapshot_with_instructions([], assignments=[assignment("Tarea 1")])

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.removed_instructions == []


def test_changed_content_of_absorbed_pdf_is_suppressed():
    antes = instruction(618295, "Tarea No.1", "1773181058")
    despues = instruction(618295, "Tarea No.1", "1780494018")
    previous = snapshot_with_instructions([antes])
    current = snapshot_with_instructions([despues], assignments=[assignment("Tarea 1")])

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.updated_instructions == []


def test_instruction_without_matching_assignment_still_reported():
    # Otra tarea distinta no debe absorber este PDF.
    pdf = instruction(618295, "Instrucciones Tarea 1", "1773181058")
    previous = snapshot_with_instructions([])
    current = snapshot_with_instructions([pdf], assignments=[assignment("Tarea 2")])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [i.name for i in diff.new_instructions] == ["Instrucciones Tarea 1"]


def test_assignment_in_other_course_does_not_supersede():
    pdf = instruction(618295, "Instrucciones Tarea 1", "1773181058")
    previous = snapshot_with_instructions([])
    current = snapshot_with_instructions(
        [pdf], assignments=[assignment("Tarea 1", course_id=9999)]
    )

    diff = DiffService().compare(previous, current, now=NOW)

    assert [i.name for i in diff.new_instructions] == ["Instrucciones Tarea 1"]


# --- INSTRUCTIONS absorbidas por su foro (evento module="forum") ---

def test_new_instruction_with_matching_forum_is_suppressed():
    pdf = instruction(618295, "03634 Foro 1", "1773181058")
    previous = snapshot_with_instructions([])
    current = snapshot_with_instructions([pdf], events=[forum("Foro 1")])

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.new_instructions == []


def test_instruction_pdf_removal_silenced_when_forum_exists():
    pdf = instruction(618295, "Foro No.1", "1773181058")
    previous = snapshot_with_instructions([pdf], events=[forum("Foro 1")])
    current = snapshot_with_instructions([], events=[forum("Foro 1")])

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.removed_instructions == []


def test_non_forum_event_does_not_supersede_instruction():
    # Un evento que no es de foro (p. ej. un aviso) no es espacio de entrega.
    pdf = instruction(618295, "Foro 1", "1773181058")
    aviso = forum("Foro 1")
    aviso.module = None
    previous = snapshot_with_instructions([])
    current = snapshot_with_instructions([pdf], events=[aviso])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [i.name for i in diff.new_instructions] == ["Foro 1"]


def test_forum_in_other_course_does_not_supersede():
    pdf = instruction(618295, "Foro 1", "1773181058")
    previous = snapshot_with_instructions([])
    current = snapshot_with_instructions([pdf], events=[forum("Foro 1", course_id=9999)])

    diff = DiffService().compare(previous, current, now=NOW)

    assert [i.name for i in diff.new_instructions] == ["Foro 1"]


# --- INSTRUCTIONS absorbidas por un entregable YA VENCIDO ---
# El entregable vencido se filtra de assignments/events (no se notifica), pero
# sigue en deliverable_refs, así que su instrucción debe quedar absorbida igual.

def test_instruction_for_expired_forum_is_suppressed():
    pdf = instruction(618295, "Foro No.1", "1773181058")
    previous = snapshot_with_instructions([])
    # events vacío (el foro venció y se filtró), pero el ref del foro persiste.
    current = snapshot_with_instructions(
        [pdf], events=[], deliverable_refs=[DeliverableRef(9460, "Foro 1")]
    )

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.new_instructions == []


def test_instruction_for_past_assignment_is_suppressed():
    pdf = instruction(618295, "Instrucciones Tarea 1", "1773181058")
    previous = snapshot_with_instructions([])
    # assignments vacío (la tarea venció), pero el ref de la tarea persiste.
    current = snapshot_with_instructions(
        [pdf], assignments=[], deliverable_refs=[DeliverableRef(9460, "Tarea 1")]
    )

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.new_instructions == []


def test_expired_deliverable_silences_instruction_removal():
    # El PDF se había notificado (antes no existía el entregable); ahora aparece
    # el foro pero ya vencido. No debe dispararse "🔴 [Instrucción]".
    pdf = instruction(618295, "Foro No.1", "1773181058")
    previous = snapshot_with_instructions([pdf])
    current = snapshot_with_instructions(
        [], events=[], deliverable_refs=[DeliverableRef(9460, "Foro 1")]
    )

    diff = DiffService().compare(previous, current, now=NOW)

    assert diff.removed_instructions == []
