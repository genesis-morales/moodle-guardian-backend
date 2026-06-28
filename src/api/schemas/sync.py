from pydantic import BaseModel


class ManualSyncRequest(BaseModel):
    moodle_user_id: int


class AssignmentItemResponse(BaseModel):
    moodle_assignment_id: int | None
    moodle_course_id: int
    name: str
    due_date: int | None
    allow_submissions_from: int | None
    cutoff_date: int | None


class CalendarEventItemResponse(BaseModel):
    moodle_event_id: int | None
    course_id: int | None
    name: str
    event_type: str | None
    due_date: int | None
    url: str | None


class InstructionItemResponse(BaseModel):
    moodle_id: int
    course_id: int
    name: str
    url: str | None = None
    content_fingerprint: str | None = None
    kind: str = "resource"
    course_name: str | None = None


class DeliverableRefResponse(BaseModel):
    course_id: int
    name: str


class AbsorbedInstructionResponse(BaseModel):
    course_id: int
    name: str
    absorbed_by: str


class ManualSyncResponse(BaseModel):
    moodle_user_id: int
    courses_count: int
    assignments_count: int
    events_count: int
    instructions_count: int = 0
    assignments: list[AssignmentItemResponse]
    events: list[CalendarEventItemResponse]
    instructions: list[InstructionItemResponse] = []
    deliverable_refs: list[DeliverableRefResponse] = []
    absorbed_instructions: list[AbsorbedInstructionResponse] = []