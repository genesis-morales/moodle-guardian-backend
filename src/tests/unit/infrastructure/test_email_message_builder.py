"""Tests de EmailMessageBuilder.

Espejo del test de TelegramMessageBuilder, pero verificando la salida HTML de email
(`<p>`, `<ul>`, `<h2>`…) en vez del subset de Telegram. No congela el HTML byte-a-byte
(el estilo inline puede cambiar); verifica el CONTENIDO semántico: que aparezcan los
ítems bajo su curso, que el HTML se escape, y que las variantes de mensaje se rendericen.

Zona horaria: usa `settings.timezone` (default America/Costa_Rica = UTC-6, sin DST).
2026-06-16 23:59 UTC -> 17:59 local -> "16 jun, 05:59 pm".
"""

from datetime import UTC, datetime

from src.application.dto.digest_dto import DeliverableItem
from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.diff_result import Change, DiffResult
from src.domain.entities.instruction import Instruction
from src.domain.entities.message import Message
from src.infrastructure.external.brevo.email_message_builder import EmailMessageBuilder

DUE = datetime(2026, 6, 16, 23, 59, tzinfo=UTC)
DUE_LOCAL_STR = "16 jun, 05:59 pm"  # UTC-6


def builder() -> EmailMessageBuilder:
    return EmailMessageBuilder()


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


def deliverable(name: str, *, course_name="Matemática", kind="assignment", module=None, deadline=DUE) -> DeliverableItem:
    return DeliverableItem(
        name=name, course_name=course_name, deadline=deadline,
        module=module, kind=kind, key="k",
    )


# --- envoltura HTML común ---

def test_wrap_produces_html_document_with_footer():
    msg = builder().build_test_message()
    assert msg.startswith("<div")
    assert msg.endswith("</div>")
    assert "CampusGuardian" in msg
    # El footer explica por qué recibe el correo (buena práctica de deliverability).
    assert "alertas por email" in msg


# --- mensajes simples ---

def test_welcome_message_html():
    msg = builder().build_welcome_message()
    assert "<h2" in msg
    assert "CampusGuardian activado" in msg


def test_relink_success_message_html():
    msg = builder().build_relink_success_message()
    assert "reactiv" in msg.lower()


def test_token_expired_renders_cta_button_with_url():
    msg = builder().build_token_expired_message(
        relink_url="https://web.app/relink?x=1", site_label="Educa"
    )
    assert 'href="https://web.app/relink?x=1"' in msg
    assert "Educa" in msg
    assert "Regenerar mi llave" in msg


def test_token_expired_without_url_has_no_cta():
    msg = builder().build_token_expired_message(relink_url="", site_label=None)
    assert "<a href" not in msg
    assert "expir" in msg.lower()


# --- cambios detectados ---

def test_changes_no_changes_message():
    msg = builder().build_changes_message(DiffResult())
    assert "No detecté cambios" in msg


def test_changes_assignment_under_its_course_with_date():
    msg = builder().build_changes_message(DiffResult(new_assignments=[assignment("Tarea 1")]))
    assert "📚 Matemática" in msg
    assert "Tarea 1" in msg
    assert DUE_LOCAL_STR in msg
    assert "<li>" in msg


def test_changes_event_uses_module_tag():
    msg = builder().build_changes_message(DiffResult(new_events=[event("Foro semana 1", module="forum")]))
    assert "Foro" in msg
    assert "Foro semana 1" in msg


def test_changes_announcement_and_updated():
    def announcement(name):
        from src.domain.entities.announcement import Announcement
        return Announcement(
            discussion_id=7, course_id=400, name=name,
            content_fingerprint="1", course_name="Historia",
        )

    change = Change(
        previous=announcement("Aviso"), current=announcement("Aviso"),
        changed_fields=["content"],
    )
    msg = builder().build_changes_message(
        DiffResult(new_announcements=[announcement("Cambio de aula")], updated_announcements=[change])
    )
    assert "📚 Historia" in msg
    assert "Cambio de aula" in msg
    assert "Anuncio" in msg


def test_changes_messages_grouped_by_sender_with_count():
    msg = builder().build_changes_message(
        DiffResult(new_messages=[
            Message(message_id=1, sender_name="Prof. García"),
            Message(message_id=2, sender_name="Prof. García"),
            Message(message_id=3, sender_name="Coordinación"),
        ])
    )
    assert "💬 Mensajes" in msg
    assert "Prof. García" in msg
    assert "2 mensajes nuevos" in msg
    assert "1 mensaje nuevo" in msg


def test_changes_html_escapes_names():
    msg = builder().build_changes_message(
        DiffResult(new_assignments=[assignment("Tarea <b>&", course_name="Curso & Co")])
    )
    # El nombre del ítem y del curso van escapados: no se cuela HTML de datos de Moodle.
    assert "Tarea &lt;b&gt;&amp;" in msg
    assert "Curso &amp; Co" in msg


def test_changes_instruction_no_date():
    msg = builder().build_changes_message(
        DiffResult(new_instructions=[Instruction(moodle_id=3, course_id=300, name="Instrucciones", course_name="Química")])
    )
    assert "Instrucción" in msg
    assert "Instrucciones" in msg
    assert DUE_LOCAL_STR not in msg


# --- digest y recordatorios ---

def test_weekly_digest_empty_is_upbeat():
    msg = builder().build_weekly_digest_message([])
    assert "día" in msg.lower()
    assert "Resumen semanal" in msg


def test_weekly_digest_groups_by_course_with_weekday():
    msg = builder().build_weekly_digest_message([deliverable("Tarea 1", course_name="Matemática")])
    assert "📚 Matemática" in msg
    assert "Tarea 1" in msg
    # con weekday: prefijo del día (16 jun cae martes -> "mar").
    assert "mar" in msg


def test_deadline_reminder_empty():
    msg = builder().build_deadline_reminder_message([], days=3)
    assert "No tenés entregas próximas" in msg


def test_deadline_reminder_lists_items():
    msg = builder().build_deadline_reminder_message(
        [deliverable("Quiz 2", course_name="Física", kind="event", module="quiz")], days=3
    )
    assert "📚 Física" in msg
    assert "Quiz 2" in msg
    assert "Quiz" in msg


def test_site_label_in_changes_header():
    msg = builder().build_changes_message(
        DiffResult(new_assignments=[assignment("Tarea 1")]), site_label="Educa"
    )
    assert "CampusGuardian • Educa" in msg
