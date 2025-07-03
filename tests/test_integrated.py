#!/usr/bin/env python3
"""
統合テストスイート

重複を削除し、効率的なテストスイートとして統合されたテストファイルです。
以下のテストを含みます：
- 制約システム全体のテスト
- アルゴリズムのテスト
- CSV読み込みのテスト
- 統合シナリオのテスト
- Multi-slotモデルのテスト
"""

import sys
import os
import unittest
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO

# インポートエラーを回避するため、try-exceptで囲む
try:
    from src.models.constraints import (
        ConstraintType, Constraint, MinRestHoursConstraint, MaxConsecutiveDaysConstraint,
        MaxWeeklyHoursConstraint, MaxNightShiftsPerWeekConstraint, RequiredDayOffAfterNightConstraint,
        RequiredBreakAfterLongShiftConstraint, RequiredBreakAfterConsecutiveSlotsConstraint,
        ConstraintParser, ConstraintValidator, create_default_constraints, DEFAULT_CONSTRAINT_DSL
    )
    from src.models.multi_slot_models import (
        TimeSlot, DailySchedule, OperatorAvailability, DeskRequirement, 
        Assignment, MultiSlotScheduler, SlotType, create_default_slots, convert_hourly_to_slots
    )
    from src.algorithms.multi_slot_da_algorithm import (
        MultiSlotDAMatchingAlgorithm, convert_legacy_operators_to_multi_slot,
        multi_slot_da_match, convert_assignments_to_dataframe
    )
    from src.algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match
except ImportError as e:
    print(f"インポートエラー: {e}")
    print("srcディレクトリの構造を確認してください")


