import logging
from datetime import UTC, datetime, timedelta
from typing import Callable, Optional

from src.application.dto.sync_dto import (
    AbsorbedInstructionItem,
    AnnouncementItemOutput,
    AssignmentItemOutput,
    CalendarEventItemOutput,
    DeliverableRefItem,
    InstructionItemOutput,
    ManualSyncInput,
    ManualSyncOutput,
    MessageItemOutput,
)
from src.domain.entities.moodle_connection import MoodleConnection
from src.domain.exceptions.domain_errors import (
    DomainError,
    MoodleFeatureDisabledError,
)
from src.domain.ports.moodle_gateway import MoodleGateway
from src.domain.ports.user_repository import UserRepository

logger = logging.getLogger(__name__)


class FetchCourseSnapshotUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        moodle_gateway: MoodleGateway,
        moodle_gateway_factory: Optional[Callable[[str], MoodleGateway]] = None,
    ) -> None:
        self.user_repository = user_repository
        # Camino legacy (user-keyed): gateway global inyectado.
        self.moodle_gateway = moodle_gateway
        # Camino multi-campus: gateway ligado a la URL del sitio de la conexión.
        self.moodle_gateway_factory = moodle_gateway_factory

    async def execute(self, data: ManualSyncInput) -> ManualSyncOutput:
        """Camino legacy (user-keyed): gateway global + token del usuario. Lo siguen
        usando digest/reminder/preview mientras no migren a conexiones."""
        user = await self.user_repository.get_by_moodle_user_id(data.moodle_user_id)
        if user is None:
            raise DomainError("Usuario no encontrado.")
        return await self._fetch(
            gateway=self.moodle_gateway,
            token=user.moodle_token,
            moodle_user_id=user.moodle_user_id,
        )

    async def execute_for_connection(
        self, connection: MoodleConnection
    ) -> ManualSyncOutput:
        """Camino multi-campus: gateway apuntando a la URL del sitio de la conexión y
        credenciales de esa conexión."""
        if self.moodle_gateway_factory is None:
            raise RuntimeError(
                "moodle_gateway_factory no configurado para el scan por conexión"
            )
        gateway = self.moodle_gateway_factory(connection.base_url)
        return await self._fetch(
            gateway=gateway,
            token=connection.moodle_token,
            moodle_user_id=connection.moodle_user_id,
        )

    async def _fetch(
        self, *, gateway: MoodleGateway, token: str, moodle_user_id: int
    ) -> ManualSyncOutput:
        now = datetime.now(UTC)

        all_courses = await gateway.get_courses(
            token=token,
            moodle_user_id=moodle_user_id,
        )

        # Solo cursos del cuatrimestre vigente: descartamos los que ya cerraron
        # (cuatrimestres anteriores) para no notificar actividades de cursos que
        # el usuario ya no está cursando.
        courses = [course for course in all_courses if course.is_active(now)]

        course_ids = [course.moodle_course_id for course in courses]
        course_names = {
            course.moodle_course_id: course.fullname for course in courses
        }

        all_assignments = await gateway.get_assignments(
            token=token,
            course_ids=course_ids,
        )

        # A diferencia de los eventos (que ya vienen con ventana temporal), las
        # tareas llegan completas. Descartamos las ya vencidas para no arrastrar
        # entregas de avances/cuatrimestres pasados.
        assignments = [a for a in all_assignments if not a.is_past(now)]

        in_30_days = now + timedelta(days=30)

        calendar_events = await gateway.get_calendar_events(
            token=token,
            course_ids=course_ids,
            timestart=int(now.timestamp()),
            timeend=int(in_30_days.timestamp()),
        )

        # Los foros los obtenemos del módulo forum (no del calendario): Moodle no
        # genera evento de calendario para un foro cuya fecha está en cutoffdate.
        # Descartamos los eventos de calendario tipo forum para no duplicar.
        non_forum_events = [e for e in calendar_events if e.module != "forum"]

        forums = await gateway.get_forums(
            token=token,
            course_ids=course_ids,
        )
        # Misma ventana temporal que los eventos: vigentes y no más allá de 30 días.
        forum_events = [
            f for f in forums
            if f.due_date is not None and now <= f.due_date <= in_30_days
        ]

        events = non_forum_events + forum_events

        # Referencias a TODOS los entregables del curso SIN filtrar por fecha.
        # Sirven para absorber instrucciones: una vez existe el espacio de
        # entrega, su PDF de instrucciones deja de ser noticia aparte, AUNQUE el
        # entregable ya haya vencido (y por eso no aparezca en `assignments`/
        # `events`, que sí se filtran por fecha). Incluimos:
        #   - tareas (mod_assign), sin el filtro `is_past`,
        #   - foros (incluso sin fecha),
        #   - eventos de calendario no-foro (en algunos Moodle el "espacio de
        #     entrega" llega como evento "due"/"close" y no como mod_assign).
        seen_refs: set[tuple[int, str]] = set()
        deliverable_refs: list[DeliverableRefItem] = []

        def _add_ref(course_id: int | None, name: str) -> None:
            if not course_id:
                return
            key = (course_id, name.strip().lower())
            if key in seen_refs:
                return
            seen_refs.add(key)
            deliverable_refs.append(DeliverableRefItem(course_id=course_id, name=name))

        for a in all_assignments:
            _add_ref(a.moodle_course_id, a.name)
        for f in forums:
            _add_ref(f.course_id, f.name)
        for e in non_forum_events:
            _add_ref(e.course_id, e.name)

        # PDFs de instrucciones (recursos de archivo de cada curso). A diferencia
        # de eventos/tareas no tienen ventana temporal: nos interesa su presencia
        # y si su contenido cambió. Nos quedamos solo con los que parecen
        # instrucciones de un entregable (tarea, foro, proyecto...) y descartamos
        # el ruido genérico del curso (reglamentos, normas APA, manuales...).
        all_resources = await gateway.get_course_resources(
            token=token,
            course_ids=course_ids,
        )
        # Además del ruido genérico (is_deliverable), descartamos las
        # instrucciones cuyo espacio de entrega ya existe: las absorbe el
        # entregable (vigente o vencido). Guardamos las absorbidas aparte para
        # poder inspeccionar en debug qué se descartó y por qué.
        instructions = []
        absorbed_instructions: list[AbsorbedInstructionItem] = []
        for r in all_resources:
            if not r.is_deliverable():
                continue
            match = next(
                (
                    ref for ref in deliverable_refs
                    if ref.course_id == r.course_id and r.is_superseded_by(ref.name)
                ),
                None,
            )
            if match is None:
                instructions.append(r)
            else:
                absorbed_instructions.append(
                    AbsorbedInstructionItem(
                        course_id=r.course_id,
                        name=r.name,
                        absorbed_by=match.name,
                    )
                )

        # Colapsar duplicados (mismo curso + nombre tokenizado): el profe a veces
        # sube el mismo PDF dos veces con distinto cmid. Dedupeamos aquí, en la
        # fuente, para que TODOS los canales (Telegram/email/WhatsApp) hereden una
        # sola línea. Nos quedamos con el moodle_id más bajo (el más antiguo, la
        # identidad más estable entre scans → menos churn si borran una copia).
        deduped: dict[tuple[int, frozenset[str]], "object"] = {}
        for r in instructions:
            key = r.dedup_key()
            existing = deduped.get(key)
            if existing is None or r.moodle_id < existing.moodle_id:
                deduped[key] = r
        instructions = list(deduped.values())

        # --- ANUNCIOS (foro Novedades/News) ---
        # Fuente con curso: reutilizamos course_names para la etiqueta. Sin ventana
        # temporal (un anuncio no vence); el diff contra el snapshot previo decide
        # qué es nuevo.
        announcements = await gateway.get_announcements(
            token=token,
            course_ids=course_ids,
        )

        # --- MENSAJES PRIVADOS ---
        # Fuente global (no por curso). El propio gateway excluye los enviados por
        # el usuario. El preview viaja aquí para la notificación, pero NO se
        # persiste (ver Message.to_dict).
        # Los mensajes son una fuente OPCIONAL: si el campus tiene la mensajería
        # apagada (`$CFG->messaging`), Moodle responde errorcode `disabled`. No
        # debe tumbar el snapshot completo — degradamos con gracia a lista vacía.
        try:
            messages = await gateway.get_messages(
                token=token,
                moodle_user_id=moodle_user_id,
            )
        except MoodleFeatureDisabledError as exc:
            logger.warning(
                "Mensajería deshabilitada en el sitio; se omiten mensajes "
                "moodle_user_id=%s detail=%s",
                moodle_user_id,
                exc,
            )
            messages = []

        return ManualSyncOutput(
            moodle_user_id=moodle_user_id,
            courses_count=len(course_ids),
            assignments_count=len(assignments),
            events_count=len(events),
            instructions_count=len(instructions),
            announcements_count=len(announcements),
            messages_count=len(messages),
            assignments=[
                AssignmentItemOutput(
                    moodle_assignment_id=item.moodle_assignment_id,
                    moodle_course_id=item.moodle_course_id,
                    name=item.name,
                    due_date=int(item.due_date.timestamp()) if item.due_date else None,
                    allow_submissions_from=int(item.allow_submissions_from.timestamp())
                    if item.allow_submissions_from else None,
                    cutoff_date=int(item.cutoff_date.timestamp()) if item.cutoff_date else None,
                    course_name=course_names.get(item.moodle_course_id),
                )
                for item in assignments
            ],
            events=[
                CalendarEventItemOutput(
                    moodle_event_id=item.moodle_event_id,
                    course_id=item.course_id,
                    name=item.name,
                    event_type=item.event_type,
                    due_date=int(item.due_date.timestamp()) if item.due_date else None,
                    url=item.url,
                    module=item.module,
                    course_name=course_names.get(item.course_id),
                )
                for item in events
            ],
            instructions=[
                InstructionItemOutput(
                    moodle_id=item.moodle_id,
                    course_id=item.course_id,
                    name=item.name,
                    url=item.url,
                    content_fingerprint=item.content_fingerprint,
                    kind=item.kind,
                    course_name=course_names.get(item.course_id),
                )
                for item in instructions
            ],
            announcements=[
                AnnouncementItemOutput(
                    discussion_id=item.discussion_id,
                    course_id=item.course_id,
                    name=item.name,
                    content_fingerprint=item.content_fingerprint,
                    url=item.url,
                    author=item.author,
                    posted_at=int(item.posted_at.timestamp()) if item.posted_at else None,
                    course_name=course_names.get(item.course_id),
                )
                for item in announcements
            ],
            messages=[
                MessageItemOutput(
                    message_id=item.message_id,
                    sender_name=item.sender_name,
                    preview=item.preview,
                    sent_at=int(item.sent_at.timestamp()) if item.sent_at else None,
                    conversation_id=item.conversation_id,
                    sender_id=item.sender_id,
                    url=item.url,
                )
                for item in messages
            ],
            deliverable_refs=deliverable_refs,
            absorbed_instructions=absorbed_instructions,
        )