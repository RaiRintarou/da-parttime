"""
Multi-slot日次モデルのユニットテスト

このモジュールは、Multi-slot日次モデルの各コンポーネントの
動作を検証するためのテストケースを提供します。
"""

import pytest
import pandas as pd
from datetime import datetime, time
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models import (
    TimeSlot, DailySchedule, OperatorAvailability, 
    DeskRequirement, Assignment, MultiSlotScheduler,
    SlotType, create_default_slots, convert_hourly_to_slots
)
from algorithms import (
    MultiSlotDAMatchingAlgorithm, convert_legacy_operators_to_multi_slot,
    multi_slot_da_match, convert_assignments_to_dataframe
)

class TestTimeSlot:
    """TimeSlotクラスのテスト"""
    
    def test_time_slot_creation(self):
        """TimeSlotの作成テスト"""
        slot = TimeSlot("morning", SlotType.MORNING, time(9, 0), time(12, 0), 3.0)
        assert slot.slot_id == "morning"
        assert slot.slot_type == SlotType.MORNING
        assert slot.start_time == time(9, 0)
        assert slot.end_time == time(12, 0)
        assert slot.duration_hours == 3.0
    
    def test_time_slot_validation(self):
        """TimeSlotの検証テスト"""
        with pytest.raises(ValueError):
            TimeSlot("invalid", SlotType.MORNING, time(9, 0), time(12, 0), -1.0)
    
    def test_time_slot_overlap(self):
        """TimeSlotの重複チェックテスト"""
        slot1 = TimeSlot("morning", SlotType.MORNING, time(9, 0), time(12, 0), 3.0)
        slot2 = TimeSlot("afternoon", SlotType.AFTERNOON, time(12, 0), time(17, 0), 5.0)
        slot3 = TimeSlot("overlap", SlotType.EVENING, time(11, 0), time(13, 0), 2.0)
        
        assert not slot1.overlaps_with(slot2)  # 重複しない
        assert slot1.overlaps_with(slot3)      # 重複する
        assert slot2.overlaps_with(slot3)      # 重複する

class TestDailySchedule:
    """DailyScheduleクラスのテスト"""
    
    def test_daily_schedule_creation(self):
        """DailyScheduleの作成テスト"""
        date = datetime(2024, 1, 1)
        schedule = DailySchedule(date=date)
        assert schedule.date == date
        assert len(schedule.slots) == 0
    
    def test_add_slot(self):
        """スロット追加テスト"""
        schedule = DailySchedule(date=datetime(2024, 1, 1))
        slot = TimeSlot("morning", SlotType.MORNING, time(9, 0), time(12, 0), 3.0)
        
        schedule.add_slot(slot)
        assert len(schedule.slots) == 1
        assert schedule.slots[0] == slot
    
    def test_get_slot_by_id(self):
        """スロットID取得テスト"""
        schedule = DailySchedule(date=datetime(2024, 1, 1))
        slot = TimeSlot("morning", SlotType.MORNING, time(9, 0), time(12, 0), 3.0)
        schedule.add_slot(slot)
        
        found_slot = schedule.get_slot_by_id("morning")
        assert found_slot == slot
        
        not_found = schedule.get_slot_by_id("nonexistent")
        assert not_found is None

class TestOperatorAvailability:
    """OperatorAvailabilityクラスのテスト"""
    
    def test_operator_availability_creation(self):
        """OperatorAvailabilityの作成テスト"""
        op = OperatorAvailability(
            operator_name="test_op",
            available_slots={"morning", "afternoon"},
            preferred_slots={"morning"}
        )
        assert op.operator_name == "test_op"
        assert "morning" in op.available_slots
        assert "afternoon" in op.available_slots
        assert "morning" in op.preferred_slots
        assert "afternoon" not in op.preferred_slots
    
    def test_can_work_slot(self):
        """スロット利用可能性チェックテスト"""
        op = OperatorAvailability(
            operator_name="test_op",
            available_slots={"morning", "afternoon"}
        )
        assert op.can_work_slot("morning")
        assert op.can_work_slot("afternoon")
        assert not op.can_work_slot("evening")
    
    def test_prefers_slot(self):
        """スロット好みチェックテスト"""
        op = OperatorAvailability(
            operator_name="test_op",
            available_slots={"morning", "afternoon"},
            preferred_slots={"morning"}
        )
        assert op.prefers_slot("morning")
        assert not op.prefers_slot("afternoon")

class TestDeskRequirement:
    """DeskRequirementクラスのテスト"""
    
    def test_desk_requirement_creation(self):
        """DeskRequirementの作成テスト"""
        desk_req = DeskRequirement(desk_name="Desk A")
        assert desk_req.desk_name == "Desk A"
        assert len(desk_req.slot_requirements) == 0
    
    def test_get_requirement_for_slot(self):
        """スロット要件取得テスト"""
        desk_req = DeskRequirement(desk_name="Desk A")
        desk_req.set_requirement_for_slot("morning", 2)
        desk_req.set_requirement_for_slot("afternoon", 3)
        
        assert desk_req.get_requirement_for_slot("morning") == 2
        assert desk_req.get_requirement_for_slot("afternoon") == 3
        assert desk_req.get_requirement_for_slot("evening") == 0  # デフォルト値

class TestAssignment:
    """Assignmentクラスのテスト"""
    
    def test_assignment_creation(self):
        """Assignmentの作成テスト"""
        date = datetime(2024, 1, 1)
        assignment = Assignment(
            operator_name="test_op",
            desk_name="Desk A",
            slot_id="morning",
            date=date
        )
        assert assignment.operator_name == "test_op"
        assert assignment.desk_name == "Desk A"
        assert assignment.slot_id == "morning"
        assert assignment.date == date
        assert assignment.assignment_type == "regular"
    
    def test_assignment_validation(self):
        """Assignmentの検証テスト"""
        date = datetime(2024, 1, 1)
        with pytest.raises(ValueError):
            Assignment("", "Desk A", "morning", date)
        
        with pytest.raises(ValueError):
            Assignment("test_op", "", "morning", date)
        
        with pytest.raises(ValueError):
            Assignment("test_op", "Desk A", "", date)

