import logging
import math
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

logger = logging.getLogger("smart_home.appliances")


class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ComfortImpact(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ApplianceState(BaseModel):
    id: str
    name: str
    room: str
    status: str = Field("OFF", description="ON, OFF, ECO, IDLE")
    power_watts: float = Field(0.0, ge=0.0)
    nominal_power_watts: float = Field(..., ge=0.0)
    priority: PriorityLevel
    comfort_impact: ComfortImpact
    minimum_runtime_minutes: int = Field(0, ge=0)
    maximum_runtime_minutes: int = Field(720, ge=0)
    current_mode: str = Field("STANDARD")
    setpoint_c: Optional[float] = None
    
    # Runtime & Energy tracking
    current_cycle_runtime_minutes: float = Field(0.0, ge=0.0)
    total_runtime_minutes: float = Field(0.0, ge=0.0)
    total_energy_kwh: float = Field(0.0, ge=0.0)
    
    # User override preservation
    is_user_override: bool = Field(False)
    override_reason: Optional[str] = None


class ApplianceManager:
    """
    Manages the fleet of smart home appliances, their operational state machines,
    power consumption profiles, energy accumulation, and manual user overrides.
    """

    def __init__(self, custom_configs: Optional[Dict[str, Dict[str, Any]]] = None):
        self.appliances: Dict[str, ApplianceState] = {}
        self._initialize_default_appliances()
        if custom_configs:
            self._apply_custom_configs(custom_configs)

    def _initialize_default_appliances(self):
        defaults = [
            ApplianceState(
                id="ac_living_room",
                name="Air Conditioner",
                room="living_room",
                status="OFF",
                power_watts=0.0,
                nominal_power_watts=1500.0,
                priority=PriorityLevel.HIGH,
                comfort_impact=ComfortImpact.HIGH,
                minimum_runtime_minutes=10,
                maximum_runtime_minutes=360,
                current_mode="COOL",
                setpoint_c=22.0
            ),
            ApplianceState(
                id="fan_bedroom",
                name="Ceiling Fan",
                room="bedroom",
                status="OFF",
                power_watts=0.0,
                nominal_power_watts=75.0,
                priority=PriorityLevel.MEDIUM,
                comfort_impact=ComfortImpact.MEDIUM,
                minimum_runtime_minutes=5,
                maximum_runtime_minutes=480,
                current_mode="SPEED_2"
            ),
            ApplianceState(
                id="lights_living_room",
                name="Living Room Lights",
                room="living_room",
                status="OFF",
                power_watts=0.0,
                nominal_power_watts=15.0,
                priority=PriorityLevel.LOW,
                comfort_impact=ComfortImpact.LOW,
                minimum_runtime_minutes=1,
                maximum_runtime_minutes=720,
                current_mode="STANDARD"
            ),
            ApplianceState(
                id="lights_bedroom",
                name="Bedroom Lights",
                room="bedroom",
                status="OFF",
                power_watts=0.0,
                nominal_power_watts=15.0,
                priority=PriorityLevel.LOW,
                comfort_impact=ComfortImpact.LOW,
                minimum_runtime_minutes=1,
                maximum_runtime_minutes=720,
                current_mode="STANDARD"
            ),
            ApplianceState(
                id="lights_kitchen",
                name="Kitchen Lights",
                room="kitchen",
                status="OFF",
                power_watts=0.0,
                nominal_power_watts=20.0,
                priority=PriorityLevel.LOW,
                comfort_impact=ComfortImpact.LOW,
                minimum_runtime_minutes=1,
                maximum_runtime_minutes=720,
                current_mode="STANDARD"
            ),
            ApplianceState(
                id="tv_living_room",
                name="Smart TV",
                room="living_room",
                status="OFF",
                power_watts=0.0,
                nominal_power_watts=120.0,
                priority=PriorityLevel.LOW,
                comfort_impact=ComfortImpact.MEDIUM,
                minimum_runtime_minutes=15,
                maximum_runtime_minutes=300,
                current_mode="STANDARD"
            ),
            ApplianceState(
                id="washing_machine",
                name="Washing Machine",
                room="kitchen",
                status="OFF",
                power_watts=0.0,
                nominal_power_watts=800.0,
                priority=PriorityLevel.LOW,
                comfort_impact=ComfortImpact.LOW,
                minimum_runtime_minutes=30,
                maximum_runtime_minutes=90,
                current_mode="STANDARD"
            ),
            ApplianceState(
                id="water_heater",
                name="Water Heater",
                room="kitchen",
                status="OFF",
                power_watts=0.0,
                nominal_power_watts=2000.0,
                priority=PriorityLevel.MEDIUM,
                comfort_impact=ComfortImpact.MEDIUM,
                minimum_runtime_minutes=15,
                maximum_runtime_minutes=180,
                current_mode="STANDARD"
            ),
            ApplianceState(
                id="refrigerator",
                name="Refrigerator",
                room="kitchen",
                status="ON",
                power_watts=150.0,
                nominal_power_watts=150.0,
                priority=PriorityLevel.HIGH,
                comfort_impact=ComfortImpact.LOW,
                minimum_runtime_minutes=10,
                maximum_runtime_minutes=720,
                current_mode="ECO"
            ),
            ApplianceState(
                id="ev_charger",
                name="Level 2 EV Charger",
                room="garage",
                status="OFF",
                power_watts=0.0,
                nominal_power_watts=3300.0,
                priority=PriorityLevel.LOW,
                comfort_impact=ComfortImpact.LOW,
                minimum_runtime_minutes=30,
                maximum_runtime_minutes=480,
                current_mode="STANDARD"
            )
        ]
        self.appliances = {app.id: app for app in defaults}

    def _apply_custom_configs(self, configs: Dict[str, Dict[str, Any]]):
        for app_id, data in configs.items():
            if app_id in self.appliances:
                current = self.appliances[app_id].model_dump()
                current.update(data)
                self.appliances[app_id] = ApplianceState(**current)

    def get_appliance(self, appliance_id: str) -> Optional[ApplianceState]:
        return self.appliances.get(appliance_id)

    def step_energy(self, dt_minutes: float):
        """
        Advances energy and runtime accumulation across all active appliances.
        Simulates refrigerator duty cycles and runtime counters.
        """
        for app in self.appliances.values():
            # Refrigerator cycling: maintains periodic duty cycle
            if app.id == "refrigerator" and app.status == "ON":
                # Fluctuates around nominal 150W between 80W (idle) and 180W (cooling)
                cycle_minute = (app.total_runtime_minutes + dt_minutes) % 40
                if cycle_minute < 20:
                    app.power_watts = 180.0
                else:
                    app.power_watts = 90.0

            if app.status in ("ON", "ECO") and app.power_watts > 0:
                app.current_cycle_runtime_minutes += dt_minutes
                app.total_runtime_minutes += dt_minutes
                # kWh = (Watts * dt_hours) / 1000
                dt_hours = dt_minutes / 60.0
                delta_kwh = (app.power_watts * dt_hours) / 1000.0
                app.total_energy_kwh = round(app.total_energy_kwh + delta_kwh, 4)
            else:
                app.current_cycle_runtime_minutes = 0.0

    def calculate_totals(self) -> Dict[str, Any]:
        """Calculates total instantaneous power load and accumulated energy."""
        total_load_watts = sum(app.power_watts for app in self.appliances.values())
        total_energy_kwh = sum(app.total_energy_kwh for app in self.appliances.values())
        
        # Room-level aggregation
        room_power: Dict[str, float] = {}
        room_energy: Dict[str, float] = {}
        for app in self.appliances.values():
            room = app.room
            room_power[room] = round(room_power.get(room, 0.0) + app.power_watts, 2)
            room_energy[room] = round(room_energy.get(room, 0.0) + app.total_energy_kwh, 4)

        return {
            "total_load_watts": round(total_load_watts, 2),
            "total_energy_kwh": round(total_energy_kwh, 4),
            "room_power_watts": room_power,
            "room_energy_kwh": room_energy
        }

    def execute_action(
        self,
        appliance_id: str,
        action: str,
        status: Optional[str] = None,
        power_watts: Optional[float] = None,
        setpoint_c: Optional[float] = None,
        mode: Optional[str] = None,
        is_user_override: bool = False,
        override_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Safely executes an appliance state transition request.
        Validates parameters and prevents unhandled crashes.
        """
        app = self.appliances.get(appliance_id)
        if not app:
            logger.warning(f"Rejected action for unknown appliance: {appliance_id}")
            return {"success": False, "error": f"Appliance '{appliance_id}' not found"}

        action_norm = action.upper()
        prev_status = app.status

        if power_watts is not None and (
            not isinstance(power_watts, (int, float))
            or isinstance(power_watts, bool)
            or not math.isfinite(power_watts)
            or power_watts < 0
        ):
            return {"success": False, "error": "power_watts must be a finite non-negative number"}

        try:
            if action_norm in ("TURN_ON", "ON"):
                app.status = "ON"
                app.power_watts = power_watts if power_watts is not None else app.nominal_power_watts
                if mode is not None:
                    app.current_mode = mode
                if setpoint_c is not None:
                    app.setpoint_c = setpoint_c
                logger.info(f"Appliance {app.name} ({app.id}) turned ON at {app.power_watts}W")

            elif action_norm in ("TURN_OFF", "OFF"):
                app.status = "OFF"
                app.power_watts = 0.0
                logger.info(f"Appliance {app.name} ({app.id}) turned OFF")

            elif action_norm in ("SET_MODE", "ECO"):
                app.status = status if status else "ECO"
                if power_watts is not None:
                    app.power_watts = max(0.0, power_watts)
                elif app.status == "ECO":
                    app.power_watts = app.nominal_power_watts * 0.65
                else:
                    app.power_watts = app.nominal_power_watts
                if mode:
                    app.current_mode = mode
                if setpoint_c is not None:
                    app.setpoint_c = setpoint_c
                logger.info(f"Appliance {app.name} mode set to {app.status} ({app.power_watts}W)")

            elif action_norm == "SET_POWER":
                if power_watts is None:
                    return {"success": False, "error": "Invalid power_watts argument"}
                app.power_watts = float(power_watts)
                if app.power_watts > 0 and app.status == "OFF":
                    app.status = "ON"
                logger.info(f"Appliance {app.name} power explicitly set to {app.power_watts}W")

            else:
                return {"success": False, "error": f"Unsupported action: {action}"}

            if is_user_override:
                app.is_user_override = True
                app.override_reason = override_reason or "Manual User Actuation"
                logger.info(f"User override active on {app.name}: {app.status}")
            else:
                # Agent action: preserve user override if already active unless explicitly reset
                pass

            return {
                "success": True,
                "appliance_id": app.id,
                "previous_status": prev_status,
                "current_status": app.status,
                "power_watts": app.power_watts,
                "is_user_override": app.is_user_override
            }

        except Exception as e:
            logger.error(f"Error executing action on {appliance_id}: {e}")
            return {"success": False, "error": str(e)}

    def clear_user_override(self, appliance_id: str):
        if appliance_id in self.appliances:
            self.appliances[appliance_id].is_user_override = False
            self.appliances[appliance_id].override_reason = None
