import logging
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.application.ports.notification_message_builder import (
    NotificationMessageBuilder,
)
from src.config.settings import get_settings
from src.domain.entities.diff_result import DiffResult

logger = logging.getLogger(__name__)

# Etiqueta por módulo de Moodle (mismo criterio que el builder de Telegram).
_MODULE_TAGS = {
    "forum": "Foro",
    "quiz": "Quiz",
    "assign": "Entrega",
    "turnitintooltwo": "Entrega",
    "scorm": "Actividad",
}

_DIAS_SEMANA = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


class EmailMessageBuilder(NotificationMessageBuilder):
    """Construye el cuerpo HTML de email de cada notificación.

    Mismo protocolo que `TelegramMessageBuilder`, pero emitiendo HTML válido de email
    (`<p>`, `<ul>`, `<h2>`…) en vez del subset de Telegram (que solo admite `<b>`,
    `<i>`, `<code>`, `<a>` y usa `\\n` como layout). No hay límite de 4000 chars.
    """

    def __init__(self) -> None:
        tz_name = get_settings().timezone
        try:
            self._tz = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            logger.warning("Zona horaria inválida '%s', usando UTC", tz_name)
            self._tz = ZoneInfo("UTC")

    # --- Envoltura común ---
    def _wrap(self, inner: str) -> str:
        return (
            '<div style="font-family:Arial,Helvetica,sans-serif;color:#1f2937;'
            'max-width:600px;margin:0 auto;line-height:1.5">'
            f"{inner}"
            '<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">'
            '<p style="font-size:12px;color:#9ca3af">CampusGuardian — tu asistente '
            "académico. Recibís este correo porque activaste las alertas por email.</p>"
            "</div>"
        )

    def _heading(self, text: str) -> str:
        return f'<h2 style="font-size:18px;margin:0 0 12px">{escape(text)}</h2>'

    # --- Mensajes simples ---
    def build_welcome_message(self) -> str:
        return self._wrap(
            self._heading("🤖 CampusGuardian activado")
            + "<p>Vínculo exitoso. Tu asistente académico ya está corriendo en "
            "segundo plano.</p>"
            "<p>Vas a recibir alertas cada vez que detecte nuevas actividades, "
            "tareas o avisos en tu plataforma universitaria.</p>"
            "<p><em>¡Muchos éxitos en tus estudios! 📚</em></p>"
        )

    def build_test_message(self) -> str:
        return self._wrap(
            self._heading("🤖 CampusGuardian")
            + "<p>Conexión de prueba exitosa. El monitoreo asíncrono está listo.</p>"
        )

    def build_relink_success_message(self) -> str:
        return self._wrap(
            self._heading("✅ CampusGuardian reactivado")
            + "<p>Tu vínculo se reactivó correctamente. Volví a vigilar tu campus y "
            "te avisaré de cualquier novedad.</p>"
        )

    def build_token_expired_message(
        self, relink_url: str, site_label: str | None = None
    ) -> str:
        campus = f" de {escape(site_label)}" if site_label else ""
        cta = ""
        if relink_url:
            url = escape(relink_url)
            cta = (
                f'<p><a href="{url}" style="display:inline-block;background:#2563eb;'
                'color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none">'
                "Regenerar mi llave</a></p>"
            )
        return self._wrap(
            self._heading("🔴 Conexión expirada")
            + f"<p>Tu vínculo con Moodle{campus} venció, así que dejé de revisar ese "
            "campus y no vas a recibir más avisos de ahí hasta reactivarlo.</p>"
            + cta
        )

    # --- Cambios detectados ---
    def build_changes_message(
        self, diff: DiffResult, site_label: str | None = None
    ) -> str:
        header = "🤖 CampusGuardian"
        if site_label:
            header = f"🤖 CampusGuardian • {site_label}"

        if not diff.has_changes:
            return self._wrap(
                self._heading(header) + "<p>No detecté cambios nuevos por ahora.</p>"
            )

        # course label -> list[str] (líneas <li> ya formateadas)
        courses: dict[str, list[str]] = {}

        def bucket(label: str) -> list[str]:
            return courses.setdefault(label, [])

        for a in diff.new_assignments:
            bucket(self._course_label(a, "moodle_course_id")).append(
                self._li("🟢 Tarea", a.name, self._due(getattr(a, "due_date", None)))
            )
        for change in diff.updated_assignments:
            bucket(self._course_label(change.current, "moodle_course_id")).append(
                self._li("🟢 Tarea (actualizada)", change.current.name)
            )
        for a in diff.removed_assignments:
            bucket(self._course_label(a, "moodle_course_id")).append(
                self._li("🔴 Tarea", a.name)
            )

        for e in diff.new_events:
            bucket(self._course_label(e, "course_id")).append(
                self._li(
                    f"🟢 {self._event_tag(e)}", e.name,
                    self._due(getattr(e, "due_date", None)),
                )
            )
        for change in diff.updated_events:
            bucket(self._course_label(change.current, "course_id")).append(
                self._li(f"🟢 {self._event_tag(change.current)} (actualizado)", change.current.name)
            )
        for e in diff.removed_events:
            bucket(self._course_label(e, "course_id")).append(
                self._li(f"🔴 {self._event_tag(e)}", e.name)
            )

        for i in diff.new_instructions:
            bucket(self._course_label(i, "course_id")).append(
                self._li("🟢 Instrucción", i.name)
            )
        for i in diff.removed_instructions:
            bucket(self._course_label(i, "course_id")).append(
                self._li("🔴 Instrucción", i.name)
            )

        for ann in diff.new_announcements:
            bucket(self._course_label(ann, "course_id")).append(
                self._li("🟢 Anuncio", ann.name)
            )
        for change in diff.updated_announcements:
            bucket(self._course_label(change.current, "course_id")).append(
                self._li("🟢 Anuncio (actualizado)", change.current.name)
            )

        blocks = [self._heading(header), "<p>Detecté cambios:</p>"]
        for label, lines in courses.items():
            if not lines:
                continue
            blocks.append(
                f'<h3 style="font-size:15px;margin:16px 0 6px">📚 {escape(label)}</h3>'
                f'<ul style="margin:0;padding-left:20px">{"".join(lines)}</ul>'
            )

        if diff.new_messages:
            counts: dict[str, int] = {}
            for msg in diff.new_messages:
                sender = msg.sender_name or "Alguien"
                counts[sender] = counts.get(sender, 0) + 1
            items = "".join(
                f"<li><strong>{escape(s)}</strong> — {c} "
                f"{'mensajes nuevos' if c > 1 else 'mensaje nuevo'}</li>"
                for s, c in counts.items()
            )
            blocks.append(
                '<h3 style="font-size:15px;margin:16px 0 6px">💬 Mensajes</h3>'
                f'<ul style="margin:0;padding-left:20px">{items}</ul>'
            )

        return self._wrap("".join(blocks))

    # --- Digest y recordatorios ---
    def build_weekly_digest_message(self, items) -> str:
        if not items:
            return self._wrap(
                self._heading("🗓️ Resumen semanal")
                + "<p>¡Vas al día! No tenés entregas pendientes registradas. 🎉</p>"
            )
        return self._wrap(
            self._heading("🗓️ Resumen semanal")
            + "<p>Tus entregas pendientes:</p>"
            + self._grouped_deliverables(items, with_weekday=True)
        )

    def build_deadline_reminder_message(self, items, days: int) -> str:
        if not items:
            return self._wrap(
                self._heading("⏰ Recordatorio de entregas")
                + "<p>No tenés entregas próximas.</p>"
            )
        return self._wrap(
            self._heading("⏰ Recordatorio de entregas")
            + "<p>Estas entregas cierran pronto:</p>"
            + self._grouped_deliverables(items, with_weekday=False)
        )

    # --- Helpers ---
    def _grouped_deliverables(self, items, *, with_weekday: bool) -> str:
        courses: dict[str, list] = {}
        for item in items:
            label = item.course_name or "Avisos Generales"
            courses.setdefault(label, []).append(item)

        blocks = []
        for label, group in courses.items():
            lines = []
            for item in group:
                tag = self._deliverable_tag(item)
                when = (
                    self._format_datetime_with_weekday(item.deadline)
                    if with_weekday
                    else self._format_datetime(item.deadline)
                )
                lines.append(self._li(f"🔹 {tag}", item.name, when))
            blocks.append(
                f'<h3 style="font-size:15px;margin:16px 0 6px">📚 {escape(label)}</h3>'
                f'<ul style="margin:0;padding-left:20px">{"".join(lines)}</ul>'
            )
        return "".join(blocks)

    def _li(self, tag: str, name: str, when: str | None = None) -> str:
        suffix = (
            f' — <code style="color:#6b7280">{escape(when)}</code>' if when else ""
        )
        return f"<li><strong>{escape(tag)}</strong> {escape(name)}{suffix}</li>"

    def _course_label(self, item, id_attr: str) -> str:
        name = getattr(item, "course_name", None)
        if name:
            return name
        course_id = getattr(item, id_attr, None)
        if course_id:
            return f"Curso {course_id}"
        return "Avisos Generales"

    def _event_tag(self, event) -> str:
        module = (getattr(event, "module", None) or "").lower()
        return _MODULE_TAGS.get(module, "Aviso")

    def _deliverable_tag(self, item) -> str:
        if getattr(item, "kind", None) == "assignment":
            return "Tarea"
        return _MODULE_TAGS.get((getattr(item, "module", None) or "").lower(), "Aviso")

    def _due(self, value) -> str | None:
        return self._format_datetime(value) if value is not None else None

    def _format_datetime(self, value) -> str:
        if value is None:
            return "sin fecha"
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("UTC"))
        value = value.astimezone(self._tz)
        return value.strftime("%d %b, %I:%M %p").lower()

    def _format_datetime_with_weekday(self, value) -> str:
        if value is None:
            return "sin fecha"
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("UTC"))
        value = value.astimezone(self._tz)
        dia = _DIAS_SEMANA[value.weekday()]
        return f"{dia} {value.strftime('%d %b, %I:%M %p').lower()}"