class TestConstraintSystem(unittest.TestCase):
    """制約システム全体のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.base_date = datetime(2024, 1, 1)
        self.operators = [
            OperatorAvailability(operator_name="田中"),
            OperatorAvailability(operator_name="佐藤")
        ]
    
    def test_constraint_types(self):
        """制約タイプのテスト"""
        self.assertEqual(ConstraintType.MIN_REST_HOURS.value, "min_rest_hours")
        self.assertEqual(ConstraintType.MAX_CONSECUTIVE_DAYS.value, "max_consecutive_days")
        self.assertEqual(ConstraintType.MAX_WEEKLY_HOURS.value, "max_weekly_hours")
        self.assertEqual(ConstraintType.MAX_NIGHT_SHIFTS_PER_WEEK.value, "max_night_shifts_per_week")
        self.assertEqual(ConstraintType.REQUIRED_DAY_OFF_AFTER_NIGHT.value, "required_day_off_after_night")
    
    def test_max_consecutive_days_constraint(self):
        """最大連勤日数制約のテスト"""
        constraint = MaxConsecutiveDaysConstraint(max_consecutive_days=3)
        
        # 有効な連勤日数
        assignments = []
        for i in range(3):
            assignments.append(Assignment("田中", "A", "morning", self.base_date + timedelta(days=i)))
        self.assertTrue(constraint.validate(assignments, self.operators))
        
        # 無効な連勤日数（4日連続）
        assignments.append(Assignment("田中", "A", "morning", self.base_date + timedelta(days=3)))
        self.assertFalse(constraint.validate(assignments, self.operators))
    
    def test_max_weekly_hours_constraint(self):
        """最大週間労働時間制約のテスト"""
        constraint = MaxWeeklyHoursConstraint(max_weekly_hours=40.0)
        
        # 有効な週間労働時間
        assignments = []
        for i in range(5):  # 5日間、各日8時間
            assignments.append(Assignment("田中", "A", "morning", self.base_date + timedelta(days=i)))
            assignments.append(Assignment("田中", "A", "afternoon", self.base_date + timedelta(days=i)))
        self.assertTrue(constraint.validate(assignments, self.operators))
        
        # 無効な週間労働時間（50時間）
        for i in range(5, 7):  # 追加で2日間
            assignments.append(Assignment("田中", "A", "morning", self.base_date + timedelta(days=i)))
            assignments.append(Assignment("田中", "A", "afternoon", self.base_date + timedelta(days=i)))
            assignments.append(Assignment("田中", "A", "evening", self.base_date + timedelta(days=i)))
        self.assertFalse(constraint.validate(assignments, self.operators))
    
    def test_max_night_shifts_per_week_constraint(self):
        """週間最大夜勤数制約のテスト"""
        constraint = MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=2)
        
        # 有効な夜勤数
        assignments = [
            Assignment("田中", "A", "night", self.base_date),
            Assignment("田中", "A", "night", self.base_date + timedelta(days=1))
        ]
        self.assertTrue(constraint.validate(assignments, self.operators))
        
        # 無効な夜勤数（3回）
        assignments.append(Assignment("田中", "A", "night", self.base_date + timedelta(days=2)))
        self.assertFalse(constraint.validate(assignments, self.operators))
    
    def test_break_constraints(self):
        """休憩制約のテスト"""
        # 長時間勤務後の休憩制約
        break_constraint = RequiredBreakAfterLongShiftConstraint(
            long_shift_threshold_hours=5.0,
            required_break_hours=1.0
        )
        
        # 連続スロット後の休憩制約
        consecutive_break_constraint = RequiredBreakAfterConsecutiveSlotsConstraint(
            max_consecutive_slots=5,
            break_desk_name="休憩"
        )
        
        # 5スロット連続勤務の後に休憩がない場合（制約違反）
        assignments = []
        for i in range(6):
            assignments.append(Assignment("田中", "Desk A", f"h{9+i:02d}", self.base_date))
        
        self.assertFalse(consecutive_break_constraint.validate(assignments, self.operators))
        
        # 5スロット連続勤務の後に休憩がある場合（制約遵守）
        assignments = []
        for i in range(5):
            assignments.append(Assignment("田中", "Desk A", f"h{9+i:02d}", self.base_date))
        assignments.append(Assignment("田中", "休憩", "h14", self.base_date))
        
        self.assertTrue(consecutive_break_constraint.validate(assignments, self.operators))


class TestMultiSlotModels(unittest.TestCase):
    """Multi-slotモデルのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.base_date = datetime(2024, 1, 1)
    
    def test_time_slot_creation(self):
        """TimeSlotの作成テスト"""
        slot = TimeSlot("h09", SlotType.HOUR_09, datetime.strptime("09:00", "%H:%M").time(), 
                       datetime.strptime("10:00", "%H:%M").time(), 1.0)
        self.assertEqual(slot.slot_id, "h09")
        self.assertEqual(slot.slot_type, SlotType.HOUR_09)
        self.assertEqual(slot.duration_hours, 1.0)
    
    def test_time_slot_validation(self):
        """TimeSlotの検証テスト"""
        with self.assertRaises(ValueError):
            TimeSlot("invalid", SlotType.HOUR_09, datetime.strptime("09:00", "%H:%M").time(), 
                    datetime.strptime("10:00", "%H:%M").time(), -1.0)
    
    def test_time_slot_overlap(self):
        """TimeSlotの重複チェックテスト"""
        slot1 = TimeSlot("h09", SlotType.HOUR_09, datetime.strptime("09:00", "%H:%M").time(), 
                        datetime.strptime("10:00", "%H:%M").time(), 1.0)
        slot2 = TimeSlot("h10", SlotType.HOUR_10, datetime.strptime("10:00", "%H:%M").time(), 
                        datetime.strptime("11:00", "%H:%M").time(), 1.0)
        slot3 = TimeSlot("h09_30", SlotType.HOUR_09, datetime.strptime("09:30", "%H:%M").time(), 
                        datetime.strptime("10:30", "%H:%M").time(), 1.0)
        
        self.assertFalse(slot1.overlaps_with(slot2))  # 重複しない
        self.assertTrue(slot1.overlaps_with(slot3))   # 重複する
        self.assertTrue(slot2.overlaps_with(slot3))   # 重複する
    
    def test_daily_schedule(self):
        """DailyScheduleのテスト"""
        schedule = DailySchedule(date=self.base_date)
        self.assertEqual(schedule.date, self.base_date)
        self.assertEqual(len(schedule.slots), 0)
        
        slot = TimeSlot("h09", SlotType.HOUR_09, datetime.strptime("09:00", "%H:%M").time(), 
                       datetime.strptime("10:00", "%H:%M").time(), 1.0)
        schedule.add_slot(slot)
        self.assertEqual(len(schedule.slots), 1)
        
        found_slot = schedule.get_slot_by_id("h09")
        self.assertEqual(found_slot, slot)
        
        not_found = schedule.get_slot_by_id("nonexistent")
        self.assertIsNone(not_found)
    
    def test_operator_availability(self):
        """OperatorAvailabilityのテスト"""
        op = OperatorAvailability(
            operator_name="test_op",
            available_slots={"h09", "h10"},
            preferred_slots={"h09"}
        )
        self.assertTrue(op.can_work_slot("h09"))
        self.assertTrue(op.prefers_slot("h09"))
        self.assertFalse(op.can_work_slot("h11"))
        self.assertFalse(op.prefers_slot("h10"))
    
    def test_desk_requirement(self):
        """DeskRequirementのテスト"""
        desk_req = DeskRequirement(desk_name="Desk A")
        self.assertEqual(desk_req.desk_name, "Desk A")
        self.assertEqual(len(desk_req.slot_requirements), 0)
        
        desk_req.set_requirement_for_slot("h09", 2)
        desk_req.set_requirement_for_slot("h10", 3)
        
        self.assertEqual(desk_req.get_requirement_for_slot("h09"), 2)
        self.assertEqual(desk_req.get_requirement_for_slot("h10"), 3)
        self.assertEqual(desk_req.get_requirement_for_slot("h11"), 0)  # デフォルト値
    
    def test_assignment_creation(self):
        """Assignmentの作成テスト"""
        assignment = Assignment("test_op", "Desk A", "h09", self.base_date)
        self.assertEqual(assignment.operator_name, "test_op")
        self.assertEqual(assignment.desk_name, "Desk A")
        self.assertEqual(assignment.slot_id, "h09")
        self.assertEqual(assignment.assignment_type, "regular")
    
    def test_assignment_validation(self):
        """Assignmentの検証テスト"""
        with self.assertRaises(ValueError):
            Assignment("", "Desk A", "h09", self.base_date)
        
        with self.assertRaises(ValueError):
            Assignment("test_op", "", "h09", self.base_date)
        
        with self.assertRaises(ValueError):
            Assignment("test_op", "Desk A", "", self.base_date)
    
    def test_multi_slot_scheduler(self):
        """MultiSlotSchedulerのテスト"""
        slots = create_default_slots()
        scheduler = MultiSlotScheduler(slots)
        self.assertEqual(len(scheduler.slots), 9)  # 9時から17時まで（9時間）
        self.assertEqual(len(scheduler.slot_ids), 9)
        
        daily_schedule = scheduler.create_daily_schedule(self.base_date)
        self.assertEqual(daily_schedule.date, self.base_date)
        self.assertEqual(len(daily_schedule.slots), 9)
        
        # 正常な割り当て
        assignments = [
            Assignment("op1", "Desk A", "h09", self.base_date),
            Assignment("op2", "Desk B", "h10", self.base_date)
        ]
        errors = scheduler.validate_assignments(assignments)
        self.assertEqual(len(errors), 0)
        
        # 重複割り当て
        assignments = [
            Assignment("op1", "Desk A", "h09", self.base_date),
            Assignment("op1", "Desk B", "h09", self.base_date)  # 同じオペレータが同じスロットに重複
        ]
        errors = scheduler.validate_assignments(assignments)
        self.assertGreater(len(errors), 0)
    
    def test_utility_functions(self):
        """ユーティリティ関数のテスト"""
        slots = create_default_slots()
        self.assertEqual(len(slots), 9)  # 9時から17時まで（9時間）
        
        slot_ids = [slot.slot_id for slot in slots]
        self.assertIn("h09", slot_ids)
        self.assertIn("h10", slot_ids)
        self.assertIn("h11", slot_ids)
        self.assertIn("h17", slot_ids)
        
        # 時間単位からスロット単位への変換テスト
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
        self.assertEqual(len(desk_requirements), 2)
        
        # Desk Aの要件をチェック
        desk_a = next(d for d in desk_requirements if d.desk_name == "Desk A")
        self.assertEqual(desk_a.get_requirement_for_slot("h09"), 2)
        self.assertEqual(desk_a.get_requirement_for_slot("h11"), 3)  # 最大値


