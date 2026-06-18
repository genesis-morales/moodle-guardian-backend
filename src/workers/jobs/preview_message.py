"""PRUEBA / DRY-RUN.

Consulta Moodle real para cada usuario activo y muestra en consola el mensaje
de Telegram **tal como se enviaría**, tratando todos los eventos/tareas como
nuevos. NO guarda snapshot ni envía nada por Telegram.

Sirve para validar formato: hora local, etiquetas [Foro]/[Entrega]/..., y el
cajón de "Avisos Generales".

Ejecutar:  python -m src.workers.jobs.preview_message
"""

import asyncio
from datetime import UTC, datetime, timedelta

from src.api.dependencies import (
    get_fetch_course_snapshot_use_case,
    get_telegram_message_builder,
    get_user_repository,
)
from src.application.dto.sync_dto import ManualSyncInput
from src.application.use_cases.run_guardian_scan import RunGuardianScanUseCase
from src.domain.entities.diff_result import DiffResult


async def main() -> None:
    user_repository = get_user_repository()
    fetch_uc = get_fetch_course_snapshot_use_case()
    builder = get_telegram_message_builder()

    # Reutilizamos el conversor DTO->entidades del caso de uso real.
    to_snapshot = RunGuardianScanUseCase._to_snapshot

    users = await user_repository.list_active()

    for user in users:
        sync = await fetch_uc.execute(ManualSyncInput(moodle_user_id=user.moodle_user_id))
        snapshot = to_snapshot(None, user.id or 0, sync)

        # Simulamos un diff donde TODO es nuevo, solo para previsualizar el render.
        diff = DiffResult(
            new_assignments=list(snapshot.assignments),
            new_events=list(snapshot.events),
        )

        print("\n" + "=" * 70)
        print(f"PREVIEW moodle_user_id={user.moodle_user_id} "
              f"(eventos={len(snapshot.events)} tareas={len(snapshot.assignments)})")
        print("=" * 70)
        print(builder.build_changes_message(diff))


if __name__ == "__main__":
    asyncio.run(main())
