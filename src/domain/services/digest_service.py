from datetime import date, datetime, timedelta, tzinfo

from src.application.dto.digest_dto import DeliverableItem
from src.domain.entities.assignment import Assignment
from src.domain.entities.calendar_event import CalendarEvent


def collect_deliverables(
    assignments: list[Assignment],
    events: list[CalendarEvent],
) -> list[DeliverableItem]:
    """Unifica tareas y eventos en una lista de entregables con fecha, ordenada
    cronológicamente. Descarta los que no tienen fecha."""
    items: list[DeliverableItem] = []

    for a in assignments:
        # Plazo efectivo = el más tardío entre due y cutoff (igual que is_past).
        deadline = max(
            (d for d in (a.due_date, a.cutoff_date) if d is not None),
            default=None,
        )
        if deadline is None:
            continue
        items.append(
            DeliverableItem(
                name=a.name,
                course_name=a.course_name,
                deadline=deadline,
                module=None,
                kind="assignment",
                key=a.stable_key(),
            )
        )

    for e in events:
        if e.due_date is None:
            continue
        items.append(
            DeliverableItem(
                name=e.name,
                course_name=e.course_name,
                deadline=e.due_date,
                module=e.module,
                kind="event",
                key=e.stable_key(),
            )
        )

    items.sort(key=lambda i: i.deadline)
    return items


def filter_future(items: list[DeliverableItem], now: datetime) -> list[DeliverableItem]:
    return [i for i in items if i.deadline >= now]


def filter_due_on_local_date(
    items: list[DeliverableItem],
    target_local_date: date,
    tz: tzinfo,
) -> list[DeliverableItem]:
    """Entregables cuyo deadline cae en una fecha calendario local concreta.

    La conversión a `tz` es crítica: un deadline a las 05:59 UTC equivale a las
    23:59 hora local del día anterior, así que comparar en UTC daría el día
    equivocado.
    """
    return [
        i for i in items
        if i.deadline.astimezone(tz).date() == target_local_date
    ]


def filter_due_within(
    items: list[DeliverableItem],
    now: datetime,
    days: int,
    tz: tzinfo,
) -> list[DeliverableItem]:
    """Entregables que vencen entre ahora y los próximos `days` días (inclusive
    del último día, en fecha local). Excluye lo ya vencido."""
    last_local_date = (now.astimezone(tz) + timedelta(days=days)).date()
    return [
        i for i in items
        if i.deadline >= now and i.deadline.astimezone(tz).date() <= last_local_date
    ]
