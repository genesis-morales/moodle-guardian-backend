"""Tests de caracterización de TelegramMessageBuilder.build_changes_message.

Congelan la salida ACTUAL del formateo de cambios (que hoy no tenía cobertura)
antes del refactor de "fuente rastreable" (feat 1a). El refactor cambia el motor
de diff y la persistencia, NO el formato de los mensajes: estos tests son la red
que detecta cualquier regresión visible.

Nota de zona horaria: el builder usa `settings.timezone` (default
America/Costa_Rica = UTC-6, sin DST). Las fechas esperadas se calculan para esa
zona: 2026-06-16 23:59 UTC -> 17:59 local -> "16 jun, 05:59 pm".
"""

from datetime import UTC, datetime

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.diff_result import (
    ChangedAssignment,
    ChangedInstruction,
    DiffResult,
)
from src.domain.entities.instruction import Instruction
from src.infrastructure.external.telegram.message_builder import TelegramMessageBuilder

DUE = datetime(2026, 6, 16, 23, 59, tzinfo=UTC)
DUE_LOCAL_STR = "16 jun, 05:59 pm"  # UTC-6


def builder() -> TelegramMessageBuilder:
    return TelegramMessageBuilder()


def assignment(name: str, *, course_name: str | None = "Matemática", due=DUE) -> Assignment:
    return Assignment(
        moodle_assignment_id=1,
        moodle_course_id=100,
        name=name,
        due_date=due,
        course_name=course_name,
    )


def event(name: str, *, module: str | None = "forum", course_name="Física", course_id=200, due=DUE) -> CalendarEvent:
    return CalendarEvent(
        moodle_event_id=2,
        course_id=course_id,
        name=name,
        event_type="due",
        due_date=due,
        module=module,
        course_name=course_name,
    )


def instruction(name: str, *, course_name="Química") -> Instruction:
    return Instruction(moodle_id=3, course_id=300, name=name, course_name=course_name)


# --- estado base ---

def test_no_changes_returns_fixed_message():
    msg = builder().build_changes_message(DiffResult())
    assert msg == (
        "<b>🤖 Moodle Guardian</b>\n\n"
        "No detecté cambios nuevos en este momento."
    )


def test_header_present_when_changes():
    msg = builder().build_changes_message(DiffResult(new_assignments=[assignment("Tarea 1")]))
    assert msg.startswith("<b>🤖 Moodle Guardian</b>\n\nDetecté cambios:")


# --- assignments ---

def test_new_assignment_line_with_due_and_course_header():
    msg = builder().build_changes_message(DiffResult(new_assignments=[assignment("Tarea 1")]))
    assert "📚 <b>Matemática</b>" in msg
    assert f"🟢 [Tarea] Tarea 1 — <code>{DUE_LOCAL_STR}</code>" in msg


def test_removed_assignment_line_red_and_no_due():
    msg = builder().build_changes_message(DiffResult(removed_assignments=[assignment("Tarea 1")]))
    assert "🔴 [Tarea] Tarea 1" in msg
    assert DUE_LOCAL_STR not in msg  # los removidos no muestran fecha


def test_updated_assignment_due_date_shows_cambio_fecha():
    change = ChangedAssignment(
        previous=assignment("Tarea 1"),
        current=assignment("Tarea 1"),
        changed_fields=["due_date"],
    )
    msg = builder().build_changes_message(DiffResult(updated_assignments=[change]))
    assert f"🟢 [Tarea Modificada] Tarea 1 (Cambió fecha) — <code>{DUE_LOCAL_STR}</code>" in msg


def test_updated_assignment_other_field_shows_ajuste_en():
    change = ChangedAssignment(
        previous=assignment("Tarea 1"),
        current=assignment("Tarea 1"),
        changed_fields=["name"],
    )
    msg = builder().build_changes_message(DiffResult(updated_assignments=[change]))
    assert "🟢 [Tarea Modificada] Tarea 1 (Ajuste en: name)" in msg


# --- events (tag dinámico por módulo) ---

def test_new_event_uses_module_tag():
    msg = builder().build_changes_message(DiffResult(new_events=[event("Foro semana 1", module="forum")]))
    assert f"🟢 [Foro] Foro semana 1 — <code>{DUE_LOCAL_STR}</code>" in msg


def test_event_unknown_module_falls_back_to_aviso():
    msg = builder().build_changes_message(DiffResult(new_events=[event("Algo", module=None)]))
    assert "🟢 [Aviso] Algo" in msg


# --- instructions (sin fecha) ---

def test_new_instruction_line_no_date():
    msg = builder().build_changes_message(DiffResult(new_instructions=[instruction("Instrucciones Tarea 1")]))
    assert "🟢 [Instrucción] Instrucciones Tarea 1" in msg
    assert DUE_LOCAL_STR not in msg


def test_updated_instruction_shows_contenido_actualizado():
    change = ChangedInstruction(
        previous=instruction("Instrucciones Tarea 1"),
        current=instruction("Instrucciones Tarea 1"),
        changed_fields=["content"],
    )
    msg = builder().build_changes_message(DiffResult(updated_instructions=[change]))
    assert "🟢 [Instrucción] Instrucciones Tarea 1 (Contenido actualizado)" in msg


# --- bucketing por curso + "Avisos Generales" al final ---

def test_avisos_generales_go_last():
    # Un evento sin curso (course_id=0, sin course_name) cae en "Avisos Generales".
    general = event("Aviso global", module=None, course_name=None, course_id=0)
    course_item = assignment("Tarea 1", course_name="Matemática")
    msg = builder().build_changes_message(
        DiffResult(new_assignments=[course_item], new_events=[general])
    )
    assert "📚 <b>Matemática</b>" in msg
    assert "📢 <b>Avisos Generales</b>" in msg
    assert msg.index("📚 <b>Matemática</b>") < msg.index("📢 <b>Avisos Generales</b>")


def test_name_is_html_escaped():
    msg = builder().build_changes_message(
        DiffResult(new_assignments=[assignment("Tarea <b>&", course_name="Curso & Co")])
    )
    assert "Tarea &lt;b&gt;&amp;" in msg
    assert "📚 <b>Curso &amp; Co</b>" in msg


# --- overflow ---

def test_overflow_returns_fallback():
    many = [
        assignment(f"Tarea numero {i} con nombre bien largo para inflar", course_name=f"Curso {i}")
        for i in range(200)
    ]
    msg = builder().build_changes_message(DiffResult(new_assignments=many))
    assert msg == (
        "<b>🤖 Moodle Guardian</b>\n\n"
        "Detecté múltiples cambios nuevos en tu plataforma.\n"
        "Te recomiendo revisar el detalle completo en tu campus virtual."
    )
