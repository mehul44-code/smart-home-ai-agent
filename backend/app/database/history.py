"""Persistence helpers for simulator snapshots and API audit events."""
from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models import (
    ApplianceEvent,
    ApplianceRecord,
    EnergyConsumption,
    SensorReadingRecord,
    TariffHistory,
)
from backend.app.simulator.simulation_engine import HomeState


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


async def persist_home_state(session: AsyncSession, state: HomeState) -> None:
    """Persist room snapshots and electrical/tariff history for an advanced step."""
    captured_at = _now()
    payload = state.model_dump(mode="json")
    for room_id, room in state.rooms.items():
        session.add(SensorReadingRecord(
            timestamp=captured_at,
            simulated_time=state.simulated_time,
            room=room_id,
            temperature_c=room.temperature_c,
            humidity_pct=room.humidity_pct,
            occupancy_count=room.occupancy_count,
            light_level_lux=room.light_level_lux,
            outdoor_temperature_c=state.weather.outdoor_temperature_c,
            weather=state.weather.condition.value,
            snapshot=payload,
        ))

    for appliance_id, appliance in state.appliances.items():
        current = await session.get(ApplianceRecord, appliance_id)
        values = {
            "name": appliance.name,
            "category": appliance.room.upper(),
            "status": appliance.status,
            "current_power_kw": appliance.power_watts / 1000.0,
            "rated_power_kw": appliance.nominal_power_watts / 1000.0,
            "priority": appliance.priority.value,
            "is_shiftable": appliance.priority.value != "CRITICAL",
            "setpoint_c": appliance.setpoint_c,
            "updated_at": captured_at,
        }
        if current is None:
            session.add(ApplianceRecord(id=appliance_id, **values))
        else:
            for key, value in values.items():
                setattr(current, key, value)
        session.add(EnergyConsumption(
            timestamp=captured_at,
            simulated_time=state.simulated_time,
            appliance_id=appliance_id,
            power_watts=appliance.power_watts,
            energy_kwh=appliance.total_energy_kwh,
            total_load_watts=state.total_load_watts,
            cumulative_energy_kwh=state.total_energy_kwh,
            tariff_tier=state.tariff.tier.value,
            tariff_rate=state.tariff.rate,
            estimated_cost=state.estimated_cost_accumulated,
        ))

    session.add(TariffHistory(
        timestamp=captured_at,
        simulated_time=state.simulated_time,
        tier=state.tariff.tier.value,
        rate=state.tariff.rate,
        currency=state.tariff.currency,
        next_tier=state.tariff.next_tier.value,
        next_rate=state.tariff.next_rate,
    ))
    await session.commit()


async def persist_appliance_event(
    session: AsyncSession,
    *,
    appliance_id: str | None,
    room: str | None,
    event_type: str,
    previous_state: dict[str, Any] | None,
    new_state: dict[str, Any] | None,
    source: str,
    reason: str | None,
    success: bool,
) -> None:
    session.add(ApplianceEvent(
        timestamp=_now(), appliance_id=appliance_id, room=room,
        event_type=event_type, previous_state=previous_state,
        new_state=new_state, source=source, reason=reason, success=success,
    ))
    await session.commit()