class TestMultiSlotScheduler:
    """MultiSlotSchedulerクラスのテスト"""
    
    def test_scheduler_creation(self):
        """MultiSlotSchedulerの作成テスト"""
        slots = create_default_slots()
        scheduler = MultiSlotScheduler(slots)
        assert len(scheduler.slots) == 4
        assert len(scheduler.slot_ids) == 4
    
    def test_create_daily_schedule(self):
        """日次スケジュール作成テスト"""
        slots = create_default_slots()
        scheduler = MultiSlotScheduler(slots)
        date = datetime(2024, 1, 1)
        
        daily_schedule = scheduler.create_daily_schedule(date)
        assert daily_schedule.date == date
        assert len(daily_schedule.slots) == 4
    
    def test_validate_assignments(self):
        """割り当て検証テスト"""
        slots = create_default_slots()
        scheduler = MultiSlotScheduler(slots)
        date = datetime(2024, 1, 1)
        
        # 正常な割り当て
        assignments = [
            Assignment("op1", "Desk A", "morning", date),
            Assignment("op2", "Desk B", "afternoon", date)
        ]
        errors = scheduler.validate_assignments(assignments)
        assert len(errors) == 0
        
        # 重複割り当て
        assignments = [
            Assignment("op1", "Desk A", "morning", date),
            Assignment("op1", "Desk B", "morning", date)  # 同じオペレータが同じスロットに重複
        ]
        errors = scheduler.validate_assignments(assignments)
        assert len(errors) > 0
    
    def test_calculate_work_hours(self):
        """労働時間計算テスト"""
        slots = create_default_slots()
        scheduler = MultiSlotScheduler(slots)
        date = datetime(2024, 1, 1)
        
        assignments = [
            Assignment("op1", "Desk A", "morning", date),   # 3時間
            Assignment("op1", "Desk A", "afternoon", date)  # 5時間
        ]
        
        total_hours = scheduler.calculate_work_hours(assignments, "op1", date)
        assert total_hours == 8.0

class TestUtilityFunctions:
    """ユーティリティ関数のテスト"""
    
    def test_create_default_slots(self):
        """デフォルトスロット作成テスト"""
        slots = create_default_slots()
        assert len(slots) == 4
        
        slot_ids = [slot.slot_id for slot in slots]
        assert "morning" in slot_ids
        assert "afternoon" in slot_ids
        assert "evening" in slot_ids
        assert "night" in slot_ids
    
    def test_convert_hourly_to_slots(self):
        """時間単位からスロット単位への変換テスト"""
        # テスト用の時間単位要件データを作成
        hourly_data = {
            "desk": ["Desk A", "Desk B"],
            "h09": [2, 1],
            "h10": [2, 1],
            "h11": [3, 2],
            "h12": [1, 1],
            "h13": [1, 1],
            "h14": [2, 2],
            "h15": [2, 2],
            "h16": [3, 1],
            "h17": [2, 1]
        }
        hourly_df = pd.DataFrame(hourly_data)
        
        desk_requirements = convert_hourly_to_slots(hourly_df)
        assert len(desk_requirements) == 2
        
        # Desk Aの要件をチェック
        desk_a = next(d for d in desk_requirements if d.desk_name == "Desk A")
        assert desk_a.get_requirement_for_slot("morning") == 3  # 最大値
        assert desk_a.get_requirement_for_slot("afternoon") == 3  # 最大値

class TestMultiSlotDAAlgorithm:
    """Multi-slot DAアルゴリズムのテスト"""
    
    def test_convert_legacy_operators_to_multi_slot(self):
        """従来オペレータデータの変換テスト"""
        legacy_ops = [
            {
                "name": "op1",
                "start": 9,
                "end": 17,
                "home": "Desk A",
                "desks": ["Desk A", "Desk B"]
            }
        ]
        
        operators = convert_legacy_operators_to_multi_slot(legacy_ops)
        assert len(operators) == 1
        
        op = operators[0]
        assert op.operator_name == "op1"
        assert "morning" in op.available_slots
        assert "afternoon" in op.available_slots
        assert "evening" not in op.available_slots
    
    def test_multi_slot_da_match(self):
        """Multi-slot DAマッチングテスト"""
        # テスト用データを作成
        hourly_data = {
            "desk": ["Desk A", "Desk B"],
            "h09": [1, 1],
            "h10": [1, 1],
            "h11": [1, 1],
            "h12": [1, 1],
            "h13": [1, 1],
            "h14": [1, 1],
            "h15": [1, 1],
            "h16": [1, 1],
            "h17": [1, 1]
        }
        hourly_df = pd.DataFrame(hourly_data)
        
        legacy_ops = [
            {
                "name": "op1",
                "start": 9,
                "end": 17,
                "home": "Desk A",
                "desks": ["Desk A", "Desk B"]
            },
            {
                "name": "op2",
                "start": 9,
                "end": 17,
                "home": "Desk B",
                "desks": ["Desk A", "Desk B"]
            }
        ]
        
        assignments, schedule_df = multi_slot_da_match(hourly_df, legacy_ops)
        
        # 結果の検証
        assert len(assignments) > 0
        assert isinstance(schedule_df, pd.DataFrame)
        assert len(schedule_df) == 2  # 2人のオペレータ

if __name__ == "__main__":
    pytest.main([__file__]) 