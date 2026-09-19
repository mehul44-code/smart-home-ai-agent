"""Simulator-backed REST API and persistence endpoints."""
from __future__ import annotations

import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.websocket import manager
from backend.app.database.database import get_db
from backend.app.database.history import persist_appliance_event, persist_home_state
from backend.app.database.models import (
    AgentDecision, AgentDecisionLog, AnomalyRecord, EnergyConsumption,
    SensorReadingRecord, TariffHistory, UserPreference,
)
from backend.app.simulator.home_simulator import simulator_instance
from backend.app.simulator.scenarios import ScenarioRegistry

router = APIRouter(tags=["Smart Home"])


class StepRequest(BaseModel):
    dt_minutes: float = Field(1.0, ge=0.0, le=1440.0)


class ScenarioRequest(BaseModel):
    scenario_id: str = Field(..., min_length=1, max_length=96)


class ApplianceActionRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=32)
    status: str | None = Field(None, max_length=32)
    power_watts: float | None = Field(None, ge=0.0, le=20000.0)
    setpoint_c: float | None = Field(None, ge=10.0, le=35.0)
    mode: str | None = Field(None, max_length=32)
    source: Literal["USER", "SYSTEM", "SIMULATOR", "AGENT"] = "USER"
    reason: str | None = Field(None, max_length=500)
    is_user_override: bool = False


class PreferenceRequest(BaseModel):
    preferred_temperature: float = Field(22.0, ge=16.0, le=32.0)
    comfort_priority: float = Field(0.5, ge=0.0, le=1.0)
    energy_priority: float = Field(0.5, ge=0.0, le=1.0)
    selected_mode: Literal["BALANCED", "COMFORT", "ENERGY_SAVING"] = "BALANCED"
    manual_override: bool = False
    override_expiry: datetime.datetime | None = None


class AnomalyRequest(BaseModel):
    appliance_id: str | None = Field(None, max_length=64)
    expected_power_watts: float = Field(..., ge=0.0)
    actual_power_watts: float = Field(..., ge=0.0)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    status: Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"] = "OPEN"
    details: dict[str, Any] | None = None


class AgentDecisionRequest(BaseModel):
    decision: str = Field(..., min_length=1, max_length=2000)
    reason: str | None = Field(None, max_length=4000)
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    selected_action: dict[str, Any] | None = None
    expected_energy: float | None = Field(None, ge=0.0)
    expected_comfort: float | None = Field(None, ge=0.0, le=100.0)
    expected_cost: float | None = Field(None, ge=0.0)
    sensor_snapshot: dict[str, Any] | None = None
    predictions: dict[str, Any] | None = None
    candidate_actions: list[dict[str, Any]] | None = None
    candidate_scores: dict[str, float] | None = None


def _json_state() -> dict[str, Any]:
    return simulator_instance.get_current_home_state().model_dump(mode="json")


def _record_to_dict(record: Any) -> dict[str, Any]:
    result = {column.name: getattr(record, column.name) for column in record.__table__.columns}
    for key, value in result.items():
        if isinstance(value, (datetime.datetime, datetime.date)):
            result[key] = value.isoformat()
    return result


async def _broadcast_state() -> None:
    await manager.broadcast({"event": "state_update", "state": _json_state()})


@router.get("/status")
async def get_system_status():
    state = _json_state()
    living_room = state["rooms"]["living_room"]
    return {"status": "online", "system_name": "Smart Home Simulator API", "simulation_time": state["timestamp"],
            "indoor_temp_c": living_room["temperature_c"], "outdoor_temp_c": state["weather"]["outdoor_temperature_c"],
            "occupancy": state["occupancy"]["is_occupied"], "tariff": state["tariff"],
            "total_power_kw": round(state["total_load_watts"] / 1000.0, 3)}


@router.get("/simulation/state")
async def get_simulation_state():
    return _json_state()


