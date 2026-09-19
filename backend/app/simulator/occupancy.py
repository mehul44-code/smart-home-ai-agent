import random
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class OccupancyState(BaseModel):
    """Represents current home-level and room-level occupancy."""
    total_occupants: int = Field(..., ge=0, description="Total occupants in the house")
    is_occupied: bool = Field(..., description="True if at least one occupant is home")
    room_occupancy: Dict[str, int] = Field(..., description="Mapping of room_id to occupant count")
    mode: str = Field("SCHEDULED", description="SCHEDULED or MANUAL_OVERRIDE")


class OccupancySimulator:
    """
    Household occupancy simulator modeling realistic human behavioral patterns:
    - 00:00 - 07:00: Night sleep (occupants in bedroom)
    - 07:00 - 09:00: Morning routine (occupancy active across bedroom, kitchen, living room)
    - 09:00 - 17:00: Workday/school (occupancy decreases to 0 or minimal)
    - 17:00 - 23:00: Evening family time (high occupancy in living room & kitchen)
    - 23:00 - 00:00: Wind-down to sleep
    """

    def __init__(self, max_household_size: int = 3, seed: Optional[int] = 42):
        self.max_household_size = max_household_size
        self.random_gen = random.Random(seed) if seed is not None else random.Random()
        self.manual_override: Optional[Dict[str, Any]] = None

    def set_override(self, total: Optional[int] = None, room_distribution: Optional[Dict[str, int]] = None):
        """Allows explicit external setting of occupants for scenarios or user testing."""
        if total is None and room_distribution is None:
            self.manual_override = None
            return

        if room_distribution is not None:
            calc_total = sum(room_distribution.values())
            self.manual_override = {
                "total": total if total is not None else calc_total,
                "rooms": room_distribution
            }
        else:
            # Distribute total occupants evenly/sensibly
            tot = total if total is not None else 0
            lr = min(tot, 1)
            br = max(0, tot - lr)
            self.manual_override = {
                "total": tot,
                "rooms": {
                    "living_room": lr,
                    "bedroom": br,
                    "kitchen": 0
                }
            }

    def reset_override(self):
        self.manual_override = None

    def calculate_state(self, hour: float) -> OccupancyState:
        """Computes room-specific and total occupancy for a given hour."""
        if self.manual_override is not None:
            tot = self.manual_override["total"]
            rooms = self.manual_override["rooms"]
            return OccupancyState(
                total_occupants=tot,
                is_occupied=tot > 0,
                room_occupancy=rooms,
                mode="MANUAL_OVERRIDE"
            )

        rooms = {"living_room": 0, "bedroom": 0, "kitchen": 0}

        # Time-based behavioral scheduling
        if 0.0 <= hour < 7.0:
            # Night: Household sleeping in bedroom
            total = self.max_household_size
            rooms["bedroom"] = total
            rooms["living_room"] = 0
            rooms["kitchen"] = 0
        elif 7.0 <= hour < 9.0:
            # Morning preparation: Occupancy transitions to kitchen & living room
            total = self.max_household_size
            rooms["kitchen"] = max(1, total // 2)
            rooms["living_room"] = total - rooms["kitchen"]
            rooms["bedroom"] = 0
        elif 9.0 <= hour < 17.0:
            # Daytime working hours: Most or all leave the house
            # Realistic chance of 0 or 1 working from home
            total = 1 if self.max_household_size >= 3 else 0
            rooms["living_room"] = total
            rooms["bedroom"] = 0
            rooms["kitchen"] = 0
        elif 17.0 <= hour < 22.0:
            # Evening: High activity in living room and kitchen
            total = self.max_household_size
            rooms["living_room"] = max(1, total - 1)
            rooms["kitchen"] = 1
            rooms["bedroom"] = 0
        else:
            # 22.0 - 24.0: Heading to bed
            total = self.max_household_size
            rooms["bedroom"] = total - 1
            rooms["living_room"] = 1
            rooms["kitchen"] = 0

        total_count = sum(rooms.values())

        return OccupancyState(
            total_occupants=total_count,
            is_occupied=total_count > 0,
            room_occupancy=rooms,
            mode="SCHEDULED"
        )
