"""
制約システムのユニットテスト

このモジュールは、Hard Constraint DSLの機能をテストします。
"""

import unittest
from datetime import datetime, timedelta
from typing import List

from ..models.constraints import (
    ConstraintType,
    Constraint,
    MinRestHoursConstraint,
    MaxConsecutiveDaysConstraint,
    MaxWeeklyHoursConstraint,
    MaxNightShiftsPerWeekConstraint,
    RequiredDayOffAfterNightConstraint,
    ConstraintParser,
    ConstraintValidator,
    create_default_constraints,
    DEFAULT_CONSTRAINT_DSL
)
from ..models.multi_slot_models import Assignment, OperatorAvailability

class TestConstraintTypes(unittest.TestCase):
    """制約タイプのテスト"""
    
    def test_constraint_type_values(self):
        """制約タイプの値が正しく設定されているかテスト"""
        self.assertEqual(ConstraintType.MIN_REST_HOURS.value, "min_rest_hours")
        self.assertEqual(ConstraintType.MAX_CONSECUTIVE_DAYS.value, "max_consecutive_days")
        self.assertEqual(ConstraintType.MAX_WEEKLY_HOURS.value, "max_weekly_hours")
        self.assertEqual(ConstraintType.MAX_NIGHT_SHIFTS_PER_WEEK.value, "max_night_shifts_per_week")
        self.assertEqual(ConstraintType.REQUIRED_DAY_OFF_AFTER_NIGHT.value, "required_day_off_after_night")

class TestMinRestHoursConstraint(unittest.TestCase):
    """最小休息時間制約のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.constraint = MinRestHoursConstraint(min_rest_hours=11.0)
        self.base_date = datetime(2024, 1, 1)
        
        # テスト用オペレーター
        self.operators = [
            OperatorAvailability(
                operator_name="田中",
                available_slots={"morning", "afternoon", "evening", "night"},
                preferred_slots=set(),
                max_work_hours_per_day=8.0,
                min_rest_hours_between_shifts=11.0
            )
        ]
    
    def test_valid_rest_hours(self):
        """有効な休息時間のテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=1)
            )
        ]
        
        self.assertTrue(self.constraint.validate(assignments, self.operators))
    
    def test_invalid_rest_hours(self):
        """無効な休息時間のテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date + timedelta(days=1)
            )
        ]
        
        # 夜勤後の朝勤務は休息時間が不足
        self.assertFalse(self.constraint.validate(assignments, self.operators))
    
    def test_non_consecutive_days(self):
        """連続しない日のテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="afternoon",
                date=self.base_date + timedelta(days=2)  # 1日空ける
            )
        ]
        
        self.assertTrue(self.constraint.validate(assignments, self.operators))

class TestMaxConsecutiveDaysConstraint(unittest.TestCase):
    """最大連勤日数制約のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.constraint = MaxConsecutiveDaysConstraint(max_consecutive_days=3)
        self.base_date = datetime(2024, 1, 1)
        
        self.operators = [
            OperatorAvailability(
                operator_name="田中",
                available_slots={"morning", "afternoon", "evening", "night"},
                preferred_slots=set(),
                max_work_hours_per_day=8.0,
                min_rest_hours_between_shifts=11.0
            )
        ]
    
    def test_valid_consecutive_days(self):
        """有効な連勤日数のテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="afternoon",
                date=self.base_date + timedelta(days=1)
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="evening",
                date=self.base_date + timedelta(days=2)
            )
        ]
        
        self.assertTrue(self.constraint.validate(assignments, self.operators))
    
    def test_invalid_consecutive_days(self):
        """無効な連勤日数のテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="afternoon",
                date=self.base_date + timedelta(days=1)
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="evening",
                date=self.base_date + timedelta(days=2)
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=3)
            )
        ]
        
        # 4日連続は制約違反
        self.assertFalse(self.constraint.validate(assignments, self.operators))

class TestMaxWeeklyHoursConstraint(unittest.TestCase):
    """最大週間労働時間制約のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.constraint = MaxWeeklyHoursConstraint(max_weekly_hours=40.0)
        self.base_date = datetime(2024, 1, 1)  # 月曜日
        
        self.operators = [
            OperatorAvailability(
                operator_name="田中",
                available_slots={"morning", "afternoon", "evening", "night"},
                preferred_slots=set(),
                max_work_hours_per_day=8.0,
                min_rest_hours_between_shifts=11.0
            )
        ]
    
    def test_valid_weekly_hours(self):
        """有効な週間労働時間のテスト"""
        assignments = [
            # 月曜日: morning(3h) + afternoon(5h) = 8h
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="afternoon",
                date=self.base_date
            ),
            # 火曜日: evening(4h) = 4h
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="evening",
                date=self.base_date + timedelta(days=1)
            ),
            # 水曜日: night(12h) = 12h
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=2)
            )
        ]
        
        # 合計: 8 + 4 + 12 = 24時間（40時間以下）
        self.assertTrue(self.constraint.validate(assignments, self.operators))
    
    def test_invalid_weekly_hours(self):
        """無効な週間労働時間のテスト"""
        assignments = [
            # 毎日night(12h)を5日間 = 60時間（40時間超過）
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=1)
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=2)
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=3)
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=4)
            )
        ]
        
        self.assertFalse(self.constraint.validate(assignments, self.operators))

