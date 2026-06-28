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
    module: str | None = None
    course_name: str | None = None


class InstructionItemOutput(BaseModel):
    moodle_id: int
    course_id: int
    name: str
    url: str | None = None
    content_fingerprint: str | None = None
    kind: str = "resource"
    course_name: str | None = None


class DeliverableRefItem(BaseModel):
    """Entregable (tarea/foro) del curso SIN filtrar por fecha, usado solo para
    absorber instrucciones de entregables ya vencidos o fuera de ventana."""

    course_id: int
    name: str


class AbsorbedInstructionItem(BaseModel):
    """Debug: instrucción descartada porque su espacio de entrega ya existe.
    `absorbed_by` es el nombre del entregable que la absorbió."""

    course_id: int
    name: str
    absorbed_by: str


class ManualSyncOutput(BaseModel):
    moodle_user_id: int
    courses_count: int
    assignments_count: int
    events_count: int
    instructions_count: int = 0
    assignments: list[AssignmentItemOutput]
    events: list[CalendarEventItemOutput]
    instructions: list[InstructionItemOutput] = []
    deliverable_refs: list[DeliverableRefItem] = []
    absorbed_instructions: list[AbsorbedInstructionItem] = []