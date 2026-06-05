from typing import Protocol, List


class SubscriptionRepository(Protocol):
    async def save_user_courses(self, user_id: int, course_ids: List[int]) -> None:
        ...

    async def get_course_ids_by_user(self, user_id: int) -> List[int]:
        ...

    async def replace_user_courses(self, user_id: int, course_ids: List[int]) -> None:
        ...