from html import escape
from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.domain.entities.diff_result import DiffResult


class TelegramMessageBuilder(NotificationMessageBuilder):
    def build_welcome_message(self) -> str:
        return (
            "<b>🤖 Moodle Guardian • Activado</b>\n\n"
            "Vínculo exitoso. Tu asistente académico ya está corriendo en segundo plano.\n\n"
            "Recibirás alertas en este chat cada vez que detecte nuevas actividades, "
            "tareas o avisos generales en tu plataforma universitaria.\n\n"
            "<i>¡Muchos éxitos en tus estudios! 📚✨</i>"
        )

    def build_test_message(self) -> str:
        return (
            "<b>🤖 Moodle Guardian</b>\n\n"
            "Conexión de prueba exitosa.\n"
            "El sistema de monitoreo asíncrono está listo."
        )

    def build_changes_message(self, diff: DiffResult) -> str:
        if not diff.has_changes:
            return (
                "<b>🤖 Moodle Guardian</b>\n\n"
                "No detecté cambios nuevos en este momento."
            )

        # course label -> {"new": [...], "removed": [...]}
        courses: dict[str, dict[str, list[str]]] = {}

        def bucket(label: str) -> dict[str, list[str]]:
            if label not in courses:
                courses[label] = {"new": [], "removed": []}
            return courses[label]

        # --- ASSIGNMENTS ---
        for assignment in diff.new_assignments:
            bucket(self._assignment_course_label(assignment))["new"].append(
                self._assignment_line("🟢", "[Tarea]", assignment)
            )
        for change in diff.updated_assignments:
            # En el formato minimalista tratamos los updates/cambios de fecha como alertas de atención (🟢)
            bucket(self._assignment_course_label(change.current))["new"].append(
                self._changed_line("🟢", "[Tarea Modificada]", change.current, change.changed_fields)
            )
        for assignment in diff.removed_assignments:
            bucket(self._assignment_course_label(assignment))["removed"].append(
                self._assignment_line("🔴", "[Tarea]", assignment, with_due=False)
            )

        # --- EVENTS / ANNOUNCEMENTS ---
        for event in diff.new_events:
            label = self._event_course_label(event)
            tag = "[Anuncio]" if label == "Avisos Generales" else "[Evento]"
            bucket(label)["new"].append(
                self._event_line("🟢", tag, event)
            )
        for change in diff.updated_events:
            label = self._event_course_label(change.current)
            tag = "[Anuncio Modificado]" if label == "Avisos Generales" else "[Evento Modificado]"
            bucket(label)["new"].append(
                self._changed_line("🟢", tag, change.current, change.changed_fields)
            )
        for event in diff.removed_events:
            label = self._event_course_label(event)
            tag = "[Anuncio]" if label == "Avisos Generales" else "[Evento]"
            bucket(label)["removed"].append(
                self._event_line("🔴", tag, event, with_due=False)
            )

        # --- BUILD MESSAGE ---
        lines: list[str] = [
            "<b>🤖 Moodle Guardian</b>",
            "",
            "Detecté cambios:",
        ]

        # Primero procesamos los cursos académicos normales
        for course_label, groups in courses.items():
            if course_label == "Avisos Generales":
                continue

            entries = groups["new"] + groups["removed"]
            if not entries:
                continue

            lines.append("")
            lines.append(f"📚 <b>{escape(course_label)}</b>")
            lines.extend(entries)

        # Dejamos "Avisos Generales" siempre al final del mensaje si existe
        if "Avisos Generales" in courses:
            gen_groups = courses["Avisos Generales"]
            gen_entries = gen_groups["new"] + gen_groups["removed"]
            if gen_entries:
                lines.append("")
                lines.append("📢 <b>Avisos Generales</b>")
                lines.extend(gen_entries)

        message = "\n".join(lines)

        if len(message) > 4000:
            return (
                "<b>🤖 Moodle Guardian</b>\n\n"
                "Detecté múltiples cambios nuevos en tu plataforma.\n"
                "Te recomiendo revisar el detalle completo en tu campus virtual."
            )

        return message

    def _assignment_course_label(self, assignment) -> str:
        if assignment.course_name:
            return assignment.course_name
        return f"Curso {assignment.moodle_course_id}"

    def _event_course_label(self, event) -> str:
        if event.course_name:
            return event.course_name
        if event.course_id is not None:
            return f"Curso {event.course_id}"
        # Mapeo directo semántico que discutimos
        return "Avisos Generales"

    def _assignment_line(self, marker: str, tag: str, assignment, with_due: bool = True) -> str:
        name = escape(assignment.name)
        if with_due and assignment.due_date is not None:
            return f"{marker} {tag} {name} — <code>{self._format_datetime(assignment.due_date)}</code>"
        return f"{marker} {tag} {name}"

    def _event_line(self, marker: str, tag: str, event, with_due: bool = True) -> str:
        name = escape(event.name)
        if with_due and event.due_date is not None:
            return f"{marker} {tag} {name} — <code>{self._format_datetime(event.due_date)}</code>"
        return f"{marker} {tag} {name}"

    def _changed_line(self, marker: str, tag: str, item, changed_fields: list[str]) -> str:
        safe_name = escape(item.name)
        fields = ", ".join(changed_fields)

        # Si cambió la fecha de entrega, la resaltamos de forma limpia
        if "due_date" in changed_fields and getattr(item, "due_date", None) is not None:
            return f"{marker} {tag} {safe_name} (Cambió fecha) — <code>{self._format_datetime(item.due_date)}</code>"

        return f"{marker} {tag} {safe_name} (Ajuste en: {fields})"

    def _format_datetime(self, value) -> str:
        if value is None:
            return "sin fecha"

        # %d -> Día (16)
        # %b -> Mes abreviado (jun)
        # %I -> Hora formato 12h (05)
        # %M -> Minutos (59)
        # %p -> AM/PM
        fecha_formateada = value.strftime("%d %b, %I:%M %p")

        # .lower() convierte el AM/PM a am/pm automáticamente
        return fecha_formateada.lower()