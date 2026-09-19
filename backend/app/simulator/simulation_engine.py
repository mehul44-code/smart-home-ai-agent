import datetime
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.simulator.weather import WeatherSimulator, WeatherState, WeatherCondition
from backend.app.simulator.occupancy import OccupancySimulator, OccupancyState
from backend.app.simulator.tariff import TariffManager, TariffState, TariffTier
from backend.app.simulator.appliances import ApplianceManager, ApplianceState
from backend.app.simulator.environment import HomeEnvironment, RoomState
from backend.app.simulator.sensors import SensorNetwork, SensorReading

logger = logging.getLogger("smart_home.simulator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class HomeState(BaseModel):
    """
    Comprehensive, high-fidelity state representation of the simulated smart home.
    Provides the central data contract for future AI perception and decision engines.
    """
    timestamp: str = Field(..., description="ISO 8601 formatted simulation timestamp")
    simulated_time: datetime.datetime = Field(..., description="Current simulated datetime")
    is_running: bool = Field(True, description="Simulation running status")
    speed_multiplier: float = Field(1.0, description="Simulation acceleration multiplier")
    
    # Environment & Rooms
    rooms: Dict[str, RoomState] = Field(..., description="Living Room, Bedroom, and Kitchen states")
    weather: WeatherState = Field(..., description="Outdoor weather, ambient temp, humidity, and solar load")
    occupancy: OccupancyState = Field(..., description="Home and room-specific occupancy counts")
    
    # Appliances & Electrical Loads
    appliances: Dict[str, ApplianceState] = Field(..., description="Fleet of monitored smart appliances")
    total_load_watts: float = Field(..., ge=0.0, description="Instantaneous aggregate household load")
    total_energy_kwh: float = Field(..., ge=0.0, description="Cumulative electrical energy consumed")
    room_power_watts: Dict[str, float] = Field(..., description="Instantaneous power breakdown per room")
    room_energy_kwh: Dict[str, float] = Field(..., description="Cumulative energy breakdown per room")
    
    # Financial Tariff & Cost
    tariff: TariffState = Field(..., description="Current Time-of-Use tariff structure")
    estimated_cost_accumulated: float = Field(..., ge=0.0, description="Cumulative electricity bill in currency")
    
    # Sensors & Telemetry
    sensors: Dict[str, SensorReading] = Field(..., description="Virtual physical sensor telemetry readings")
    
    # Overrides & Active Scenario
    active_overrides: Dict[str, Any] = Field(default_factory=dict, description="Active user manual overrides")
    active_scenario: Optional[str] = Field(None, description="Active demo scenario ID if loaded")


class SimulationEngine:
    """
    Core Smart Home Simulation Engine.
    Orchestrates physical thermodynamics, weather, occupancy routines,
    appliance power dynamics, TOU tariffs, and virtual sensor networks.
    """

    def __init__(
        self,
        start_time: Optional[datetime.datetime] = None,
        default_step_minutes: float = 1.0,
        currency: str = "₹"
    ):
        self.initial_start_time = start_time or datetime.datetime(2026, 6, 15, 14, 0, 0)
        self.current_time = self.initial_start_time
        self.default_step_minutes = default_step_minutes
        self.is_running = True
        self.speed_multiplier = 1.0
        self.active_scenario: Optional[str] = None
        
        # Financial accumulation
        self.cumulative_cost = 0.0

        # Sub-simulators
        self.weather = WeatherSimulator(base_temp_c=28.0)
        self.occupancy = OccupancySimulator(max_household_size=3)
        self.tariff = TariffManager(off_peak_rate=4.0, normal_rate=8.0, peak_rate=12.0, currency=currency)
        self.appliances = ApplianceManager()
        self.environment = HomeEnvironment(base_indoor_temp=24.5, base_indoor_humidity=55.0)
        self.sensor_network = SensorNetwork()

        logger.info(f"Smart Home Simulation Engine initialized at {self.current_time.isoformat()}")

    def start(self):
        """Resumes or starts the simulation clock."""
        self.is_running = True
        logger.info("Simulation clock started.")

    def pause(self):
        """Freezes simulation time progression."""
        self.is_running = False
        logger.info("Simulation clock paused.")

    def reset(self):
        """Restores the simulator back to its initial pristine baseline."""
        self.current_time = self.initial_start_time
        self.is_running = True
        self.active_scenario = None
        self.cumulative_cost = 0.0

        self.weather = WeatherSimulator(base_temp_c=28.0)
        self.occupancy = OccupancySimulator(max_household_size=3)
        self.tariff.reset_override()
        self.appliances = ApplianceManager()
        self.environment.reset(base_temp=24.5, base_humidity=55.0)

        logger.info("Simulation reset to initial state.")

    def step(self, dt_minutes: Optional[float] = None) -> HomeState:
        """
        Advances the entire physical simulation forward by dt_minutes.
        Computes heat flows, power draws, appliance duty cycles, and energy costs.
        """
        dt = dt_minutes if dt_minutes is not None else self.default_step_minutes
        if dt < 0:
            raise ValueError("dt_minutes must be non-negative")

        step_start_time = self.current_time
        effective_dt = dt if self.is_running else 0.0

        if effective_dt > 0:
            self.current_time += datetime.timedelta(minutes=effective_dt)

        hour_float = self.current_time.hour + (self.current_time.minute / 60.0) + (self.current_time.second / 3600.0)

        # 1. Update sub-models
        w_state = self.weather.calculate_state(hour_float)
        occ_state = self.occupancy.calculate_state(hour_float)
        t_state = self.tariff.calculate_tariff(self.current_time.hour, self.current_time.minute)

        # 2. Advance appliance runtimes & power cycles
        if effective_dt > 0:
            self.appliances.step_energy(effective_dt)

        # 3. Advance multi-room thermodynamic physics
        if effective_dt > 0:
            self.environment.step_physics(
                dt_minutes=effective_dt,
                weather=w_state,
                occupancy=occ_state,
                appliances=self.appliances,
                hour=hour_float
            )

        # 4. Energy & Cost aggregation
        electrical_totals = self.appliances.calculate_totals()
        total_load_watts = electrical_totals["total_load_watts"]

        if effective_dt > 0:
            # Price every portion of a long step at the tariff active during that
            # portion. This keeps a 16:30--17:30 step from being charged entirely
            # at the 17:30 PEAK rate.
            step_cost = self._calculate_step_cost(total_load_watts, step_start_time, effective_dt)
            self.cumulative_cost = round(self.cumulative_cost + step_cost, 4)

        # 5. Compile room states
        room_states = self.environment.get_room_states(
            weather=w_state,
            occupancy=occ_state,
            appliances=self.appliances,
            hour=hour_float
        )

        # 6. Generate virtual sensor network telemetry
        sensor_readings = self.sensor_network.generate_readings(
            current_time=self.current_time,
            rooms=room_states,
            weather=w_state,
            occupancy=occ_state,
            tariff=t_state,
            appliances=self.appliances.appliances,
            total_load_watts=total_load_watts
        )

        # Active overrides tracking
        overrides = {
            app_id: {
                "status": app.status,
                "power_watts": app.power_watts,
                "reason": app.override_reason
            }
            for app_id, app in self.appliances.appliances.items()
            if app.is_user_override
        }

        return HomeState(
            timestamp=self.current_time.isoformat(),
            simulated_time=self.current_time,
            is_running=self.is_running,
            speed_multiplier=self.speed_multiplier,
            rooms=room_states,
            weather=w_state,
            occupancy=occ_state,
            appliances=self.appliances.appliances,
            total_load_watts=total_load_watts,
            total_energy_kwh=electrical_totals["total_energy_kwh"],
            room_power_watts=electrical_totals["room_power_watts"],
            room_energy_kwh=electrical_totals["room_energy_kwh"],
            tariff=t_state,
            estimated_cost_accumulated=round(self.cumulative_cost, 2),
            sensors=sensor_readings,
            active_overrides=overrides,
            active_scenario=self.active_scenario
        )

    def _calculate_step_cost(
        self,
        load_watts: float,
        start_time: datetime.datetime,
        dt_minutes: float
    ) -> float:
        """Return TOU-priced energy cost for a step, including tariff boundaries."""
        remaining_minutes = dt_minutes
        cursor = start_time
        cost = 0.0

        while remaining_minutes > 1e-9:
            tariff = self.tariff.calculate_tariff(cursor.hour, cursor.minute)
            # Manual tariff overrides intentionally apply until cleared.
            minutes_in_tier = (
                remaining_minutes
                if self.tariff.manual_override is not None
                else max(1.0 / 60.0, float(tariff.minutes_until_next_tier))
            )
            segment_minutes = min(remaining_minutes, minutes_in_tier)
            cost += (load_watts * (segment_minutes / 60.0) / 1000.0) * tariff.rate
            cursor += datetime.timedelta(minutes=segment_minutes)
            remaining_minutes -= segment_minutes

        return cost

    def advance_time(self, minutes: float) -> HomeState:
        """Accelerated simulation fast-forward without real-time delay."""
        return self.step(dt_minutes=minutes)

    def get_current_home_state(self) -> HomeState:
        """Safe non-advancing query for current home telemetry."""
        return self.step(dt_minutes=0.0)

    # Simulation Controller Modifiers
    def change_temperature(self, room_id: str, temp_c: float):
        self.environment.set_room_temperature(room_id, temp_c)
        logger.info(f"Room '{room_id}' temperature modified to {temp_c}°C")

    def change_occupancy(self, count: int, room_distribution: Optional[Dict[str, int]] = None):
        self.occupancy.set_override(total=count, room_distribution=room_distribution)
        logger.info(f"Occupancy modified to {count} occupants")

    def change_weather(self, condition: WeatherCondition, temp_c: Optional[float] = None, humidity_pct: Optional[float] = None):
        self.weather.set_condition(condition, temp_c=temp_c, humidity_pct=humidity_pct)
        logger.info(f"Weather condition changed to {condition.value}")

    def change_tariff(self, tier: TariffTier, rate: Optional[float] = None):
        self.tariff.set_override(tier, rate)
        logger.info(f"Tariff modified to {tier.value} ({rate} / kWh)")

    def turn_appliance_on(self, appliance_id: str, is_user_override: bool = False) -> Dict[str, Any]:
        return self.appliances.execute_action(appliance_id, "TURN_ON", is_user_override=is_user_override)

    def turn_appliance_off(self, appliance_id: str, is_user_override: bool = False) -> Dict[str, Any]:
        return self.appliances.execute_action(appliance_id, "TURN_OFF", is_user_override=is_user_override)

    def execute_appliance_action(
        self,
        appliance_id: str,
        action: str,
        status: Optional[str] = None,
        power_watts: Optional[float] = None,
        setpoint_c: Optional[float] = None,
        mode: Optional[str] = None,
        is_user_override: bool = False
    ) -> Dict[str, Any]:
        """Safe execution method for future AI agent actions or user overrides."""
        return self.appliances.execute_action(
            appliance_id=appliance_id,
            action=action,
            status=status,
            power_watts=power_watts,
            setpoint_c=setpoint_c,
            mode=mode,
            is_user_override=is_user_override
        )
