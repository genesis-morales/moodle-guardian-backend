from html import escape

from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.domain.entities.diff_result import DiffResult


class TelegramMessageBuilder(NotificationMessageBuilder):
    def build_welcome_message(self) -> str:
        return (
            "<b>Guardian Unediano</b>\n\n"
            "¡Bienvenido(a)! Tu conexión con Telegram quedó lista.\n"
            "A partir de ahora podré avisarte sobre tareas, cambios importantes y eventos de tu plataforma.\n\n"
            "Gracias por activar tus notificaciones."
        )

    def build_test_message(self) -> str:
        return (
            "<b>Guardian Unediano</b>\n\n"
            "Conexión con Telegram lista.\n"
            "Ya puedes recibir alertas de tareas y eventos."
        )

    def build_changes_message(self, diff: DiffResult) -> str:
        if not diff.has_changes:
            return (
                "<b>Guardian Unediano</b>\n\n"
                "No detecté cambios nuevos en este momento."
            )

        lines: list[str] = [
            "<b>Guardian Unediano</b>",
            "",
            "<b>Cambios detectados:</b>",
        ]

        if diff.new_assignments:
            lines.append("")
            lines.append("<b>Nuevas tareas</b>")
            for assignment in diff.new_assignments[:5]:
                name = escape(assignment.name)
                due = self._format_datetime(assignment.due_date)
                lines.append(f"- {name} — {due}")

        if diff.updated_assignments:
            lines.append("")
            lines.append("<b>Tareas actualizadas</b>")
            for change in diff.updated_assignments[:5]:
                name = escape(change.current.name)
                fields = ", ".join(change.changed_fields)
                lines.append(f"- {name} (cambió: {fields})")

        if diff.removed_assignments:
            lines.append("")
            lines.append("<b>Tareas eliminadas</b>")
            for assignment in diff.removed_assignments[:5]:
                name = escape(assignment.name)
                lines.append(f"- {name}")

        if diff.new_events:
            lines.append("")
            lines.append("<b>Nuevos eventos</b>")
            for event in diff.new_events[:5]:
                name = escape(event.name)
                due = self._format_datetime(event.due_date)
                lines.append(f"- {name} — {due}")

        if diff.updated_events:
            lines.append("")
            lines.append("<b>Eventos actualizados</b>")
            for change in diff.updated_events[:5]:
                name = escape(change.current.name)
                fields = ", ".join(change.changed_fields)
                lines.append(f"- {name} (cambió: {fields})")

        if diff.removed_events:
            lines.append("")
            lines.append("<b>Eventos eliminados</b>")
            for event in diff.removed_events[:5]:
                name = escape(event.name)
                lines.append(f"- {name}")

        message = "\n".join(lines)

        if len(message) > 4000:
            return (
                "<b>Guardian Unediano</b>\n\n"
                "Detecté muchos cambios nuevos en tu plataforma.\n"
                "Te recomiendo revisar el detalle en la aplicación."
            )

        return message

    def _format_datetime(self, value) -> str:
        if value is None:
            return "sin fecha"
        return value.strftime("%Y-%m-%d %H:%M")