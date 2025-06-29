#!/usr/bin/env python3
"""
制約付きMulti-slot DAアルゴリズムのテスト

制約付きMulti-slot DAアルゴリズムの動作をテストします。
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match
from models.constraints import (
    MinRestHoursConstraint, MaxConsecutiveDaysConstraint,
    MaxWeeklyHoursConstraint, MaxNightShiftsPerWeekConstraint,
    RequiredDayOffAfterNightConstraint
)

def test_constrained_algorithm():
    """制約付きアルゴリズムの基本テスト"""
    print("🧪 制約付きMulti-slot DAアルゴリズム テスト開始")
    print("=" * 60)
    
    # テストデータ作成
    print("📊 テストデータ作成中...")
    
    # デスク要件（3時間分）
    desks_data = {
        "desk": ["Desk A", "Desk B"],
        "h09": [1, 1],  # 9時: 各デスク1人必要
        "h10": [1, 1],  # 10時: 各デスク1人必要
        "h11": [1, 1],  # 11時: 各デスク1人必要
        "h12": [0, 0],  # 12時以降は0
        "h13": [0, 0],
        "h14": [0, 0],
        "h15": [0, 0],
        "h16": [0, 0],
        "h17": [0, 0]
    }
    
    hourly_requirements = pd.DataFrame(desks_data)
    print("デスク要件:")
    print(hourly_requirements)
    print()
    
    # オペレーターデータ（2人）
    operators_data = [
        {
            "name": "Op1",
            "start": 9,
            "end": 12,  # 3時間勤務
            "home": "Desk A",
            "desks": ["Desk A", "Desk B"]
        },
        {
            "name": "Op2", 
            "start": 9,
            "end": 12,  # 3時間勤務
            "home": "Desk B",
            "desks": ["Desk A", "Desk B"]
        }
    ]
    
    print("オペレーターデータ:")
    for op in operators_data:
        print(f"  {op['name']}: {op['start']}時-{op['end']}時, 所属: {op['home']}, 対応: {op['desks']}")
    print()
    
    # 制約の設定
    print("🔒 制約設定:")
    constraints = [
        MinRestHoursConstraint(min_rest_hours=11.0),
        MaxConsecutiveDaysConstraint(max_consecutive_days=6),
        MaxWeeklyHoursConstraint(max_weekly_hours=40.0),
        MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=2),
        RequiredDayOffAfterNightConstraint()
    ]
    
    for constraint in constraints:
        print(f"  • {constraint.description}")
    print()
    
    # 制約付きMulti-slot DAアルゴリズム実行
    print("🚀 制約付きMulti-slot DAアルゴリズム実行中...")
    try:
        assignments, schedule_df = constrained_multi_slot_da_match(
            hourly_requirements, operators_data, constraints
        )
        
        print("✅ アルゴリズム実行成功!")
        print()
        
        # 結果表示
        print("📋 割り当て結果:")
        for assignment in assignments:
            print(f"  {assignment.operator_name} → {assignment.desk_name} ({assignment.slot_id})")
        print()
        
        print("📅 スケジュール表:")
        print(schedule_df)
        print()
        
        # 制約違反チェック
        print("🔍 制約違反チェック:")
        from models.constraints import ConstraintValidator
        validator = ConstraintValidator(constraints)
        violations = validator.get_violations(assignments, [])
        
        if violations:
            print("⚠️ 制約違反が検出されました:")
            for violation in violations:
                print(f"  • {violation}")
        else:
            print("✅ すべての制約を満たしています")
        print()
        
        # 検証
        print("📊 結果検証:")
        print(f"  割り当て数: {len(assignments)}")
        print(f"  オペレーター数: {len(operators_data)}")
        print(f"  デスク数: {len(hourly_requirements)}")
        print(f"  制約数: {len(constraints)}")
        
        # 各デスクの割り当て状況を確認
        for desk in hourly_requirements["desk"]:
            desk_assignments = [a for a in assignments if a.desk_name == desk]
            print(f"  {desk}: {len(desk_assignments)}人割り当て")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        print("詳細なエラー情報:")
        print(traceback.format_exc())

def test_constraint_violations():
    """制約違反のテスト"""
    print("\n🔒 制約違反テスト")
    print("=" * 40)
    
    # 連続勤務のテストデータ
    test_date = datetime.now()
    
    # 制約に違反する割り当てを作成（連続7日勤務）
    from models.multi_slot_models import Assignment
    
    assignments = []
    for i in range(7):  # 7日連続勤務
        assignment = Assignment(
            operator_name="TestOp",
            desk_name="Desk A",
            slot_id="morning",
            date=test_date + timedelta(days=i)
        )
        assignments.append(assignment)
    
    # 制約チェック
    constraint = MaxConsecutiveDaysConstraint(max_consecutive_days=6)
    is_valid = constraint.validate(assignments, [])
    
    print(f"連続7日勤務の制約チェック: {'❌ 違反' if not is_valid else '✅ 適合'}")
    print(f"期待結果: ❌ 違反 (6日制限に対して7日)")
    
    # 最小休息時間のテスト
    rest_constraint = MinRestHoursConstraint(min_rest_hours=11.0)
    
    # 休息時間が不足する割り当て（夜勤後の朝勤務）
    night_assignment = Assignment(
        operator_name="TestOp",
        desk_name="Desk A",
        slot_id="night",
        date=test_date
    )
    
    morning_assignment = Assignment(
        operator_name="TestOp",
        desk_name="Desk A",
        slot_id="morning",
        date=test_date + timedelta(days=1)
    )
    
    rest_assignments = [night_assignment, morning_assignment]
    rest_is_valid = rest_constraint.validate(rest_assignments, [])
    
    print(f"夜勤後の朝勤務の制約チェック: {'❌ 違反' if not rest_is_valid else '✅ 適合'}")
    print(f"期待結果: ❌ 違反 (休息時間不足)")

if __name__ == "__main__":
    test_constraint_violations()
    test_constrained_algorithm() 