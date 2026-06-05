from dataclasses import dataclass
from typing import Optional


@dataclass
class Course:
    id: Optional[int]
    moodle_course_id: int
    fullname: str
    shortname: str
    visible: bool = True