@router.get("/sensors")
async def get_sensors(limit: int = Query(0, ge=0, le=500), db: AsyncSession = Depends(get_db)):
    if limit == 0:
        return {"source": "simulator", "sensors": _json_state()["sensors"]}
    rows = (await db.execute(select(SensorReadingRecord).order_by(desc(SensorReadingRecord.id)).limit(limit))).scalars().all()
    return {"source": "database", "count": len(rows), "readings": [_record_to_dict(row) for row in rows]}


@router.get("/appliances")
async def get_appliances():
    state = _json_state()
    return {"count": len(state["appliances"]), "appliances": state["appliances"]}


@router.get("/energy")
async def get_energy(limit: int = Query(0, ge=0, le=500), db: AsyncSession = Depends(get_db)):
    state = _json_state()
    current = {"timestamp": state["timestamp"], "total_load_watts": state["total_load_watts"],
               "total_energy_kwh": state["total_energy_kwh"], "room_power_watts": state["room_power_watts"],
               "room_energy_kwh": state["room_energy_kwh"], "estimated_cost": state["estimated_cost_accumulated"]}
    if limit == 0:
        return {"current": current}
    rows = (await db.execute(select(EnergyConsumption).order_by(desc(EnergyConsumption.id)).limit(limit))).scalars().all()
    return {"current": current, "history": [_record_to_dict(row) for row in rows]}


@router.get("/tariff")
async def get_tariff(limit: int = Query(0, ge=0, le=500), db: AsyncSession = Depends(get_db)):
    tariff = _json_state()["tariff"]
    if limit == 0:
        return tariff
    rows = (await db.execute(select(TariffHistory).order_by(desc(TariffHistory.id)).limit(limit))).scalars().all()
    return {"current": tariff, "history": [_record_to_dict(row) for row in rows]}


@router.get("/agent/status")
async def get_agent_status():
    return {"status": "not_enabled", "message": "Autonomous decision-making is not enabled in this project stage."}


@router.get("/agent/history")
async def get_agent_history(limit: int = Query(50, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AgentDecision).order_by(desc(AgentDecision.id)).limit(limit))).scalars().all()
    return {"count": len(rows), "history": [_record_to_dict(row) for row in rows]}


@router.get("/anomalies")
async def get_anomalies(limit: int = Query(50, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AnomalyRecord).order_by(desc(AnomalyRecord.id)).limit(limit))).scalars().all()
    return {"count": len(rows), "anomalies": [_record_to_dict(row) for row in rows]}


@router.get("/preferences")
async def get_preferences(db: AsyncSession = Depends(get_db)):
    preference = await db.get(UserPreference, 1)
    if preference is None:
        preference = UserPreference(id=1)
        db.add(preference)
        await db.commit()
        await db.refresh(preference)
    return _record_to_dict(preference)


@router.post("/simulation/start")
async def start_simulation(db: AsyncSession = Depends(get_db)):
    try:
        simulator_instance.engine.start()
        state = simulator_instance.get_current_home_state()
        await persist_home_state(db, state)
        await _broadcast_state()
        return {"success": True, "state": state.model_dump(mode="json")}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@router.post("/simulation/pause")
async def pause_simulation(db: AsyncSession = Depends(get_db)):
    try:
        simulator_instance.engine.pause()
        state = simulator_instance.get_current_home_state()
        await persist_home_state(db, state)
        await _broadcast_state()
        return {"success": True, "state": state.model_dump(mode="json")}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@router.post("/simulation/reset")
async def reset_simulation(db: AsyncSession = Depends(get_db)):
    try:
        simulator_instance.engine.reset()
        state = simulator_instance.get_current_home_state()
        await persist_home_state(db, state)
        await _broadcast_state()
        return {"success": True, "state": state.model_dump(mode="json")}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@router.post("/simulation/step")
async def step_simulation(request: StepRequest, db: AsyncSession = Depends(get_db)):
    try:
        state = simulator_instance.engine.step(request.dt_minutes)
        await persist_home_state(db, state)
    except (ValueError, SQLAlchemyError) as exc:
        raise HTTPException(status_code=400, detail="Unable to advance simulation") from exc
    await _broadcast_state()
    return state.model_dump(mode="json")


