import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, JSON
from backend.app.database.database import Base


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class TelemetryRecord(Base):
    """Historical sensor and smart meter readings."""
    __tablename__ = "telemetry_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    indoor_temp_c = Column(Float, nullable=False)
    outdoor_temp_c = Column(Float, nullable=False)
    humidity_pct = Column(Float, nullable=False)
    occupancy = Column(Boolean, default=False)
    tariff_rate = Column(Float, nullable=False)
    total_power_kw = Column(Float, nullable=False)
    solar_power_kw = Column(Float, default=0.0)
    grid_power_kw = Column(Float, nullable=False)


class ApplianceRecord(Base):
    """Appliance metadata, current operational state, and power ratings."""
    __tablename__ = "appliances"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)  # HVAC, EV, WATER_HEATER, etc.
    status = Column(String(32), default="OFF")      # ON, OFF, ECO, IDLE
    current_power_kw = Column(Float, default=0.0)
    rated_power_kw = Column(Float, nullable=False)
    priority = Column(String(32), default="MEDIUM") # CRITICAL, HIGH, MEDIUM, LOW
    is_shiftable = Column(Boolean, default=True)
    setpoint_c = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=utc_now)


class AgentDecisionLog(Base):
    """Audit log of decisions across the 7-stage cognitive loop."""
    __tablename__ = "agent_decision_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    stage_data = Column(JSON, nullable=False)  # Serialized 7-stage output
    selected_action = Column(String(128), nullable=False)
    estimated_cost_saving = Column(Float, default=0.0)
    comfort_score = Column(Float, default=1.0)
    explanation = Column(Text, nullable=False)


# Persistent history tables. The simulator remains the authoritative source for
# current state; these rows are snapshots and audit records for later analysis.
class SensorReadingRecord(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True, nullable=False)
    simulated_time = Column(DateTime, index=True, nullable=False)
    room = Column(String(64), nullable=True, index=True)
    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    occupancy_count = Column(Integer, nullable=True)
    light_level_lux = Column(Float, nullable=True)
    outdoor_temperature_c = Column(Float, nullable=True)
    weather = Column(String(32), nullable=True)
    snapshot = Column(JSON, nullable=False)


class ApplianceEvent(Base):
    __tablename__ = "appliance_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True, nullable=False)
    appliance_id = Column(String(64), nullable=True, index=True)
    room = Column(String(64), nullable=True)
    event_type = Column(String(64), nullable=False)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    source = Column(String(32), nullable=False, default="SYSTEM")
    reason = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=True)


class EnergyConsumption(Base):
    __tablename__ = "energy_consumption"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True, nullable=False)
    simulated_time = Column(DateTime, index=True, nullable=False)
    appliance_id = Column(String(64), nullable=True, index=True)
    power_watts = Column(Float, nullable=True)
    energy_kwh = Column(Float, nullable=True)
    total_load_watts = Column(Float, nullable=False)
    cumulative_energy_kwh = Column(Float, nullable=False)
    tariff_tier = Column(String(32), nullable=False)
    tariff_rate = Column(Float, nullable=False)
    estimated_cost = Column(Float, nullable=False)


class TariffHistory(Base):
    __tablename__ = "tariff_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True, nullable=False)
    simulated_time = Column(DateTime, index=True, nullable=False)
    tier = Column(String(32), nullable=False)
    rate = Column(Float, nullable=False)
    currency = Column(String(16), nullable=False)
    next_tier = Column(String(32), nullable=True)
    next_rate = Column(Float, nullable=True)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, default=1)
    preferred_temperature = Column(Float, nullable=False, default=22.0)
    comfort_priority = Column(Float, nullable=False, default=0.5)
    energy_priority = Column(Float, nullable=False, default=0.5)
    selected_mode = Column(String(32), nullable=False, default="BALANCED")
    manual_override = Column(Boolean, nullable=False, default=False)
    override_expiry = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True, nullable=False)
    event_type = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    source = Column(String(32), nullable=False, default="SYSTEM")


class AnomalyRecord(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True, nullable=False)
    appliance_id = Column(String(64), nullable=True, index=True)
    expected_power_watts = Column(Float, nullable=False)
    actual_power_watts = Column(Float, nullable=False)
    deviation_watts = Column(Float, nullable=False)
    severity = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="OPEN")
    details = Column(JSON, nullable=True)


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, index=True, nullable=False)
    decision = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    selected_action = Column(JSON, nullable=True)
    expected_energy_kwh = Column(Float, nullable=True)
    expected_comfort = Column(Float, nullable=True)
    expected_cost = Column(Float, nullable=True)
    sensor_snapshot = Column(JSON, nullable=True)
    predictions = Column(JSON, nullable=True)
    candidate_actions = Column(JSON, nullable=True)
    candidate_scores = Column(JSON, nullable=True)
