from sqlalchemy import delete, select

from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.models import UserCourseModel


class PostgresSubscriptionRepository:
    async def save_user_courses(self, user_id: int, course_ids: list[int]) -> None:
        async with AsyncSessionLocal() as session:
            for course_id in course_ids:
                session.add(
                    UserCourseModel(
                        user_id=user_id,
                        moodle_course_id=course_id,
                    )
                )
            await session.commit()

    async def get_course_ids_by_user(self, user_id: int) -> list[int]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserCourseModel.moodle_course_id).where(
                    UserCourseModel.user_id == user_id
                )
            )
            return list(result.scalars().all())

    async def replace_user_courses(self, user_id: int, course_ids: list[int]) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(UserCourseModel).where(UserCourseModel.user_id == user_id)
            )

            for course_id in course_ids:
                session.add(
                    UserCourseModel(
                        user_id=user_id,
                        moodle_course_id=course_id,
                    )
                )

            await session.commit()