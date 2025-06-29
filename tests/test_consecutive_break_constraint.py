#!/usr/bin/env python3
"""
連続スロット後の必須休憩制約のテスト

5スロット連続で働いたオペレータが次のスロットで休憩デスクにアサインされる制約の動作を確認します。
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import unittest

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.constraints import RequiredBreakAfterConsecutiveSlotsConstraint
from models.multi_slot_models import Assignment, OperatorAvailability
from algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match


class TestConsecutiveBreakConstraint(unittest.TestCase):
    """連続スロット後の必須休憩制約のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.base_date = datetime(2024, 1, 1)
        self.operators = [
            OperatorAvailability(operator_name="Op1"),
            OperatorAvailability(operator_name="Op2")
        ]
    
    def test_consecutive_break_constraint_validation(self):
        """連続スロット後の必須休憩制約の検証テスト"""
        constraint = RequiredBreakAfterConsecutiveSlotsConstraint(
            max_consecutive_slots=5,
            break_desk_name="休憩"
        )
        
        # 5スロット連続勤務の後に休憩がない場合（制約違反）
        assignments = []
        for i in range(6):  # 6スロット連続勤務
            assignment = Assignment(
                operator_name="Op1",
                desk_name="Desk A",
                slot_id=f"h{9+i:02d}",
                date=self.base_date
            )
            assignments.append(assignment)
        
        # 制約違反をチェック
        self.assertFalse(constraint.validate(assignments, self.operators))
        
        # 5スロット連続勤務の後に休憩がある場合（制約遵守）
        assignments = []
        for i in range(5):  # 5スロット連続勤務
            assignment = Assignment(
                operator_name="Op1",
                desk_name="Desk A",
                slot_id=f"h{9+i:02d}",
                date=self.base_date
            )
            assignments.append(assignment)
        
        # 6番目のスロットで休憩
        break_assignment = Assignment(
            operator_name="Op1",
            desk_name="休憩",
            slot_id="h14",
            date=self.base_date
        )
        assignments.append(break_assignment)
        
        # 制約遵守をチェック
        self.assertTrue(constraint.validate(assignments, self.operators))
    
    def test_required_break_assignments_generation(self):
        """必要な休憩割り当ての生成テスト"""
        constraint = RequiredBreakAfterConsecutiveSlotsConstraint(
            max_consecutive_slots=5,
            break_desk_name="休憩"
        )
        
        # 5スロット連続勤務の後に通常のスロットがある場合
        assignments = []
        for i in range(5):  # 5スロット連続勤務
            assignment = Assignment(
                operator_name="Op1",
                desk_name="Desk A",
                slot_id=f"h{9+i:02d}",
                date=self.base_date
            )
            assignments.append(assignment)
        
        # 6番目のスロットで通常のデスクに割り当て
        next_assignment = Assignment(
            operator_name="Op1",
            desk_name="Desk B",
            slot_id="h14",
            date=self.base_date
        )
        assignments.append(next_assignment)
        
        # 必要な休憩割り当てを取得
        break_assignments = constraint.get_required_break_assignments(assignments, self.operators)
        
        # 休憩割り当てが生成されることを確認
        self.assertEqual(len(break_assignments), 1)
        self.assertEqual(break_assignments[0]['operator_name'], "Op1")
        self.assertEqual(break_assignments[0]['slot_id'], "h14")
        self.assertEqual(break_assignments[0]['desk_name'], "休憩")
        self.assertEqual(break_assignments[0]['date'], self.base_date)
        self.assertIn("連続5スロット後の必須休憩", break_assignments[0]['reason'])
    
    def test_consecutive_count_reset_after_break(self):
        """休憩後の連続カウントリセットテスト"""
        constraint = RequiredBreakAfterConsecutiveSlotsConstraint(
            max_consecutive_slots=5,
            break_desk_name="休憩"
        )
        
        # 5スロット連続勤務 → 休憩 → 5スロット連続勤務（制約遵守）
        assignments = []
        
        # 最初の5スロット連続勤務
        for i in range(5):
            assignment = Assignment(
                operator_name="Op1",
                desk_name="Desk A",
                slot_id=f"h{9+i:02d}",
                date=self.base_date
            )
            assignments.append(assignment)
        
        # 休憩
        break_assignment = Assignment(
            operator_name="Op1",
            desk_name="休憩",
            slot_id="h14",
            date=self.base_date
        )
        assignments.append(break_assignment)
        
        # 次の5スロット連続勤務
        for i in range(5):
            assignment = Assignment(
                operator_name="Op1",
                desk_name="Desk A",
                slot_id=f"h{14+i+1:02d}",
                date=self.base_date
            )
            assignments.append(assignment)
        
        # 制約遵守をチェック
        self.assertTrue(constraint.validate(assignments, self.operators))

    def test_assign_after_break_is_allowed(self):
        """休憩後に同じデスク・異なるデスクにアサインできることのテスト"""
        constraint = RequiredBreakAfterConsecutiveSlotsConstraint(
            max_consecutive_slots=3,
            break_desk_name="休憩"
        )
        # 3スロット連続勤務→休憩→同じデスク
        assignments = []
        for i in range(3):
            assignments.append(Assignment(
                operator_name="Op1",
                desk_name="Desk A",
                slot_id=f"h{9+i:02d}",
                date=self.base_date
            ))
        assignments.append(Assignment(
            operator_name="Op1",
            desk_name="休憩",
            slot_id="h12",
            date=self.base_date
        ))
        assignments.append(Assignment(
            operator_name="Op1",
            desk_name="Desk A",
            slot_id="h13",
            date=self.base_date
        ))
        # 制約遵守をチェック
        self.assertTrue(constraint.validate(assignments, self.operators))

        # 3スロット連続勤務→休憩→異なるデスク
        assignments = []
        for i in range(3):
            assignments.append(Assignment(
                operator_name="Op1",
                desk_name="Desk A",
                slot_id=f"h{9+i:02d}",
                date=self.base_date
            ))
        assignments.append(Assignment(
            operator_name="Op1",
            desk_name="休憩",
            slot_id="h12",
            date=self.base_date
        ))
        assignments.append(Assignment(
            operator_name="Op1",
            desk_name="Desk B",
            slot_id="h13",
            date=self.base_date
        ))
        # 制約遵守をチェック
        self.assertTrue(constraint.validate(assignments, self.operators))