class TestAlgorithms(unittest.TestCase):
    """アルゴリズムのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.base_date = datetime(2024, 1, 1)
        
        # デスク要件
        self.desks_data = {
            "desk": ["Desk A", "Desk B"],
            "h09": [1, 1],
            "h10": [1, 1],
            "h11": [1, 1],
            "h12": [0, 0],
            "h13": [0, 0],
            "h14": [0, 0],
            "h15": [0, 0],
            "h16": [0, 0],
            "h17": [0, 0]
        }
        self.hourly_requirements = pd.DataFrame(self.desks_data)
        
        # オペレーターデータ
        self.operators_data = [
            {
                "name": "Op1",
                "start": 9,
                "end": 12,
                "home": "Desk A",
                "desks": ["Desk A", "Desk B"]
            },
            {
                "name": "Op2",
                "start": 9,
                "end": 12,
                "home": "Desk B",
                "desks": ["Desk A", "Desk B"]
            }
        ]
    
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
        self.assertEqual(len(operators), 1)
        
        op = operators[0]
        self.assertEqual(op.operator_name, "op1")
        self.assertIn("h09", op.available_slots)
        self.assertIn("h10", op.available_slots)
        self.assertIn("h16", op.available_slots)  # 9-17時なので16時まで
        self.assertNotIn("h17", op.available_slots)  # 17時は含まれない
    
    def test_multi_slot_da_match(self):
        """Multi-slot DAアルゴリズムのテスト"""
        assignments, schedule = multi_slot_da_match(self.hourly_requirements, self.operators_data)
        
        self.assertIsInstance(assignments, list)
        self.assertIsInstance(schedule, pd.DataFrame)
        self.assertGreater(len(assignments), 0)
        
        # 各デスクの割り当て状況を確認
        for desk in self.hourly_requirements["desk"]:
            desk_assignments = [a for a in assignments if a.desk_name == desk]
            self.assertGreaterEqual(len(desk_assignments), 0)
    
    def test_constrained_multi_slot_da_match(self):
        """制約付きMulti-slot DAアルゴリズムのテスト"""
        constraints = [
            MaxConsecutiveDaysConstraint(max_consecutive_days=6),
            MaxWeeklyHoursConstraint(max_weekly_hours=40.0),
            MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=2),
            RequiredBreakAfterLongShiftConstraint(long_shift_threshold_hours=5.0, required_break_hours=1.0),
            RequiredBreakAfterConsecutiveSlotsConstraint(max_consecutive_slots=5, break_desk_name="休憩"),
        ]
        
        assignments, schedule = constrained_multi_slot_da_match(
            self.hourly_requirements, self.operators_data, constraints, self.base_date
        )
        
        self.assertIsInstance(assignments, list)
        self.assertIsInstance(schedule, pd.DataFrame)
        
        # 制約違反チェック
        validator = ConstraintValidator(constraints)
        violations = validator.get_violations(assignments, [])
        self.assertEqual(len(violations), 0, f"制約違反が検出されました: {violations}")


class TestCSVOperations(unittest.TestCase):
    """CSV操作のテスト"""
    
    def test_operator_csv_parsing(self):
        """オペレーターCSV解析のテスト"""
        test_csv_data = """name,start,end,home,desks