class TestMaxNightShiftsPerWeekConstraint(unittest.TestCase):
    """週間最大夜勤数制約のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.constraint = MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=2)
        self.base_date = datetime(2024, 1, 1)  # 月曜日
        
        self.operators = [
            OperatorAvailability(
                operator_name="田中",
                available_slots={"morning", "afternoon", "evening", "night"},
                preferred_slots=set(),
                max_work_hours_per_day=8.0,
                min_rest_hours_between_shifts=11.0
            )
        ]
    
    def test_valid_night_shifts(self):
        """有効な夜勤数のテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=1)
            )
        ]
        
        self.assertTrue(self.constraint.validate(assignments, self.operators))
    
    def test_invalid_night_shifts(self):
        """無効な夜勤数のテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=1)
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=2)
            )
        ]
        
        # 3回の夜勤は制約違反
        self.assertFalse(self.constraint.validate(assignments, self.operators))

class TestRequiredDayOffAfterNightConstraint(unittest.TestCase):
    """夜勤後の必須休日制約のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.constraint = RequiredDayOffAfterNightConstraint()
        self.base_date = datetime(2024, 1, 1)
        
        self.operators = [
            OperatorAvailability(
                operator_name="田中",
                available_slots={"morning", "afternoon", "evening", "night"},
                preferred_slots=set(),
                max_work_hours_per_day=8.0,
                min_rest_hours_between_shifts=11.0
            )
        ]
    
    def test_valid_day_off_after_night(self):
        """有効な夜勤後の休日のテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date
            ),
            # 翌日は休日（割り当てなし）
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date + timedelta(days=2)  # 2日後
            )
        ]
        
        self.assertTrue(self.constraint.validate(assignments, self.operators))
    
    def test_invalid_day_off_after_night(self):
        """無効な夜勤後の休日のテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date + timedelta(days=1)  # 翌日
            )
        ]
        
        # 夜勤の翌日に勤務があるのは制約違反
        self.assertFalse(self.constraint.validate(assignments, self.operators))

