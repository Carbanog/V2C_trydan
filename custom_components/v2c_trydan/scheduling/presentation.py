"""Localized backend summaries using HA's normal translation resources."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from ..const import DOMAIN
from .policy import DAYS, PERIODS, WeeklySchedule


async def async_schedule_summary(
    hass: HomeAssistant,
    draft: dict[str, Any],
    schedule: WeeklySchedule,
    language: str,
) -> dict[str, str]:
    """Describe a validated draft, never mutate or activate its configuration."""
    texts = await async_get_translations(hass, language, "selector", {DOMAIN})
    prefix = f"component.{DOMAIN}.selector."

    def label(selector: str, value: str) -> str:
        return texts.get(f"{prefix}{selector}.options.{value}", value)

    lines = [
        f"- {', '.join(label('weekdays', day) for day in block['days'])}: "
        f"{block['start'][:5]} → {block['end'][:5]} — "
        f"{label('tariff', block['period'])}"
        for block in draft["blocks"]
    ]
    gaps = schedule.coverage_gaps()
    gap_lines = []
    for day, name in enumerate(DAYS):
        for start, end in gaps:
            start, end = max(start, day * 1440), min(end, (day + 1) * 1440)
            if start < end:
                first, last = start - day * 1440, end - day * 1440
                gap_lines.append(
                    f"- {label('weekdays', name)}: "
                    f"{first // 60:02d}:{first % 60:02d} → "
                    f"{last // 60:02d}:{last % 60:02d}"
                )
    return {
        "enabled": label(
            "scheduling_enabled", "enabled" if schedule.enabled else "disabled"
        ),
        "blocks": "\n".join(lines) or "—",
        "allowed": ", ".join(
            label("tariff", period) for period in PERIODS if period in schedule.allowed
        )
        or "—",
        "unassigned_minutes": str(sum(end - start for start, end in gaps)),
        "gaps": "\n".join(gap_lines) or "—",
    }
