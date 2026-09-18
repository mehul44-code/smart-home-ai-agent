from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from backend.app.database.database import get_db
from backend.app.database.models import TelemetryRecord, AgentDecisionLog
from backend.app.simulator.home_simulator import simulator_instance
from backend.app.agent.core import agent_instance

router = APIRouter(prefix="/api", tags=["Smart Home & Agent"])


class ApplianceOverrideRequest(BaseModel):
    status: str
    power_kw: float
    setpoint_c: Optional[float] = None


@router.get("/status")
async def get_system_status():
    """Returns current environment telemetry, simulator status, and agent health."""
    current_state = simulator_instance.step(dt_minutes=0.0)
    return {
        "status": "online",
        "system_name": "Smart Home Autonomous AI Agent",
        "simulation_time": current_state["timestamp"],
        "indoor_temp_c": current_state["indoor_temp_c"],
        "outdoor_temp_c": current_state["outdoor_temp_c"],
        "occupancy": current_state["occupancy"],
        "tariff": current_state["tariff"],
        "solar_generation_kw": current_state["solar_generation_kw"],
        "total_power_kw": current_state["total_power_kw"],
        "grid_power_kw": current_state["grid_power_kw"]
    }


@router.get("/appliances")
async def get_appliances():
    """Lists all monitored smart home appliances and their current operational state."""
    return {
        "count": len(simulator_instance.appliances),
        "appliances": simulator_instance.appliances
    }


@router.post("/appliances/{appliance_id}/override")
async def override_appliance(appliance_id: str, req: ApplianceOverrideRequest):
    """Allows manual user override of an appliance."""
    if appliance_id not in simulator_instance.appliances:
        raise HTTPException(status_code=404, detail=f"Appliance '{appliance_id}' not found")
    
    simulator_instance.set_appliance_state(
        appliance_id=appliance_id,
        status=req.status,
        power_kw=req.power_kw,
        setpoint_c=req.setpoint_c
    )
    return {
        "message": f"Appliance '{appliance_id}' override applied",
        "current_state": simulator_instance.appliances[appliance_id]
    }


@router.post("/agent/step")
async def execute_agent_step(db: AsyncSession = Depends(get_db)):
    """
    Triggers one complete pass of the 7-stage cognitive loop:
    PERCEPTION -> PREDICTION -> REASONING -> DECISION -> ACTION -> FEEDBACK -> EXPLANATION
    """
    result = agent_instance.step()

    # Persist decision log asynchronously
    try:
        log_entry = AgentDecisionLog(
            stage_data=result,
            selected_action=result["stage_4_decision"]["chosen_strategy"],
            estimated_cost_saving=result["stage_4_decision"].get("projected_hourly_cost_usd", 0.0),
            comfort_score=result["stage_6_feedback"].get("comfort_satisfaction_pct", 100.0) / 100.0,
            explanation=result["stage_7_explanation"]
        )
        db.add(log_entry)
        
        # Also persist telemetry record
        st = result["consequent_state"]
        telemetry = TelemetryRecord(
            indoor_temp_c=st["indoor_temp_c"],
            outdoor_temp_c=st["outdoor_temp_c"],
            humidity_pct=st["humidity_pct"],
            occupancy=st["occupancy"],
            tariff_rate=st["tariff"]["rate"],
            total_power_kw=st["total_power_kw"],
            solar_power_kw=st["solar_generation_kw"],
            grid_power_kw=st["grid_power_kw"]
        )
        db.add(telemetry)
        await db.commit()
    except Exception as e:
        await db.rollback()
        # Non-blocking for response if db logging fails
        print(f"Warning: Failed to persist step to DB: {e}")

    return result


@router.get("/history")
async def get_history(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Returns recent telemetry and agent decision logs for analytics and charts."""
    query = select(TelemetryRecord).order_by(desc(TelemetryRecord.id)).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()
    
    return {
        "count": len(records),
        "history": [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "indoor_temp_c": r.indoor_temp_c,
                "outdoor_temp_c": r.outdoor_temp_c,
                "humidity_pct": r.humidity_pct,
                "tariff_rate": r.tariff_rate,
                "total_power_kw": r.total_power_kw,
                "solar_power_kw": r.solar_power_kw,
                "grid_power_kw": r.grid_power_kw
            }
            for r in reversed(records)
        ]
    }
