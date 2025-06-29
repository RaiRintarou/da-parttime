"""
モデル層

Multi-slot日次モデルのデータ構造を提供します。
"""

from .multi_slot_models import (
    TimeSlot,
    DailySchedule,
    OperatorAvailability,
    DeskRequirement,
    Assignment,
    MultiSlotScheduler,
    SlotType,
    create_default_slots,
    convert_hourly_to_slots
)

__all__ = [
    "TimeSlot",
    "DailySchedule", 
    "OperatorAvailability",
    "DeskRequirement",
    "Assignment",
    "MultiSlotScheduler",
    "SlotType",
    "create_default_slots",
    "convert_hourly_to_slots"
] 