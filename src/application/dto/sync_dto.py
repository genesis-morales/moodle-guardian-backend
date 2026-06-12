from pydantic import BaseModel


class ManualSyncInput(BaseModel):
    moodle_user_id: int


class AssignmentItemOutput(BaseModel):
    moodle_assignment_id: int | None
    moodle_course_id: int
    name: str
    due_date: int | None
    allow_submissions_from: int | None
    cutoff_date: int | None
    course_name: str | None = None


class CalendarEventItemOutput(BaseModel):
    moodle_event_id: int | None
    course_id: int | None
    name: str
    event_type: str | None
    due_date: int | None
    url: str | None
    course_name: str | None = None


class ManualSyncOutput(BaseModel):
    moodle_user_id: int
    courses_count: int
    assignments_count: int
    events_count: int
    assignments: list[AssignmentItemOutput]
    events: list[CalendarEventItemOutput]