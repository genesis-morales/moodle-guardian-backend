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


# --- announcements (foro Novedades) ---

def announcement(name: str, *, course_name="Historia", course_id=400):
    from src.domain.entities.announcement import Announcement
    return Announcement(
        discussion_id=7,
        course_id=course_id,
        name=name,
        content_fingerprint="100",
        course_name=course_name,
    )


def test_new_announcement_under_its_course():
    msg = builder().build_changes_message(
        DiffResult(new_announcements=[announcement("Cambio de aula")])
    )
    assert "📚 <b>Historia</b>" in msg
    assert "🟢 [Anuncio] Cambio de aula" in msg


def test_updated_announcement_shows_actualizado():
    from src.domain.entities.diff_result import Change
    change = Change(
        previous=announcement("Aviso"),
        current=announcement("Aviso"),
        changed_fields=["content"],
    )
    msg = builder().build_changes_message(DiffResult(updated_announcements=[change]))
    assert "🟢 [Anuncio] Aviso (Actualizado)" in msg


# --- mensajes privados (sección propia, agrupada por remitente) ---

def message(msg_id: int, sender: str):
    from src.domain.entities.message import Message
    return Message(message_id=msg_id, sender_name=sender)


def test_messages_grouped_by_sender_with_count():
    msg = builder().build_changes_message(
        DiffResult(new_messages=[
            message(1, "Prof. García"),
            message(2, "Prof. García"),
            message(3, "Coordinación"),
        ])
    )
    assert "💬 <b>Mensajes</b>" in msg
    assert "🟢 <b>Prof. García</b> — 2 mensajes nuevos" in msg
    assert "🟢 <b>Coordinación</b> — 1 mensaje nuevo" in msg


def test_messages_only_still_notifies():
    # Un diff con solo mensajes nuevos igual produce mensaje (has_changes=True).
    msg = builder().build_changes_message(DiffResult(new_messages=[message(1, "X")]))
    assert msg.startswith("<b>🤖 Moodle Guardian</b>")
    assert "💬 <b>Mensajes</b>" in msg


# --- etiqueta de campus (multi-campus) ---

def test_site_label_in_header_when_provided():
    msg = builder().build_changes_message(
        DiffResult(new_assignments=[assignment("Tarea 1")]), site_label="Educa"
    )
    assert msg.startswith("<b>🤖 Moodle Guardian • Educa</b>")


def test_no_site_label_keeps_classic_header():
    msg = builder().build_changes_message(
        DiffResult(new_assignments=[assignment("Tarea 1")])
    )
    assert msg.startswith("<b>🤖 Moodle Guardian</b>\n")