class TestConstraintParser(unittest.TestCase):
    """制約パーサーのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.parser = ConstraintParser()
    
    def test_parse_min_rest_hours(self):
        """最小休息時間のパーステスト"""
        constraint_text = "min_rest_hours = 10.5"
        constraints = self.parser.parse_constraints(constraint_text)
        
        self.assertEqual(len(constraints), 1)
        self.assertIsInstance(constraints[0], MinRestHoursConstraint)
        if isinstance(constraints[0], MinRestHoursConstraint):
            self.assertEqual(constraints[0].min_rest_hours, 10.5)
    
    def test_parse_max_consecutive_days(self):
        """最大連勤日数のパーステスト"""
        constraint_text = "max_consecutive_days = 5"
        constraints = self.parser.parse_constraints(constraint_text)
        
        self.assertEqual(len(constraints), 1)
        self.assertIsInstance(constraints[0], MaxConsecutiveDaysConstraint)
        if isinstance(constraints[0], MaxConsecutiveDaysConstraint):
            self.assertEqual(constraints[0].max_consecutive_days, 5)
    
    def test_parse_max_weekly_hours(self):
        """最大週間労働時間のパーステスト"""
        constraint_text = "max_weekly_hours = 35.0"
        constraints = self.parser.parse_constraints(constraint_text)
        
        self.assertEqual(len(constraints), 1)
        self.assertIsInstance(constraints[0], MaxWeeklyHoursConstraint)
        if isinstance(constraints[0], MaxWeeklyHoursConstraint):
            self.assertEqual(constraints[0].max_weekly_hours, 35.0)
    
    def test_parse_max_night_shifts(self):
        """週間最大夜勤数のパーステスト"""
        constraint_text = "max_night_shifts_per_week = 3"
        constraints = self.parser.parse_constraints(constraint_text)
        
        self.assertEqual(len(constraints), 1)
        self.assertIsInstance(constraints[0], MaxNightShiftsPerWeekConstraint)
        if isinstance(constraints[0], MaxNightShiftsPerWeekConstraint):
            self.assertEqual(constraints[0].max_night_shifts_per_week, 3)
    
    def test_parse_required_day_off_after_night(self):
        """夜勤後の必須休日のパーステスト"""
        constraint_text = "required_day_off_after_night"
        constraints = self.parser.parse_constraints(constraint_text)
        
        self.assertEqual(len(constraints), 1)
        self.assertIsInstance(constraints[0], RequiredDayOffAfterNightConstraint)
    
    def test_parse_multiple_constraints(self):
        """複数制約のパーステスト"""
        constraint_text = """
        min_rest_hours = 11.0
        max_consecutive_days = 6
        max_weekly_hours = 40.0
        max_night_shifts_per_week = 2
        required_day_off_after_night
        """
        constraints = self.parser.parse_constraints(constraint_text)
        
        self.assertEqual(len(constraints), 5)
        self.assertIsInstance(constraints[0], MinRestHoursConstraint)
        self.assertIsInstance(constraints[1], MaxConsecutiveDaysConstraint)
        self.assertIsInstance(constraints[2], MaxWeeklyHoursConstraint)
        self.assertIsInstance(constraints[3], MaxNightShiftsPerWeekConstraint)
        self.assertIsInstance(constraints[4], RequiredDayOffAfterNightConstraint)
    
    def test_parse_with_comments(self):
        """コメント付き制約のパーステスト"""
        constraint_text = """
        # これはコメントです
        min_rest_hours = 11.0
        # これもコメント
        max_consecutive_days = 6
        """
        constraints = self.parser.parse_constraints(constraint_text)
        
        self.assertEqual(len(constraints), 2)
        self.assertIsInstance(constraints[0], MinRestHoursConstraint)
        self.assertIsInstance(constraints[1], MaxConsecutiveDaysConstraint)

class TestConstraintValidator(unittest.TestCase):
    """制約バリデーターのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.constraints = [
            MinRestHoursConstraint(min_rest_hours=11.0),
            MaxConsecutiveDaysConstraint(max_consecutive_days=3),
            MaxWeeklyHoursConstraint(max_weekly_hours=40.0),
            MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=2),
            RequiredDayOffAfterNightConstraint(),
        ]
        self.validator = ConstraintValidator(self.constraints)
        
        self.base_date = datetime(2024, 1, 1)
        self.operators = [
            OperatorAvailability(
                operator_name="田中",
                available_slots={"morning", "afternoon", "evening", "night"},
                preferred_slots=set(),
                max_work_hours_per_day=8.0,
                min_rest_hours_between_shifts=11.0
            )
        ]
    
    def test_validate_all_valid(self):
        """全て有効な制約のテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date + timedelta(days=1)
            )
        ]
        
        results = self.validator.validate_all(assignments, self.operators)
        
        self.assertTrue(all(results.values()))
        self.assertEqual(len(results), 5)
    
    def test_get_violations(self):
        """違反制約の取得テスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date + timedelta(days=1)
            )
        ]
        
        violations = self.validator.get_violations(assignments, self.operators)
        
        # 夜勤後の必須休日制約に違反
        self.assertIn("required_day_off_after_night", violations)
    
    def test_calculate_total_violation_score(self):
        """総違反スコアの計算テスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="night",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="morning",
                date=self.base_date + timedelta(days=1)
            )
        ]
        
        score = self.validator.calculate_total_violation_score(assignments, self.operators)
        
        # 少なくとも1つの制約に違反しているため、スコアは0より大きい
        self.assertGreater(score, 0.0)

class TestDefaultConstraints(unittest.TestCase):
    """デフォルト制約のテスト"""
    
    def test_create_default_constraints(self):
        """デフォルト制約セットの作成テスト"""
        constraints = create_default_constraints()
        
        self.assertEqual(len(constraints), 5)
        self.assertIsInstance(constraints[0], MinRestHoursConstraint)
        self.assertIsInstance(constraints[1], MaxConsecutiveDaysConstraint)
        self.assertIsInstance(constraints[2], MaxWeeklyHoursConstraint)
        self.assertIsInstance(constraints[3], MaxNightShiftsPerWeekConstraint)
        self.assertIsInstance(constraints[4], RequiredDayOffAfterNightConstraint)
    
    def test_default_constraint_dsl(self):
        """デフォルト制約DSLのテスト"""
        parser = ConstraintParser()
        constraints = parser.parse_constraints(DEFAULT_CONSTRAINT_DSL)
        
        self.assertEqual(len(constraints), 5)
        self.assertIsInstance(constraints[0], MinRestHoursConstraint)
        self.assertIsInstance(constraints[1], MaxConsecutiveDaysConstraint)
        self.assertIsInstance(constraints[2], MaxWeeklyHoursConstraint)
        self.assertIsInstance(constraints[3], MaxNightShiftsPerWeekConstraint)
        self.assertIsInstance(constraints[4], RequiredDayOffAfterNightConstraint)

if __name__ == '__main__':
    unittest.main() 