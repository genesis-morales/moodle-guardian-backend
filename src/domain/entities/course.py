from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Course:
    id: Optional[int]
    moodle_course_id: int
    fullname: str
    shortname: str
    visible: bool = True
    start_date: datetime | None = None
    end_date: datetime | None = None

    def is_active(self, now: datetime) -> bool:
        """Un curso está vigente si aún no terminó.

        Moodle entrega `enddate=0` (-> None aquí) para cursos sin fecha de
        cierre, que tratamos como vigentes. Si hay fecha de cierre y ya pasó,
        el curso es de un cuatrimestre anterior y se descarta.
        """
        if self.end_date is None:
            return True
        return self.end_date >= now