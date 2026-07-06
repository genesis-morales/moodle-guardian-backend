from datetime import UTC, datetime

from src.domain.entities.announcement import Announcement
from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.course import Course
from src.domain.entities.instruction import Instruction
from src.domain.entities.message import Message
from src.domain.ports.moodle_gateway import MoodleGateway
from src.infrastructure.external.moodle.http_client import MoodleHttpClient


class MoodleClient(MoodleGateway):
    def __init__(self, http_client: MoodleHttpClient) -> None:
        self.http_client = http_client

    async def validate_token(self, token: str) -> bool:
        data = await self.http_client.call(
            token=token,
            wsfunction="core_webservice_get_site_info",
            params={},
        )
        return "userid" in data

    async def get_courses(self, token: str, moodle_user_id: int) -> list[Course]:
        data = await self.http_client.call(
            token=token,
            wsfunction="core_enrol_get_users_courses",
            params={"userid": moodle_user_id},
        )

        return [
            Course(
                id=None,
                moodle_course_id=item["id"],
                fullname=item.get("fullname", ""),
                shortname=item.get("shortname", ""),
                visible=bool(item.get("visible", 1)),
                start_date=datetime.fromtimestamp(item["startdate"], UTC)
                if item.get("startdate") else None,
                end_date=datetime.fromtimestamp(item["enddate"], UTC)
                if item.get("enddate") else None,
            )
            for item in data
        ]

    async def get_assignments(
        self,
        token: str,
        course_ids: list[int],
    ) -> list[Assignment]:
        if not course_ids:
            return []

        params = {f"courseids[{i}]": course_id for i, course_id in enumerate(course_ids)}

        data = await self.http_client.call(
            token=token,
            wsfunction="mod_assign_get_assignments",
            params=params,
        )

        assignments: list[Assignment] = []
        for course in data.get("courses", []):
            course_id = course["id"]
            for item in course.get("assignments", []):
                assignments.append(
                    Assignment(
                        id=None,
                        moodle_assignment_id=item["id"],
                        moodle_course_id=course_id,
                        name=item.get("name", ""),
                        due_date=datetime.fromtimestamp(item["duedate"], UTC)
                        if item.get("duedate") else None,
                        allow_submissions_from=datetime.fromtimestamp(
                            item["allowsubmissionsfromdate"], UTC
                        )
                        if item.get("allowsubmissionsfromdate") else None,
                        cutoff_date=datetime.fromtimestamp(item["cutoffdate"], UTC)
                        if item.get("cutoffdate") else None,
                    )
                )

        return assignments

    async def get_calendar_events(
        self,
        token: str,
        course_ids: list[int],
        timestart: int,
        timeend: int,
    ) -> list[CalendarEvent]:
        params = {
            "options[timestart]": timestart,
            "options[timeend]": timeend,
            "options[userevents]": 1,
            "options[siteevents]": 1,
            "options[ignorehidden]": 1,
        }

        for i, course_id in enumerate(course_ids):
            params[f"events[courseids][{i}]"] = course_id

        data = await self.http_client.call(
            token=token,
            wsfunction="core_calendar_get_calendar_events",
            params=params,
        )

        return [
            CalendarEvent(
                id=None,
                moodle_event_id=item["id"],
                course_id=item.get("courseid"),
                name=item.get("name", ""),
                event_type=item.get("eventtype"),
                due_date=datetime.fromtimestamp(item["timestart"], UTC)
                if item.get("timestart") else None,
                url=item.get("viewurl"),
                module=item.get("modulename"),
            )
            for item in data.get("events", [])
        ]

    async def get_forums(
        self,
        token: str,
        course_ids: list[int],
    ) -> list[CalendarEvent]:
        if not course_ids:
            return []

        params = {f"courseids[{i}]": course_id for i, course_id in enumerate(course_ids)}

        data = await self.http_client.call(
            token=token,
            wsfunction="mod_forum_get_forums_by_courses",
            params=params,
        )

        forums: list[CalendarEvent] = []
        for item in data:
            # El plazo efectivo del foro es el más tardío entre duedate y
            # cutoffdate (se puede entregar tarde hasta el cutoff).
            duedate = item.get("duedate") or 0
            cutoffdate = item.get("cutoffdate") or 0
            deadline_ts = max(duedate, cutoffdate)
            # Devolvemos TODOS los foros, incluso sin fecha (due_date=None). Los
            # que tienen fecha alimentan los recordatorios; los que no, sirven
            # igual para absorber su PDF de instrucciones (la presencia del foro
            # basta). El consumidor de eventos filtra los `due_date is None`.
            due_date = (
                datetime.fromtimestamp(deadline_ts, UTC) if deadline_ts > 0 else None
            )

            forums.append(
                CalendarEvent(
                    id=None,
                    moodle_event_id=None,
                    course_id=item.get("course"),
                    name=item.get("name", ""),
                    event_type="due",
                    due_date=due_date,
                    url=None,
                    module="forum",
                )
            )

        return forums

    async def get_course_resources(
        self,
        token: str,
        course_ids: list[int],
    ) -> list[Instruction]:
        instructions: list[Instruction] = []

        for course_id in course_ids:
            sections = await self.http_client.call(
                token=token,
                wsfunction="core_course_get_contents",
                params={"courseid": course_id},
            )

            for section in sections:
                for module in section.get("modules", []):
                    modname = module.get("modname")
                    if modname not in ("resource", "folder"):
                        continue

                    cmid = module.get("id")
                    contents = module.get("contents", [])
                    # Solo archivos PDF.
                    pdf_files = [
                        f for f in contents
                        if f.get("type") == "file"
                        and (f.get("mimetype") == "application/pdf"
                             or str(f.get("filename", "")).lower().endswith(".pdf"))
                    ]

                    for file in pdf_files:
                        # `resource` = un archivo: usamos el nombre del módulo
                        # (más legible). `folder` = varios: usamos el filename
                        # de cada archivo para distinguirlos.
                        if modname == "resource" and len(pdf_files) == 1:
                            name = module.get("name") or file.get("filename", "")
                        else:
                            name = file.get("filename", "")

                        instructions.append(
                            Instruction(
                                id=None,
                                moodle_id=cmid,
                                course_id=course_id,
                                name=name,
                                url=file.get("fileurl"),
                                content_fingerprint=str(file.get("timemodified") or ""),
                                kind=modname,
                            )
                        )

        return instructions

    async def get_announcements(
        self,
        token: str,
        course_ids: list[int],
    ) -> list[Announcement]:
        if not course_ids:
            return []

        # 1) Ubicar el foro de Novedades (type="news") de cada curso.
        params = {f"courseids[{i}]": course_id for i, course_id in enumerate(course_ids)}
        forums = await self.http_client.call(
            token=token,
            wsfunction="mod_forum_get_forums_by_courses",
            params=params,
        )
        news_forums = [f for f in forums if f.get("type") == "news"]

        # 2) Traer las discusiones (cada una = un anuncio) de cada foro news.
        announcements: list[Announcement] = []
        for forum in news_forums:
            forum_id = forum.get("id")
            course_id = forum.get("course")
            if forum_id is None:
                continue

            data = await self.http_client.call(
                token=token,
                wsfunction="mod_forum_get_forum_discussions",
                params={"forumid": forum_id},
            )

            for disc in data.get("discussions", []):
                discussion_id = disc.get("discussion") or disc.get("id")
                if discussion_id is None:
                    continue
                # timemodified detecta ediciones; usermodified/timemodified varían
                # según la versión de Moodle, así que caemos a modified/created.
                fingerprint = (
                    disc.get("timemodified")
                    or disc.get("modified")
                    or disc.get("created")
                )
                created = disc.get("created") or disc.get("timemodified")
                announcements.append(
                    Announcement(
                        id=None,
                        discussion_id=discussion_id,
                        course_id=course_id,
                        name=disc.get("subject") or disc.get("name", ""),
                        content_fingerprint=str(fingerprint) if fingerprint else None,
                        url=None,
                        author=disc.get("userfullname"),
                        posted_at=datetime.fromtimestamp(created, UTC)
                        if created else None,
                    )
                )

        return announcements

    async def get_messages(
        self,
        token: str,
        moodle_user_id: int,
    ) -> list[Message]:
        data = await self.http_client.call(
            token=token,
            wsfunction="core_message_get_conversations",
            params={
                "userid": moodle_user_id,
                # type=1: conversaciones individuales (1:1). Los grupos (type=2) y
                # autoconversación quedan fuera del MVP de mensajes.
                "type": 1,
            },
        )

        messages: list[Message] = []
        for conv in data.get("conversations", []):
            conversation_id = conv.get("id")

            # El remitente es el "otro" miembro de la conversación 1:1.
            members = conv.get("members", [])
            other = next(
                (m for m in members if m.get("id") != moodle_user_id),
                members[0] if members else None,
            )
            sender_name = (other or {}).get("fullname", "Alguien")
            sender_id = (other or {}).get("id")

            for msg in conv.get("messages", []):
                # Saltamos los mensajes enviados por el propio usuario: no son aviso.
                if msg.get("useridfrom") == moodle_user_id:
                    continue
                message_id = msg.get("id")
                if message_id is None:
                    continue
                sent_ts = msg.get("timecreated")
                messages.append(
                    Message(
                        id=None,
                        message_id=message_id,
                        sender_name=sender_name,
                        preview=msg.get("text"),
                        sent_at=datetime.fromtimestamp(sent_ts, UTC)
                        if sent_ts else None,
                        conversation_id=conversation_id,
                        sender_id=sender_id,
                    )
                )

        return messages