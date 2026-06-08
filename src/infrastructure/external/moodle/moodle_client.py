from datetime import UTC, datetime

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.course import Course
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
            )
            for item in data.get("events", [])
        ]