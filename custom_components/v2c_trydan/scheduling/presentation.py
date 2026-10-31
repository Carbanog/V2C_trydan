"""Localized backend summaries using HA's normal translation resources."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from ..const import DOMAIN
from .policy import DAYS, PERIODS, WeeklySchedule


def _label(texts: dict[str, str], selector: str, value: str) -> str:
    return texts.get(f"component.{DOMAIN}.selector.{selector}.options.{value}", value)


def _block_label(block: dict[str, Any], texts: dict[str, str]) -> str:
    return (
        f"{', '.join(_label(texts, 'weekdays', day) for day in block['days'])}: "
        f"{block['start'][:5]} → {block['end'][:5]} — "
        f"{_label(texts, 'tariff', block['period'])}"
    )


async def async_block_choices(
    hass: HomeAssistant,
    blocks: list[dict[str, Any]],
    language: str,
) -> list[dict[str, str]]:
    """Use the same translated day/tariff names for editing and removal."""
    texts = await async_get_translations(hass, language, "selector", {DOMAIN})
    return [
        {"value": str(index), "label": _block_label(block, texts)}
        for index, block in enumerate(blocks)
    ]


async def async_schedule_summary(
    hass: HomeAssistant,
    draft: dict[str, Any],
    schedule: WeeklySchedule,
    language: str,
) -> dict[str, str]:
    """Describe a validated draft, never mutate or activate its configuration."""
    texts = await async_get_translations(hass, language, "selector", {DOMAIN})

    def label(selector: str, value: str) -> str:
        return _label(texts, selector, value)

    lines = [f"- {_block_label(block, texts)}" for block in draft["blocks"]]
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
