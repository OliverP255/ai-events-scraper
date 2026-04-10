from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def raw_from_parsed(
    source: str,
    d: dict[str, Any],
    *,
    extra: dict[str, Any] | None = None,
) -> "RawEvent":
    return RawEvent(
        source=source,
        url=d["url"],
        title=d.get("title") or "",
        description=d.get("description"),
        starts_at=d.get("starts_at"),
        ends_at=d.get("ends_at"),
        venue=d.get("venue"),
        city=d.get("city"),
        country=d.get("country"),
        is_in_person=d.get("is_in_person"),
        attendance_mode_uri=d.get("attendance_mode_uri"),
        extra=extra or {},
    )


@dataclass
class RawEvent:
    """Normalized event row before persistence."""

    source: str
    url: str
    title: str
    description: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    venue: str | None
    city: str | None
    country: str | None
    is_in_person: bool | None
    attendance_mode_uri: str | None
    extra: dict[str, Any] = field(default_factory=dict)