@router.post("/simulation/scenario")
async def load_scenario(request: ScenarioRequest, db: AsyncSession = Depends(get_db)):
    result = ScenarioRegistry.apply_scenario(request.scenario_id, simulator_instance.engine)
    if not result["success"]:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    await persist_home_state(db, simulator_instance.get_current_home_state())
    await _broadcast_state()
    return result


@router.post("/appliances/{appliance_id}/action")
async def appliance_action(appliance_id: str, request: ApplianceActionRequest, db: AsyncSession = Depends(get_db)):
    before = simulator_instance.get_current_home_state()
    appliance = before.appliances.get(appliance_id)
    if appliance is None:
        await persist_appliance_event(db, appliance_id=appliance_id, room=None, event_type="INVALID_ACTION",
            previous_state=None, new_state=None, source=request.source, reason="Unknown appliance", success=False)
        raise HTTPException(status_code=404, detail="Unknown appliance")
    previous = appliance.model_dump(mode="json")
    result = simulator_instance.engine.execute_appliance_action(
        appliance_id, request.action, status=request.status, power_watts=request.power_watts,
        setpoint_c=request.setpoint_c, mode=request.mode,
        is_user_override=request.is_user_override or request.source == "USER")
    current = simulator_instance.get_current_home_state()
    new_state = current.appliances[appliance_id].model_dump(mode="json")
    event_type = "USER_OVERRIDE" if request.is_user_override or request.source == "USER" else request.action.upper()
    await persist_appliance_event(db, appliance_id=appliance_id, room=appliance.room, event_type=event_type,
        previous_state=previous, new_state=new_state if result["success"] else None,
        source=request.source, reason=request.reason or result.get("error"), success=result["success"])
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    await persist_home_state(db, current)
    await _broadcast_state()
    return {"success": True, "result": result, "state": current.model_dump(mode="json")}


@router.post("/override")
async def apply_override(request: ApplianceActionRequest, appliance_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    request.is_user_override = True
    request.source = "USER"
    return await appliance_action(appliance_id, request, db)


@router.post("/preferences")
async def save_preferences(request: PreferenceRequest, db: AsyncSession = Depends(get_db)):
    if request.override_expiry and request.override_expiry <= datetime.datetime.now(request.override_expiry.tzinfo):
        raise HTTPException(status_code=422, detail="override_expiry must be in the future")
    preference = await db.get(UserPreference, 1)
    if preference is None:
        preference = UserPreference(id=1)
        db.add(preference)
    for field, value in request.model_dump().items():
        setattr(preference, field, value)
    await db.commit()
    await db.refresh(preference)
    return _record_to_dict(preference)


@router.post("/anomalies")
async def create_anomaly(request: AnomalyRequest, db: AsyncSession = Depends(get_db)):
    if request.appliance_id and request.appliance_id not in simulator_instance.engine.appliances.appliances:
        raise HTTPException(status_code=404, detail="Unknown appliance")
    record = AnomalyRecord(appliance=request.appliance_id, expected_power=request.expected_power_watts,
        actual_power=request.actual_power_watts, deviation=request.actual_power_watts - request.expected_power_watts,
        severity=request.severity, status=request.status, details=request.details)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _record_to_dict(record)


@router.post("/agent/decisions")
async def create_agent_decision(request: AgentDecisionRequest, db: AsyncSession = Depends(get_db)):
    """Store supplied decision history; this route does not create decisions."""
    record = AgentDecision(**request.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _record_to_dict(record)


# Compatibility endpoint retained for existing tests/clients; this task does not
# add or alter autonomous decision behaviour.
@router.post("/agent/step")
async def legacy_agent_step(db: AsyncSession = Depends(get_db)):
    from backend.app.agent.core import agent_instance
    result = agent_instance.step()
    db.add(AgentDecisionLog(stage_data=result, selected_action=result["stage_4_decision"]["chosen_strategy"],
        estimated_cost_saving=result["stage_4_decision"].get("projected_hourly_cost_usd", 0.0),
        comfort_score=result["stage_6_feedback"].get("comfort_satisfaction_pct", 100.0) / 100.0,
        explanation=result["stage_7_explanation"]))
    await db.commit()
    return result
