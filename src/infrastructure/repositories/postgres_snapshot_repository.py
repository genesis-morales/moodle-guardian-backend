from datetime import datetime
from typing import Optional

from sqlalchemy import select

from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent
from src.domain.entities.snapshot import Snapshot
from src.domain.ports.snapshot_repository import SnapshotRepository
from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.models.snapshot_model import SnapshotModel


class PostgresSnapshotRepository(SnapshotRepository):
    async def save(self, snapshot: Snapshot) -> Snapshot:
        if snapshot.user_id is None:
            raise ValueError("snapshot.user_id is required")

        async with AsyncSessionLocal() as session:
            model = SnapshotModel(
                user_id=snapshot.user_id,
                moodle_user_id=snapshot.moodle_user_id,
                captured_at=snapshot.captured_at,
                assignments=[self._assignment_to_dict(item) for item in snapshot.assignments],
                events=[self._event_to_dict(item) for item in snapshot.events],
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def get_latest_by_user_id(self, user_id: int) -> Optional[Snapshot]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SnapshotModel)
                .where(SnapshotModel.user_id == user_id)
                .order_by(SnapshotModel.captured_at.desc())
            )
            model = result.scalars().first()
            return self._to_entity(model) if model else None

    def _to_entity(self, model: SnapshotModel) -> Snapshot:
        return Snapshot(
            user_id=model.user_id,
            moodle_user_id=model.moodle_user_id,
            captured_at=model.captured_at,
            assignments=[self._dict_to_assignment(item) for item in (model.assignments or [])],
            events=[self._dict_to_event(item) for item in (model.events or [])],
        )

    def _assignment_to_dict(self, item: Assignment) -> dict:
        return {
            "moodle_assignment_id": item.moodle_assignment_id,
            "moodle_course_id": item.moodle_course_id,
            "name": item.name,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "allow_submissions_from": (
                item.allow_submissions_from.isoformat()
                if item.allow_submissions_from
                else None
            ),
            "cutoff_date": item.cutoff_date.isoformat() if item.cutoff_date else None,
            "course_name": item.course_name,
        }

    def _event_to_dict(self, item: CalendarEvent) -> dict:
        return {
            "moodle_event_id": item.moodle_event_id,
            "course_id": item.course_id,
            "name": item.name,
            "event_type": item.event_type,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "url": item.url,
            "module": item.module,
            "course_name": item.course_name,
        }

    def _dict_to_assignment(self, data: dict) -> Assignment:
        return Assignment(
            moodle_assignment_id=data["moodle_assignment_id"],
            moodle_course_id=data["moodle_course_id"],
            name=data["name"],
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            allow_submissions_from=(
                datetime.fromisoformat(data["allow_submissions_from"])
                if data.get("allow_submissions_from")
                else None
            ),
            cutoff_date=datetime.fromisoformat(data["cutoff_date"]) if data.get("cutoff_date") else None,
            course_name=data.get("course_name"),
        )

    def _dict_to_event(self, data: dict) -> CalendarEvent:
        return CalendarEvent(
            moodle_event_id=data["moodle_event_id"],
            course_id=data["course_id"],
            name=data["name"],
            event_type=data["event_type"],
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            url=data["url"],
            module=data.get("module"),
            course_name=data.get("course_name"),
        )