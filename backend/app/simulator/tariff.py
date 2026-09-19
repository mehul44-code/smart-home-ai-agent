from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class TariffTier(str, Enum):
    OFF_PEAK = "OFF_PEAK"
    NORMAL = "NORMAL"
    PEAK = "PEAK"


class TariffPeriod(BaseModel):
    tier: TariffTier
    start_hour: float
    end_hour: float
    rate: float
    label: str


class TariffState(BaseModel):
    """Represents current electricity tariff parameters."""
    tier: TariffTier = Field(..., description="Active tariff tier name")
    rate: float = Field(..., ge=0.0, description="Price per kWh in configured currency")
    currency: str = Field("₹", description="Currency symbol (e.g. ₹ or INR)")
    time_period_label: str = Field(..., description="Human-readable schedule window")
    minutes_until_next_tier: int = Field(..., ge=0, description="Minutes remaining until next price change")
    next_tier: TariffTier = Field(..., description="Upcoming tariff tier")
    next_rate: float = Field(..., ge=0.0, description="Upcoming rate per kWh")
    next_off_peak_minutes: int = Field(0, ge=0, description="Minutes until the next off-peak period")
    next_off_peak_rate: float = Field(0.0, ge=0.0, description="Rate in the next off-peak period")


class TariffManager:
    """
    Manages Time-of-Use (TOU) electricity pricing tariffs.
    Default configuration:
    - OFF_PEAK: ₹4/kWh (00:00 - 06:00 & 22:00 - 24:00)
    - NORMAL:   ₹8/kWh (06:00 - 17:00)
    - PEAK:     ₹12/kWh (17:00 - 22:00)
    """

    def __init__(
        self,
        off_peak_rate: float = 4.0,
        normal_rate: float = 8.0,
        peak_rate: float = 12.0,
        currency: str = "₹"
    ):
        self.currency = currency
        self.rates = {
            TariffTier.OFF_PEAK: off_peak_rate,
            TariffTier.NORMAL: normal_rate,
            TariffTier.PEAK: peak_rate
        }
        self.schedule: List[TariffPeriod] = [
            TariffPeriod(tier=TariffTier.OFF_PEAK, start_hour=0.0, end_hour=6.0, rate=off_peak_rate, label="00:00–06:00"),
            TariffPeriod(tier=TariffTier.NORMAL, start_hour=6.0, end_hour=17.0, rate=normal_rate, label="06:00–17:00"),
            TariffPeriod(tier=TariffTier.PEAK, start_hour=17.0, end_hour=22.0, rate=peak_rate, label="17:00–22:00"),
            TariffPeriod(tier=TariffTier.OFF_PEAK, start_hour=22.0, end_hour=24.0, rate=off_peak_rate, label="22:00–24:00")
        ]
        self.manual_override: Optional[Dict[str, Any]] = None

    def set_override(self, tier: TariffTier, rate: Optional[float] = None):
        self.manual_override = {
            "tier": tier,
            "rate": rate if rate is not None else self.rates.get(tier, 8.0)
        }

    def reset_override(self):
        self.manual_override = None

    def update_rates(self, off_peak: Optional[float] = None, normal: Optional[float] = None, peak: Optional[float] = None):
        if off_peak is not None:
            self.rates[TariffTier.OFF_PEAK] = off_peak
        if normal is not None:
            self.rates[TariffTier.NORMAL] = normal
        if peak is not None:
            self.rates[TariffTier.PEAK] = peak

        # Rebuild schedule
        self.schedule = [
            TariffPeriod(tier=TariffTier.OFF_PEAK, start_hour=0.0, end_hour=6.0, rate=self.rates[TariffTier.OFF_PEAK], label="00:00–06:00"),
            TariffPeriod(tier=TariffTier.NORMAL, start_hour=6.0, end_hour=17.0, rate=self.rates[TariffTier.NORMAL], label="06:00–17:00"),
            TariffPeriod(tier=TariffTier.PEAK, start_hour=17.0, end_hour=22.0, rate=self.rates[TariffTier.PEAK], label="17:00–22:00"),
            TariffPeriod(tier=TariffTier.OFF_PEAK, start_hour=22.0, end_hour=24.0, rate=self.rates[TariffTier.OFF_PEAK], label="22:00–24:00")
        ]

    def calculate_tariff(self, hour: float, minute: float = 0.0) -> TariffState:
        """Calculates the active tariff tier and upcoming transition window."""
        currentTimeFloat = (hour % 24.0) + (minute / 60.0)

        if self.manual_override is not None:
            tier = self.manual_override["tier"]
            rate = self.manual_override["rate"]
            off_peak_minutes, off_peak_rate = self._next_off_peak_forecast(currentTimeFloat)
            return TariffState(
                tier=tier,
                rate=rate,
                currency=self.currency,
                time_period_label="MANUAL_OVERRIDE",
                minutes_until_next_tier=999,
                next_tier=tier,
                next_rate=rate,
                next_off_peak_minutes=off_peak_minutes,
                next_off_peak_rate=off_peak_rate,
            )

        active_period = self.schedule[0]
        active_index = 0
        for idx, period in enumerate(self.schedule):
            if period.start_hour <= currentTimeFloat < period.end_hour:
                active_period = period
                active_index = idx
                break

        # Calculate minutes until next period
        minutes_remaining = int((active_period.end_hour - currentTimeFloat) * 60.0)
        next_index = (active_index + 1) % len(self.schedule)
        next_period = self.schedule[next_index]
        # Forecast the first upcoming OFF_PEAK window using the same configured
        # tariff schedule (rather than hard-coding a household rate).
        elapsed, off_peak_rate = self._next_off_peak_forecast(currentTimeFloat)

        return TariffState(
            tier=active_period.tier,
            rate=active_period.rate,
            currency=self.currency,
            time_period_label=active_period.label,
            minutes_until_next_tier=max(0, minutes_remaining),
            next_tier=next_period.tier,
            next_rate=next_period.rate,
            next_off_peak_minutes=int(round(elapsed)),
            next_off_peak_rate=off_peak_rate,
        )

    def _next_off_peak_forecast(self, current_time_float: float) -> tuple[int, float]:
        """Forecast from the configured schedule even when current price is overridden."""
        active_index = next((idx for idx, period in enumerate(self.schedule)
                             if period.start_hour <= current_time_float < period.end_hour), 0)
        active_period = self.schedule[active_index]
        if active_period.tier == TariffTier.OFF_PEAK:
            return 0, active_period.rate
        elapsed = 0.0
        cursor_index = active_index
        cursor_hour = current_time_float
        for _ in range(len(self.schedule) + 1):
            period = self.schedule[cursor_index]
            remaining = (period.end_hour - cursor_hour) if cursor_index == active_index else (period.end_hour - period.start_hour)
            elapsed += max(0.0, remaining) * 60.0
            cursor_index = (cursor_index + 1) % len(self.schedule)
            cursor_hour = self.schedule[cursor_index].start_hour
            if self.schedule[cursor_index].tier == TariffTier.OFF_PEAK:
                return int(round(elapsed)), self.schedule[cursor_index].rate
        return 0, self.rates[TariffTier.OFF_PEAK]
