#!/usr/bin/env python3
"""
制約設定UIのテスト

Streamlitアプリの制約設定UIの動作をテストします。
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.constraints import (
    MinRestHoursConstraint, MaxConsecutiveDaysConstraint,
    MaxWeeklyHoursConstraint, MaxNightShiftsPerWeekConstraint,
    RequiredDayOffAfterNightConstraint
)

def test_constraint_creation():
    """制約作成のテスト"""
    print("🧪 制約設定UI テスト開始")
    print("=" * 50)
    
    # テスト用の制約設定
    test_settings = {
        "min_rest_hours": 10.0,
        "max_consecutive_days": 5,
        "max_weekly_hours": 35.0,
        "max_night_shifts_per_week": 3,
        "required_day_off_after_night": True,
        "enable_min_rest": True,
        "enable_consecutive": True,
        "enable_weekly_hours": False,  # 無効化
        "enable_night_shifts": True,
        "enable_day_off_after_night": False  # 無効化
    }
    
    print("📊 テスト設定:")
    for key, value in test_settings.items():
        print(f"  {key}: {value}")
    print()
    
    # 制約リストを作成
    constraints = []
    
    if test_settings["enable_min_rest"]:
        constraint = MinRestHoursConstraint(min_rest_hours=test_settings["min_rest_hours"])
        constraints.append(constraint)
        print(f"✅ 最小休息時間制約追加: {constraint.description}")
    
    if test_settings["enable_consecutive"]:
        constraint = MaxConsecutiveDaysConstraint(max_consecutive_days=test_settings["max_consecutive_days"])
        constraints.append(constraint)
        print(f"✅ 最大連勤日数制約追加: {constraint.description}")
    
    if test_settings["enable_weekly_hours"]:
        constraint = MaxWeeklyHoursConstraint(max_weekly_hours=test_settings["max_weekly_hours"])
        constraints.append(constraint)
        print(f"✅ 最大週間労働時間制約追加: {constraint.description}")
    
    if test_settings["enable_night_shifts"]:
        constraint = MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=test_settings["max_night_shifts_per_week"])
        constraints.append(constraint)
        print(f"✅ 週間最大夜勤数制約追加: {constraint.description}")
    
    if test_settings["enable_day_off_after_night"]:
        constraint = RequiredDayOffAfterNightConstraint()
        constraints.append(constraint)
        print(f"✅ 夜勤後の必須休日制約追加: {constraint.description}")
    
    print()
    print(f"📋 作成された制約数: {len(constraints)}")
    
    # 制約の詳細表示
    print("\n🔍 制約詳細:")
    for i, constraint in enumerate(constraints, 1):
        print(f"  {i}. {constraint.description}")
        print(f"     タイプ: {constraint.constraint_type.value}")
        print(f"     ハード制約: {constraint.is_hard}")
        print(f"     重み: {constraint.weight}")
    
    return constraints

def test_constraint_validation():
    """制約検証のテスト"""
    print("\n🔒 制約検証テスト")
    print("=" * 30)
    
    # テスト用の制約を作成
    constraints = [
        MinRestHoursConstraint(min_rest_hours=10.0),
        MaxConsecutiveDaysConstraint(max_consecutive_days=5),
        MaxWeeklyHoursConstraint(max_weekly_hours=35.0)
    ]
    
    # 制約検証器を作成
    from models.constraints import ConstraintValidator
    validator = ConstraintValidator(constraints)
    
    print(f"✅ 制約検証器作成完了")
    print(f"   制約数: {len(constraints)}")
    
    # 制約の詳細表示
    print("\n📋 制約一覧:")
    for constraint in constraints:
        print(f"  • {constraint.description}")
    
    return validator

def test_constraint_persistence():
    """制約設定の永続化テスト"""
    print("\n💾 制約設定永続化テスト")
    print("=" * 35)
    
    # 模擬的なセッション状態
    session_state = {
        "saved_constraints": {
            "min_rest_hours": 12.0,
            "max_consecutive_days": 4,
            "max_weekly_hours": 30.0,
            "max_night_shifts_per_week": 1,
            "required_day_off_after_night": True,
            "enable_min_rest": True,
            "enable_consecutive": True,
            "enable_weekly_hours": True,
            "enable_night_shifts": True,
            "enable_day_off_after_night": True
        }
    }
    
    print("📊 保存された設定:")
    for key, value in session_state["saved_constraints"].items():
        print(f"  {key}: {value}")
    
    # 設定から制約を復元
    saved = session_state["saved_constraints"]
    constraints = []
    
    if saved["enable_min_rest"]:
        constraints.append(MinRestHoursConstraint(min_rest_hours=saved["min_rest_hours"]))
    
    if saved["enable_consecutive"]:
        constraints.append(MaxConsecutiveDaysConstraint(max_consecutive_days=saved["max_consecutive_days"]))
    
    if saved["enable_weekly_hours"]:
        constraints.append(MaxWeeklyHoursConstraint(max_weekly_hours=saved["max_weekly_hours"]))
    
    if saved["enable_night_shifts"]:
        constraints.append(MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=saved["max_night_shifts_per_week"]))
    
    if saved["enable_day_off_after_night"]:
        constraints.append(RequiredDayOffAfterNightConstraint())
    
    print(f"\n✅ 復元された制約数: {len(constraints)}")
    
    return constraints

if __name__ == "__main__":
    # 各テストを実行
    test_constraint_creation()
    test_constraint_validation()
    test_constraint_persistence()
    
    print("\n🎉 制約設定UIテスト完了!")
    print("Streamlitアプリで制約設定機能をテストしてください。") 