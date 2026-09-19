import random
import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.app.simulator.environment import RoomState
from backend.app.simulator.weather import WeatherState
from backend.app.simulator.occupancy import OccupancyState
from backend.app.simulator.tariff import TariffState
from backend.app.simulator.appliances import ApplianceState


class SensorReading(BaseModel):
    sensor_id: str
    sensor_type: str  # temperature, humidity, occupancy, light_level, power, weather, tariff
    room_id: Optional[str] = None
    value: Any
    unit: str
    timestamp: str
    is_anomaly: bool = False


class SensorNetwork:
    """
    Simulates a network of physical IoT sensors placed throughout the smart home.
    Emulates realistic hardware sensor behavior with small calibrated measurement noise
    without erratic or jumpy values.
    """

    def __init__(self, noise_seed: Optional[int] = 42):
        self.rng = random.Random(noise_seed) if noise_seed is not None else random.Random()

    def generate_readings(
        self,
        current_time: datetime.datetime,
        rooms: Dict[str, RoomState],
        weather: WeatherState,
        occupancy: OccupancyState,
        tariff: TariffState,
        appliances: Dict[str, ApplianceState],
        total_load_watts: float
    ) -> Dict[str, SensorReading]:
        """Collects telemetry snapshots across all virtual sensors."""
        iso_time = current_time.isoformat()
        readings: Dict[str, SensorReading] = {}

        # Simulation clock. Keeping this in the sensor payload lets consumers use
        # the same timestamped observation contract for every input signal.
        readings["sensor_simulated_time"] = SensorReading(
            sensor_id="sensor_simulated_time",
            sensor_type="simulated_time",
            room_id=None,
            value=iso_time,
            unit="ISO 8601",
            timestamp=iso_time
        )

        # 1. Room Environmental Sensors
        for room_id, r in rooms.items():
            # Temperature sensor (calibrated noise: ±0.05°C)
            t_noise = self.rng.uniform(-0.04, 0.04)
            temp_val = round(r.temperature_c + t_noise, 2)
            readings[f"sensor_temp_{room_id}"] = SensorReading(
                sensor_id=f"sensor_temp_{room_id}",
                sensor_type="temperature",
                room_id=room_id,
                value=temp_val,
                unit="°C",
                timestamp=iso_time
            )

            # Humidity sensor (calibrated noise: ±0.2%)
            h_noise = self.rng.uniform(-0.15, 0.15)
            hum_val = round(max(0.0, min(100.0, r.humidity_pct + h_noise)), 1)
            readings[f"sensor_humidity_{room_id}"] = SensorReading(
                sensor_id=f"sensor_humidity_{room_id}",
                sensor_type="humidity",
                room_id=room_id,
                value=hum_val,
                unit="%",
                timestamp=iso_time
            )

            # PIR Occupancy / Motion sensor
            readings[f"sensor_occupancy_{room_id}"] = SensorReading(
                sensor_id=f"sensor_occupancy_{room_id}",
                sensor_type="occupancy",
                room_id=room_id,
                value=r.occupancy_count,
                unit="persons",
                timestamp=iso_time
            )

            # Lux ambient light sensor
            lux_noise = self.rng.uniform(-1.0, 1.0)
            lux_val = round(max(0.0, r.light_level_lux + lux_noise), 1)
            readings[f"sensor_light_{room_id}"] = SensorReading(
                sensor_id=f"sensor_light_{room_id}",
                sensor_type="light_level",
                room_id=room_id,
                value=lux_val,
                unit="Lux",
                timestamp=iso_time
            )

        # 2. Outdoor Weather Station
        readings["sensor_weather_outdoor_temp"] = SensorReading(
            sensor_id="sensor_weather_outdoor_temp",
            sensor_type="outdoor_temperature",
            room_id=None,
            value=weather.outdoor_temperature_c,
            unit="°C",
            timestamp=iso_time
        )
        readings["sensor_weather_condition"] = SensorReading(
            sensor_id="sensor_weather_condition",
            sensor_type="weather_condition",
            room_id=None,
            value=weather.condition.value,
            unit="condition",
            timestamp=iso_time
        )
        readings["sensor_weather_outdoor_humidity"] = SensorReading(
            sensor_id="sensor_weather_outdoor_humidity",
            sensor_type="humidity",
            room_id=None,
            value=weather.humidity_pct,
            unit="%",
            timestamp=iso_time
        )

        # 3. Smart Meter / Grid & Tariff Sensors
        readings["sensor_meter_total_load"] = SensorReading(
            sensor_id="sensor_meter_total_load",
            sensor_type="power",
            room_id=None,
            value=round(total_load_watts, 1),
            unit="Watts",
            timestamp=iso_time
        )
        readings["sensor_tariff_rate"] = SensorReading(
            sensor_id="sensor_tariff_rate",
            sensor_type="tariff",
            room_id=None,
            value=tariff.rate,
            unit=f"{tariff.currency}/kWh",
            timestamp=iso_time
        )
        readings["sensor_tariff_tier"] = SensorReading(
            sensor_id="sensor_tariff_tier",
            sensor_type="tariff",
            room_id=None,
            value=tariff.tier.value,
            unit="tier",
            timestamp=iso_time
        )

        # 4. Appliance Individual Smart Plugs
        for app_id, app in appliances.items():
            is_anomaly = (app.id == "washing_machine" and app.power_watts > 1200.0)
            readings[f"sensor_plug_{app_id}"] = SensorReading(
                sensor_id=f"sensor_plug_{app_id}",
                sensor_type="power",
                room_id=app.room,
                value=app.power_watts,
                unit="Watts",
                timestamp=iso_time,
                is_anomaly=is_anomaly
            )

        return readings
