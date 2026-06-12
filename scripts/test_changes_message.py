from datetime import datetime, timezone

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.diff_result import DiffResult
from src.infrastructure.external.telegram.message_builder import TelegramMessageBuilder


def main() -> None:
    builder = TelegramMessageBuilder()

    diff = DiffResult(
        new_assignments=[
            Assignment(
                moodle_assignment_id=101,
                moodle_course_id=777,
                name="Ensayo 1",
                due_date=datetime(2026, 6, 18, 23, 0, tzinfo=timezone.utc),
                allow_submissions_from=None,
                cutoff_date=None,
                course_name="Innovación y Tecnología",
            )
        ],
        updated_assignments=[],
        removed_assignments=[
            Assignment(
                moodle_assignment_id=103,
                moodle_course_id=999,
                name="Tarea vieja eliminada",
                due_date=None,
                allow_submissions_from=None,
                cutoff_date=None,
                course_name=None,
            )
        ],
        new_events=[
            CalendarEvent(
                moodle_event_id=201,
                name="Foro No. 1 pendiente",
                event_type="due",
                due_date=datetime(2026, 6, 16, 5, 59, tzinfo=timezone.utc),
                url="https://example.com/forum",
                course_id=777,
                course_name="Innovación y Tecnología",
            ),
            CalendarEvent(
                moodle_event_id=202,
                name="Recordatorio institucional",
                event_type="general",
                due_date=None,
                url=None,
                course_id=None,
                course_name=None,
            ),
        ],
        updated_events=[],
        removed_events=[
            CalendarEvent(
                moodle_event_id=203,
                name="Realizar juego 1 cierre",
                event_type="due",
                due_date=None,
                url=None,
                course_id=999,
                course_name=None,
            )
        ],
    )

    message = builder.build_changes_message(diff)
    print(message)


if __name__ == "__main__":
    main()