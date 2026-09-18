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
