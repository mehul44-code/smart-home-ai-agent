import math
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.simulator.weather import WeatherState, WeatherCondition
from backend.app.simulator.occupancy import OccupancyState
from backend.app.simulator.appliances import ApplianceManager


class RoomState(BaseModel):
    room_id: str
    name: str
    temperature_c: float = Field(..., description="Indoor dry-bulb temperature in °C")
    humidity_pct: float = Field(..., description="Indoor relative humidity percentage (0-100%)")
    occupancy_count: int = Field(0, ge=0)
    is_occupied: bool = Field(False)
    light_level_lux: float = Field(..., ge=0.0, description="Illuminance in Lux")
    target_temperature_c: float = Field(22.0)
    outdoor_temperature_c: float = Field(...)
    weather_condition: WeatherCondition = Field(...)


class HomeEnvironment:
    """
    Thermodynamic and environmental model of a 3-room home:
    - Living Room (large thermal mass, AC, TV, Lights)
    - Bedroom (medium thermal mass, Ceiling Fan, Lights)
    - Kitchen (refrigerator, water heater, washing machine, cooking heat)
    """

    def __init__(self, base_indoor_temp: float = 24.0, base_indoor_humidity: float = 55.0):
        # Room physical parameters:
        # C_room (thermal capacitance kWh / °C)
        # R_envelope (thermal resistance °C / kW)
        self.rooms_config = {
            "living_room": {
                "name": "Living Room",
                "c_th": 12.0,
                "r_env": 3.0,
                "target_temp": 22.0,
                "window_area_factor": 1.2
            },
            "bedroom": {
                "name": "Bedroom",
                "c_th": 8.0,
                "r_env": 3.5,
                "target_temp": 22.5,
                "window_area_factor": 0.9
            },
            "kitchen": {
                "name": "Kitchen",
                "c_th": 6.5,
                "r_env": 3.2,
                "target_temp": 23.0,
                "window_area_factor": 0.7
            }
        }

        # Dynamic state
        self.temperatures: Dict[str, float] = {
            r: base_indoor_temp for r in self.rooms_config
        }
        self.humidities: Dict[str, float] = {
            r: base_indoor_humidity for r in self.rooms_config
        }

    def reset(self, base_temp: float = 24.0, base_humidity: float = 55.0):
        for r in self.temperatures:
            self.temperatures[r] = base_temp
            self.humidities[r] = base_humidity

    def set_room_temperature(self, room_id: str, temp_c: float):
        if room_id in self.temperatures:
            self.temperatures[room_id] = round(temp_c, 2)

    def set_room_humidity(self, room_id: str, humidity_pct: float):
        if room_id in self.humidities:
            self.humidities[room_id] = round(max(10.0, min(100.0, humidity_pct)), 1)

    def step_physics(
        self,
        dt_minutes: float,
        weather: WeatherState,
        occupancy: OccupancyState,
        appliances: ApplianceManager,
        hour: float
    ):
        """
        Advances the thermodynamic state of each room over dt_minutes:
        1. Envelope conductive & solar heat flux from outdoor weather
        2. Internal heat gains from occupants (~100W each)
        3. Internal heat gains from running appliances
        4. Active HVAC cooling and dehumidification
        5. Ceiling fan air circulation
        6. Inter-room thermal coupling (diffusion across interior walls)
        """
        dt_hours = dt_minutes / 60.0
        new_temps = dict(self.temperatures)
        new_humidities = dict(self.humidities)

        # 1. Individual room thermal & moisture balance
        for room_id, cfg in self.rooms_config.items():
            t_in = self.temperatures[room_id]
            h_in = self.humidities[room_id]
            c_th = cfg["c_th"]
            r_env = cfg["r_env"]

            # Heat transfer through building envelope (kW)
            # Weather heating factor amplifies solar heat gain through windows
            q_envelope = ((weather.outdoor_temperature_c - t_in) / r_env) * weather.heating_factor

            # Internal heat gains from occupants (approx 0.1 kW / person)
            occ_count = occupancy.room_occupancy.get(room_id, 0)
            q_occupants = occ_count * 0.10

            # Internal heat gains from appliances located in this room (kW)
            room_appliances = [app for app in appliances.appliances.values() if app.room == room_id]
            appliance_watts = sum(app.power_watts for app in room_appliances)
            # Most electrical power eventually converts to heat, except active cooling
            q_appliances_heat = (appliance_watts / 1000.0) * 0.40

            # Active cooling heat extraction (kW)
            q_cooling = 0.0
            dehumidification_rate = 0.0

            if room_id == "living_room":
                ac = appliances.get_appliance("ac_living_room")
                if ac and ac.status in ("ON", "ECO") and ac.power_watts > 0:
                    cop = 3.2 if ac.status == "ON" else 3.5
                    # Cooling capacity = Electric Power * COP
                    cooling_capacity_kw = (ac.power_watts / 1000.0) * cop
                    # Modulate cooling if room is already at or below setpoint
                    setpoint = ac.setpoint_c or 22.0
                    temp_gap = max(0.0, t_in - setpoint)
                    throttle = min(1.0, temp_gap / 1.5) if temp_gap > 0 else 0.05
                    q_cooling = cooling_capacity_kw * throttle
                    # AC condenser extracts moisture
                    dehumidification_rate = 0.08 * (ac.power_watts / 1500.0)

            elif room_id == "bedroom":
                fan = appliances.get_appliance("fan_bedroom")
                if fan and fan.status == "ON":
                    # Fans circulate air: slight thermal cooling (~0.05 kW equivalent sensible drop)
                    q_cooling = 0.05

            # Net temperature rate of change: dT/dt = (Q_in - Q_out) / C_th
            dT_dt = (q_envelope + q_occupants + q_appliances_heat - q_cooling) / c_th
            new_temps[room_id] = t_in + (dT_dt * dt_hours)

            # Humidity rate of change:
            # - Outdoor humidity slowly diffuses in (rate proportional to gap)
            # - Occupants add slight humidity (+0.02 %/min)
            # - AC removes humidity
            dh_dt = ((weather.humidity_pct - h_in) * 0.02) + (occ_count * 0.05) - (dehumidification_rate * 10.0)
            new_humidities[room_id] = max(25.0, min(95.0, h_in + (dh_dt * dt_minutes)))

        # 2. Inter-room thermal coupling (heat diffusion between rooms)
        # Living Room connects to Bedroom and Kitchen
        k_inter = 0.15 * dt_hours  # coupling coefficient
        delta_lr_br = (new_temps["living_room"] - new_temps["bedroom"]) * k_inter
        delta_lr_kt = (new_temps["living_room"] - new_temps["kitchen"]) * k_inter

        new_temps["living_room"] -= (delta_lr_br + delta_lr_kt) * 0.5
        new_temps["bedroom"] += delta_lr_br * 0.5
        new_temps["kitchen"] += delta_lr_kt * 0.5

        # Update stored states
        for r in self.rooms_config:
            self.temperatures[r] = round(new_temps[r], 2)
            self.humidities[r] = round(new_humidities[r], 1)

    def get_room_light_level(self, room_id: str, hour: float, appliances: ApplianceManager) -> float:
        """
        Calculates ambient room illuminance in Lux based on:
        - Daylight sun curve (0 lx at night to 400 lx near large windows at noon)
        - Active room lights (+350 lx when turned ON)
        """
        # Base natural light:
        if 6.0 <= hour <= 18.5:
            sun_angle = math.sin((hour - 6.0) * math.pi / 12.5)
            window_factor = self.rooms_config.get(room_id, {}).get("window_area_factor", 1.0)
            natural_lux = max(0.0, 420.0 * sun_angle * window_factor)
        else:
            natural_lux = 2.0  # night ambient moonlight/street light

        # Electric artificial lighting
        light_app_id = f"lights_{room_id}"
        light_app = appliances.get_appliance(light_app_id)
        artificial_lux = 0.0
        if light_app and light_app.status == "ON":
            artificial_lux = 380.0

        return round(natural_lux + artificial_lux, 1)

    def get_room_states(
        self,
        weather: WeatherState,
        occupancy: OccupancyState,
        appliances: ApplianceManager,
        hour: float
    ) -> Dict[str, RoomState]:
        """Generates comprehensive state objects for all 3 rooms."""
        states = {}
        for room_id, cfg in self.rooms_config.items():
            occ = occupancy.room_occupancy.get(room_id, 0)
            states[room_id] = RoomState(
                room_id=room_id,
                name=cfg["name"],
                temperature_c=self.temperatures[room_id],
                humidity_pct=self.humidities[room_id],
                occupancy_count=occ,
                is_occupied=occ > 0,
                light_level_lux=self.get_room_light_level(room_id, hour, appliances),
                target_temperature_c=cfg["target_temp"],
                outdoor_temperature_c=weather.outdoor_temperature_c,
                weather_condition=weather.condition
            )
        return states