Op1,9,12,Desk A,"Desk A,Desk B"
Op2,9,12,Desk B,"Desk A,Desk B"
"""
        
        operators_df = pd.read_csv(StringIO(test_csv_data))
        
        # 必要な列の存在チェック
        required_columns = ["name", "start", "end", "home", "desks"]
        for col in required_columns:
            self.assertIn(col, operators_df.columns)
        
        # データの検証
        self.assertEqual(len(operators_df), 2)
        self.assertEqual(operators_df.iloc[0]["name"], "Op1")
        self.assertEqual(operators_df.iloc[0]["start"], 9)
        self.assertEqual(operators_df.iloc[0]["end"], 12)
    
    def test_csv_paths(self):
        """CSVファイルパスのテスト"""
        # 期待されるファイルパス
        expected_files = [
            "data/shifts/シフト表.csv",
            "data/operators/operators_default.csv"
        ]
        
        for file_path in expected_files:
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    self.assertIsInstance(df, pd.DataFrame)
                except Exception as e:
                    self.fail(f"CSVファイル読み込みエラー: {file_path} - {str(e)}")


class TestConstraintParser(unittest.TestCase):
    """制約パーサーのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.parser = ConstraintParser()
    
    def test_parse_max_consecutive_days(self):
        """最大連勤日数制約のパーステスト"""
        constraint_text = "max_consecutive_days: 6"
        constraints = self.parser.parse_constraints(constraint_text)
        self.assertEqual(len(constraints), 1)
        self.assertIsInstance(constraints[0], MaxConsecutiveDaysConstraint)
        if isinstance(constraints[0], MaxConsecutiveDaysConstraint):
            self.assertEqual(constraints[0].max_consecutive_days, 6)  # type: ignore
    
    def test_parse_multiple_constraints(self):
        """複数制約のパーステスト"""
        constraint_text = """
        max_consecutive_days: 6
        max_weekly_hours: 40.0
        """
        constraints = self.parser.parse_constraints(constraint_text)
        self.assertEqual(len(constraints), 2)
        constraint_types = [c.constraint_type for c in constraints]
        self.assertIn(ConstraintType.MAX_CONSECUTIVE_DAYS, constraint_types)
        self.assertIn(ConstraintType.MAX_WEEKLY_HOURS, constraint_types)


