import math
import random
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class WeatherCondition(str, Enum):
    SUNNY = "SUNNY"
    CLOUDY = "CLOUDY"
    RAINY = "RAINY"
    HOT = "HOT"
    MILD = "MILD"


class WeatherState(BaseModel):
    """Represents current ambient weather state."""
    outdoor_temperature_c: float = Field(..., description="Outdoor ambient dry-bulb temperature in °C")
    humidity_pct: float = Field(..., description="Outdoor relative humidity percentage (0-100%)")
    condition: WeatherCondition = Field(WeatherCondition.SUNNY, description="Current weather condition")
    solar_irradiance_w_m2: float = Field(..., description="Solar irradiance in Watts per square meter")
    heating_factor: float = Field(1.0, description="Solar and ambient heating multiplier on building envelope")


class WeatherSimulator:
    """
    Lightweight, realistic outdoor weather and ambient temperature simulator.
    Models continuous diurnal temperature curves matching realistic times:
    - Morning (06:00 - 12:00): ~22 - 26°C
    - Afternoon (12:00 - 17:00): ~27 - 34°C
    - Evening (17:00 - 22:00): ~25 - 30°C
    - Night (22:00 - 06:00): ~22 - 27°C
    """

    def __init__(
        self,
        base_temp_c: float = 27.0,
        temp_amplitude_c: float = 5.5,
        condition: WeatherCondition = WeatherCondition.SUNNY,
        seed: Optional[int] = 42
    ):
        self.base_temp_c = base_temp_c
        self.temp_amplitude_c = temp_amplitude_c
        self.condition = condition
        self.random_gen = random.Random(seed) if seed is not None else random.Random()
        
        # Smoothed noise offsets
        self._temp_offset = 0.0
        self._humidity_offset = 0.0
        self.manual_override: Optional[Dict[str, Any]] = None

    def set_condition(self, condition: WeatherCondition, temp_c: Optional[float] = None, humidity_pct: Optional[float] = None):
        """Allows explicit external or scenario-driven weather setting."""
        self.condition = condition
        if temp_c is not None or humidity_pct is not None:
            self.manual_override = {
                "temperature": temp_c,
                "humidity": humidity_pct
            }
        else:
            self.manual_override = None

    def reset_override(self):
        self.manual_override = None

    def calculate_state(self, hour: float) -> WeatherState:
        """
        Computes the weather state for the given hour of the day (0.0 - 24.0).
        Smoothly interpolates diurnal curves and applies weather condition modifiers.
        """
        if self.manual_override is not None:
            ovr_t = self.manual_override.get("temperature")
            ovr_h = self.manual_override.get("humidity")
            temp = ovr_t if ovr_t is not None else self.base_temp_c
            hum = ovr_h if ovr_h is not None else 60.0
            return WeatherState(
                outdoor_temperature_c=round(temp, 2),
                humidity_pct=round(hum, 1),
                condition=self.condition,
                solar_irradiance_w_m2=450.0 if self.condition == WeatherCondition.SUNNY else 100.0,
                heating_factor=1.1 if self.condition in (WeatherCondition.SUNNY, WeatherCondition.HOT) else 0.8
            )

        # Baseline diurnal temperature cycle:
        # Minimum around 05:30 (sunrise), maximum around 15:00 (mid-afternoon)
        # Shift hour by 9.0 so sine peak occurs at hour 15.0: sin((15 - 9) * pi / 12) = sin(pi/2) = 1.0
        rad = (hour - 9.0) * math.pi / 12.0
        diurnal_temp = self.base_temp_c + self.temp_amplitude_c * math.sin(rad)

        # Condition-specific modifiers:
        condition_temp_delta = 0.0
        condition_humidity_base = 55.0
        heating_factor = 1.0
        cloud_factor = 1.0

        if self.condition == WeatherCondition.HOT:
            condition_temp_delta = +4.5
            condition_humidity_base = 40.0
            heating_factor = 1.35
            cloud_factor = 1.0
        elif self.condition == WeatherCondition.MILD:
            condition_temp_delta = -1.5
            condition_humidity_base = 50.0
            heating_factor = 0.95
            cloud_factor = 0.9
        elif self.condition == WeatherCondition.CLOUDY:
            condition_temp_delta = -2.5
            condition_humidity_base = 70.0
            heating_factor = 0.75
            cloud_factor = 0.4
        elif self.condition == WeatherCondition.RAINY:
            condition_temp_delta = -4.0
            condition_humidity_base = 88.0
            heating_factor = 0.60
            cloud_factor = 0.2
        elif self.condition == WeatherCondition.SUNNY:
            condition_temp_delta = +0.5
            condition_humidity_base = 48.0
            heating_factor = 1.10
            cloud_factor = 1.0

        # Small continuous variation without random jumping
        self._temp_offset += self.random_gen.uniform(-0.05, 0.05)
        self._temp_offset = max(-0.5, min(0.5, self._temp_offset))

        outdoor_temp = diurnal_temp + condition_temp_delta + self._temp_offset

        # Relative humidity typically has inverse relationship with temperature:
        # Cooler air has higher RH; warmer air has lower RH.
        temp_ratio = (outdoor_temp - 22.0) / 14.0  # normalized across 22-36C
        diurnal_humidity = condition_humidity_base - (temp_ratio * 20.0)
        self._humidity_offset += self.random_gen.uniform(-0.1, 0.1)
        self._humidity_offset = max(-2.0, min(2.0, self._humidity_offset))
        humidity = max(20.0, min(98.0, diurnal_humidity + self._humidity_offset))

        # Solar irradiance calculation (W/m^2)
        if 6.0 <= hour <= 19.0:
            solar_sin = math.sin((hour - 6.0) * math.pi / 13.0)
            solar_irradiance = max(0.0, 950.0 * solar_sin * cloud_factor)
        else:
            solar_irradiance = 0.0

        return WeatherState(
            outdoor_temperature_c=round(outdoor_temp, 2),
            humidity_pct=round(humidity, 1),
            condition=self.condition,
            solar_irradiance_w_m2=round(solar_irradiance, 1),
            heating_factor=round(heating_factor, 2)
        )
