import httpx

from src.config.settings import get_settings
from src.domain.entities.course import Course
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.assignment import Assignment
from src.domain.ports.moodle_gateway import MoodleGateway


class MoodleClient(MoodleGateway):
    def __init__(self) -> None:
        self.settings = get_settings()

    async def validate_token(self, token: str) -> bool:
        params = self._base_params(
            token=token,
            function_name=self.settings.moodle_site_info_function,
        )

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.get(self.settings.moodle_base_url, params=params)
            response.raise_for_status()
            data = response.json()

        return "exception" not in data and "userid" in data

    async def get_courses(self, token: str, moodle_user_id: int) -> list[Course]:
        params = self._base_params(
            token=token,
            function_name=self.settings.moodle_courses_function,
        )
        params["userid"] = moodle_user_id

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.get(self.settings.moodle_base_url, params=params)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, dict) and data.get("exception"):
            return []

        courses: list[Course] = []
        for item in data:
            courses.append(
                Course(
                    id=None,
                    moodle_course_id=item["id"],
                    fullname=item.get("fullname", ""),
                    shortname=item.get("shortname", ""),
                    visible=bool(item.get("visible", 1)),
                )
            )

        return courses

    async def get_assignments(
        self,
        token: str,
        moodle_user_id: int,
        course_ids: list[int],
    ) -> list[Assignment]:
        params = self._base_params(
            token=token,
            function_name=self.settings.moodle_assignments_function,
        )

        for index, course_id in enumerate(course_ids):
            params[f"courseids[{index}]"] = course_id

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.get(self.settings.moodle_base_url, params=params)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, dict) and data.get("exception"):
            return []

        assignments: list[Assignment] = []
        courses_data = data.get("courses", [])

        for course in courses_data:
            moodle_course_id = course.get("id")
            for assignment in course.get("assignments", []):
                assignments.append(
                    Assignment(
                        id=None,
                        moodle_assignment_id=assignment.get("id"),
                        moodle_course_id=moodle_course_id,
                        name=assignment.get("name", ""),
                        due_date=self._to_datetime(assignment.get("duedate")),
                        allow_submissions_from=self._to_datetime(
                            assignment.get("allowsubmissionsfromdate")),
                        cutoff_date=self._to_datetime(assignment.get("cutoffdate")),
                        url=None,
                        is_visible=not bool(assignment.get("hidden", 0)),
                    )
                )

        return assignments

    async def get_calendar_events(
        self,
        token: str,
        moodle_user_id: int,
    ) -> list[CalendarEvent]:
        params = self._base_params(
            token=token,
            function_name=self.settings.moodle_calendar_events_function,
        )

        params["events[courseids][0]"] = "all"
        params["options[timefrom]"] = 0

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.get(self.settings.moodle_base_url, params=params)
            response.raise_for_status()
            data = response.json()

        if isinstance(data, dict) and data.get("exception"):
            return []

        events: list[CalendarEvent] = []
        for event in data.get("events", []):
            events.append(
                CalendarEvent(
                    id=None,
                    moodle_event_id=event.get("id"),
                    course_id=event.get("courseid"),
                    name=event.get("name", ""),
                    event_type=event.get("eventtype"),
                    due_date=self._to_datetime(event.get("timestart")),
                    url=event.get("viewurl"),
                )
            )

        return events

    def _base_params(self, token: str, function_name: str) -> dict[str, str | int]:
        return {
            "wstoken": token,
            "wsfunction": function_name,
            "moodlewsrestformat": "json",
        }

    def _to_datetime(self, value: int | None):
        if not value:
            return None

        from datetime import datetime, UTC
        return datetime.fromtimestamp(value, tz=UTC)