class TestConstraintValidator(unittest.TestCase):
    """制約検証器のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.base_date = datetime(2024, 1, 1)
        self.operators = [
            OperatorAvailability(operator_name="田中"),
            OperatorAvailability(operator_name="佐藤")
        ]
        self.constraints = [
            MaxConsecutiveDaysConstraint(max_consecutive_days=6),
            MaxWeeklyHoursConstraint(max_weekly_hours=40.0),
            MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=2),
            RequiredBreakAfterLongShiftConstraint(long_shift_threshold_hours=5.0, required_break_hours=1.0),
            RequiredBreakAfterConsecutiveSlotsConstraint(max_consecutive_slots=5, break_desk_name="休憩"),
        ]
        self.validator = ConstraintValidator(self.constraints)
    
    def test_validate_all_valid(self):
        """すべて有効な割り当てのテスト"""
        assignments = [
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="afternoon",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="evening",
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
                slot_id="afternoon",
                date=self.base_date
            ),
            Assignment(
                operator_name="田中",
                desk_name="A",
                slot_id="evening",
                date=self.base_date + timedelta(days=1)
            )
        ]
        violations = self.validator.get_violations(assignments, self.operators)
        self.assertEqual(len(violations), 0)


class TestDefaultConstraints(unittest.TestCase):
    """デフォルト制約のテスト"""
    
    def test_create_default_constraints(self):
        """デフォルト制約セットの作成テスト"""
        constraints = create_default_constraints()
        self.assertEqual(len(constraints), 5)  # 5件に修正
        self.assertIsInstance(constraints[0], MaxConsecutiveDaysConstraint)
        self.assertIsInstance(constraints[1], MaxWeeklyHoursConstraint)
        self.assertIsInstance(constraints[2], MaxNightShiftsPerWeekConstraint)
        self.assertIsInstance(constraints[3], RequiredBreakAfterLongShiftConstraint)
        self.assertIsInstance(constraints[4], RequiredBreakAfterConsecutiveSlotsConstraint)
    
    def test_default_constraint_dsl(self):
        """デフォルト制約DSLのテスト"""
        parser = ConstraintParser()
        constraints = parser.parse_constraints(DEFAULT_CONSTRAINT_DSL)
        self.assertEqual(len(constraints), 3)  # 3件に修正
        self.assertIsInstance(constraints[0], MaxConsecutiveDaysConstraint)
        self.assertIsInstance(constraints[1], MaxWeeklyHoursConstraint)
        self.assertIsInstance(constraints[2], MaxNightShiftsPerWeekConstraint)


class TestIntegrationScenarios(unittest.TestCase):
    """統合シナリオのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.base_date = datetime(2024, 1, 1)
        
        # より大きなテストデータ
        self.desks_data = {
            "desk": ["Desk A", "Desk B", "Desk C", "Desk D"],
            "h09": [2, 2, 1, 1],
            "h10": [2, 2, 1, 1],
            "h11": [2, 2, 1, 1],
            "h12": [1, 1, 1, 1],
            "h13": [1, 1, 1, 1],
            "h14": [1, 1, 1, 1],
            "h15": [1, 1, 1, 1],
            "h16": [1, 1, 1, 1],
            "h17": [1, 1, 1, 1]
        }
        self.hourly_requirements = pd.DataFrame(self.desks_data)
        
        self.operators_data = [
            {"name": f"Op{i}", "start": 9, "end": 17, "home": f"Desk {chr(65+i%4)}", 
             "desks": ["Desk A", "Desk B", "Desk C", "Desk D"]}
            for i in range(1, 9)  # 8人のオペレーター
        ]
    
    def test_5day_shift_generation(self):
        """5日分シフト生成のテスト"""
        constraints = create_default_constraints()
        all_assignments = []
        
        for day in range(5):
            current_date = self.base_date + timedelta(days=day)
            assignments, schedule = constrained_multi_slot_da_match(
                self.hourly_requirements, self.operators_data, constraints, current_date
            )
            all_assignments.extend(assignments)
        
        # 検証
        self.assertGreater(len(all_assignments), 0)
        
        # 制約違反チェック
        validator = ConstraintValidator(constraints)
        violations = validator.get_violations(all_assignments, [])
        self.assertEqual(len(violations), 0, f"制約違反が検出されました: {violations}")
    
    def test_constraint_parser(self):
        """制約パーサーのテスト"""
        dsl_text = """
        max_consecutive_days: 6
        max_weekly_hours: 40.0
        """
        
        parser = ConstraintParser()
        constraints = parser.parse_constraints(dsl_text)
        
        self.assertGreater(len(constraints), 0)
        
        # 制約タイプの確認
        constraint_types = [c.constraint_type for c in constraints]
        self.assertIn(ConstraintType.MAX_CONSECUTIVE_DAYS, constraint_types)
        self.assertIn(ConstraintType.MAX_WEEKLY_HOURS, constraint_types)


def run_all_tests():
    """すべてのテストを実行"""
    print("🧪 統合テストスイート開始")
    print("=" * 60)
    
    # テストスイートを作成
    test_suite = unittest.TestSuite()
    
    # 各テストクラスを追加
    test_classes = [
        TestConstraintSystem,
        TestMultiSlotModels,
        TestAlgorithms,
        TestCSVOperations,
        TestConstraintParser,
        TestConstraintValidator,
        TestDefaultConstraints,
        TestIntegrationScenarios
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # テストを実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print(f"  実行テスト数: {result.testsRun}")
    print(f"  成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失敗: {len(result.failures)}")
    print(f"  エラー: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失敗したテスト:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback}")
    
    if result.errors:
        print("\n❌ エラーが発生したテスト:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ すべてのテストが成功しました!")
    else:
        print("\n⚠️ 一部のテストが失敗しました")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 