from sqlalchemy import select

from src.domain.entities.scan_run import ScanFailure, ScanRun
from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.models.scan_run_model import ScanRunModel


class PostgresScanRunRepository:
    async def save(self, run: ScanRun) -> ScanRun:
        async with AsyncSessionLocal() as session:
            model = ScanRunModel(
                job_name=run.job_name,
                started_at=run.started_at,
                finished_at=run.finished_at,
                total_users=run.total_users,
                success_count=run.success_count,
                failure_count=run.failure_count,
                failures=[
                    {"moodle_user_id": f.moodle_user_id, "error": f.error}
                    for f in run.failures
                ],
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def list_recent(self, limit: int = 20) -> list[ScanRun]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ScanRunModel)
                .order_by(ScanRunModel.finished_at.desc())
                .limit(limit)
            )
            return [self._to_entity(model) for model in result.scalars().all()]

    def _to_entity(self, model: ScanRunModel) -> ScanRun:
        return ScanRun(
            id=model.id,
            job_name=model.job_name,
            started_at=model.started_at,
            finished_at=model.finished_at,
            total_users=model.total_users,
            success_count=model.success_count,
            failure_count=model.failure_count,
            failures=[
                ScanFailure(
                    moodle_user_id=item.get("moodle_user_id"),
                    error=item.get("error", ""),
                )
                for item in (model.failures or [])
            ],
        )
