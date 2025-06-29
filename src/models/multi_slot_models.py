"""
Multi-slot日次モデル用のデータ構造とクラス定義

このモジュールは、シフトマッチングシステムを時間単位から
スロット単位の日次モデルに拡張するための基盤を提供します。
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum

class SlotType(Enum):
    """スロットタイプの定義（1時間単位）"""
    HOUR_09 = "h09"  # 9:00-10:00
    HOUR_10 = "h10"  # 10:00-11:00
    HOUR_11 = "h11"  # 11:00-12:00
    HOUR_12 = "h12"  # 12:00-13:00
    HOUR_13 = "h13"  # 13:00-14:00
    HOUR_14 = "h14"  # 14:00-15:00
    HOUR_15 = "h15"  # 15:00-16:00
    HOUR_16 = "h16"  # 16:00-17:00
    HOUR_17 = "h17"  # 17:00-18:00

@dataclass
class TimeSlot:
    """時間スロットの定義（1時間単位）"""
    slot_id: str
    slot_type: SlotType
    start_time: time
    end_time: time
    duration_hours: float = 1.0
    
    def __post_init__(self):
        """スロット作成後の検証"""
        if self.duration_hours <= 0:
            raise ValueError("スロットの時間は正の値である必要があります")
    
    def overlaps_with(self, other: 'TimeSlot') -> bool:
        """他のスロットと重複するかチェック"""
        return not (self.end_time <= other.start_time or other.end_time <= self.start_time)

@dataclass
class DailySchedule:
    """1日のスケジュール定義"""
    date: datetime
    slots: List[TimeSlot] = field(default_factory=list)
    
    def add_slot(self, slot: TimeSlot):
        """スロットを追加"""
        self.slots.append(slot)
    
    def get_slot_by_id(self, slot_id: str) -> Optional[TimeSlot]:
        """スロットIDでスロットを取得"""
        for slot in self.slots:
            if slot.slot_id == slot_id:
                return slot
        return None

@dataclass
class OperatorAvailability:
    """オペレータの利用可能性"""
    operator_name: str
    available_slots: Set[str] = field(default_factory=set)
    preferred_slots: Set[str] = field(default_factory=set)
    desks: Set[str] = field(default_factory=set)  # 対応可能なデスクのセット
    max_work_hours_per_day: float = 8.0
    min_rest_hours_between_shifts: float = 11.0
    
    def can_work_slot(self, slot_id: str) -> bool:
        """指定されたスロットで働けるかチェック"""
        return slot_id in self.available_slots
    
    def prefers_slot(self, slot_id: str) -> bool:
        """指定されたスロットを好むかチェック"""
        return slot_id in self.preferred_slots
    
    def can_work_desk(self, desk_name: str) -> bool:
        """指定されたデスクで働けるかチェック"""
        return desk_name in self.desks

@dataclass
class DeskRequirement:
    """デスクの要件"""
    desk_name: str
    slot_requirements: Dict[str, int] = field(default_factory=dict)
    
    def get_requirement_for_slot(self, slot_id: str) -> int:
        """指定されたスロットの要件人数を取得"""
        return self.slot_requirements.get(slot_id, 0)
    
    def set_requirement_for_slot(self, slot_id: str, count: int):
        """指定されたスロットの要件人数を設定"""
        self.slot_requirements[slot_id] = count

@dataclass
class Assignment:
    """割り当て情報"""
    operator_name: str
    desk_name: str
    slot_id: str
    date: datetime
    assignment_type: str = "regular"  # regular, overtime, emergency
    
    def __post_init__(self):
        """割り当て作成後の検証"""
        if not self.operator_name or not self.desk_name or not self.slot_id:
            raise ValueError("オペレータ名、デスク名、スロットIDは必須です")

class MultiSlotScheduler:
    """Multi-slot日次スケジューラー"""
    
    def __init__(self, slots: List[TimeSlot]):
        self.slots = slots
        self.slot_ids = [slot.slot_id for slot in slots]
    
    def create_daily_schedule(self, date: datetime) -> DailySchedule:
        """指定された日付のスケジュールを作成"""
        daily_schedule = DailySchedule(date=date)
        for slot in self.slots:
            daily_schedule.add_slot(slot)
        return daily_schedule
    
    def validate_assignments(self, assignments: List[Assignment]) -> List[str]:
        """割り当ての妥当性を検証"""
        errors = []
        
        # 重複チェック
        assignment_keys = set()
        for assignment in assignments:
            key = (assignment.operator_name, assignment.slot_id, assignment.date)
            if key in assignment_keys:
                errors.append(f"重複割り当て: {assignment.operator_name} が {assignment.slot_id} に重複して割り当て")
            assignment_keys.add(key)
        
        # 時間制約チェック
        for assignment in assignments:
            # ここで時間制約の詳細チェックを実装
            pass
        
        return errors
    
    def calculate_work_hours(self, assignments: List[Assignment], operator_name: str, date: datetime) -> float:
        """指定されたオペレータの指定日の労働時間を計算"""
        total_hours = 0.0
        for assignment in assignments:
            if assignment.operator_name == operator_name and assignment.date.date() == date.date():
                slot = next((s for s in self.slots if s.slot_id == assignment.slot_id), None)
                if slot:
                    total_hours += slot.duration_hours
        return total_hours

def create_default_slots() -> List[TimeSlot]:
    """デフォルトのスロット設定を作成（1時間単位）"""
    slots = []
    for hour in range(9, 18):  # 9時から17時まで
        slot_id = f"h{hour:02d}"
        # SlotTypeの正しいメンバーにアクセス
        slot_type_name = f"HOUR_{hour:02d}"
        slot_type = getattr(SlotType, slot_type_name)
        start_time = time(hour, 0)
        end_time = time(hour + 1, 0) if hour < 23 else time(0, 0)
        
        slots.append(TimeSlot(
            slot_id=slot_id,
            slot_type=slot_type,
            start_time=start_time,
            end_time=end_time,
            duration_hours=1.0
        ))
    return slots

def convert_hourly_to_slots(hourly_requirements: pd.DataFrame) -> List[DeskRequirement]:
    """時間単位の要件をスロット単位に変換（1時間単位）"""
    desk_requirements = []
    
    for _, row in hourly_requirements.iterrows():
        desk_name = str(row["desk"])
        desk_req = DeskRequirement(desk_name=desk_name)
        
        # 各時間帯の要件を直接スロットに設定
        for hour in range(9, 18):  # 9時から17時まで
            slot_id = f"h{hour:02d}"
            col_name = f"h{hour:02d}"
            
            if col_name in row:
                requirement = int(row[col_name])
                desk_req.set_requirement_for_slot(slot_id, requirement)
                print(f"DEBUG: {desk_name} {slot_id}スロット要件: {requirement}")
        
        desk_requirements.append(desk_req)
    
    return desk_requirements 