def test_consecutive_break_integration():
    """連続スロット後の必須休憩制約の統合テスト"""
    print("🧪 連続スロット後の必須休憩制約の統合テストを開始します")
    
    # テスト用のデスク要員数データ
    req_data = {
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
    req_df = pd.DataFrame(req_data)
    
    # テスト用のオペレーターデータ（長時間勤務するオペレーター）
    ops_data = [
        {
            "name": "Op1",
            "start": 9,
            "end": 17,
            "home": "Desk A",
            "desks": "Desk A,Desk B"
        },
        {
            "name": "Op2", 
            "start": 9,
            "end": 17,
            "home": "Desk B",
            "desks": "Desk A,Desk B"
        }
    ]
    
    # 連続スロット後の必須休憩制約を作成
    from models.constraints import RequiredBreakAfterConsecutiveSlotsConstraint
    consecutive_break_constraint = RequiredBreakAfterConsecutiveSlotsConstraint(
        max_consecutive_slots=5,
        break_desk_name="休憩"
    )
    
    print(f"📋 制約設定:")
    print(f"  • 最大連続スロット数: {consecutive_break_constraint.max_consecutive_slots}")
    print(f"  • 休憩デスク名: {consecutive_break_constraint.break_desk_name}")
    
    # 制約付きアルゴリズムでマッチング実行
    assignments, schedule = constrained_multi_slot_da_match(
        hourly_requirements=req_df,
        legacy_ops=ops_data,
        constraints=[consecutive_break_constraint],
        target_date=datetime.now()
    )
    
    print(f"📊 割り当て結果:")
    print(f"  • 総割り当て数: {len(assignments)}")
    
    # 休憩割り当てを確認
    break_assignments = [a for a in assignments if a.desk_name == "休憩"]
    print(f"  • 休憩割り当て数: {len(break_assignments)}")
    
    for break_assignment in break_assignments:
        print(f"    - {break_assignment.operator_name}: {break_assignment.slot_id} ({break_assignment.date.strftime('%Y-%m-%d')})")
    
    print(f"📋 シフト表:")
    print(schedule)
    
    print("✅ 連続スロット後の必須休憩制約の統合テストが完了しました")


if __name__ == "__main__":
    # ユニットテストを実行
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # 統合テストを実行
    test_consecutive_break_integration() 