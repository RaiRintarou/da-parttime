#!/usr/bin/env python3
"""
休憩時間制約の動作確認テスト

連続稼働5時間以上の場合に1時間の休憩を必須とする制約の動作を確認します。
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.constraints import RequiredBreakAfterLongShiftConstraint
from models.multi_slot_models import Assignment, OperatorAvailability
from algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match

def test_break_constraint():
    """休憩時間制約の動作確認"""
    print("🧪 休憩時間制約の動作確認を開始します")
    
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
    
    # 休憩時間制約を作成
    break_constraint = RequiredBreakAfterLongShiftConstraint(
        long_shift_threshold_hours=5.0,
        required_break_hours=1.0
    )
    
    print(f"📋 制約設定:")
    print(f"  • 長時間シフト閾値: {break_constraint.long_shift_threshold_hours}時間")
    print(f"  • 必須休憩時間: {break_constraint.required_break_hours}時間")
    
    # 制約付きアルゴリズムでマッチング実行
    target_date = datetime(2024, 1, 1)
    assignments, schedule = constrained_multi_slot_da_match(
        req_df, ops_data, [break_constraint], target_date
    )
    
    print(f"\n📊 マッチング結果:")
    print(f"  • 総割り当て数: {len(assignments)}")
    
    # 割り当て結果を表示
    for assignment in assignments:
        print(f"  • {assignment.operator_name} → {assignment.desk_name} ({assignment.slot_id})")
    
    # 休憩割り当てを取得
    operators = [
        OperatorAvailability(operator_name=op["name"])
        for op in ops_data
    ]
    
    break_assignments = break_constraint.get_break_assignments(assignments, operators)
    
    print(f"\n☕ 休憩割り当て:")
    if break_assignments:
        for break_assignment in break_assignments:
            print(f"  • {break_assignment['operator_name']}: h{break_assignment['break_hour']:02d} ({break_assignment['desk_name']})")
            print(f"    → {break_assignment['reason']}")
    else:
        print("  • 必要な休憩割り当てはありません")
    
    # シフト表を表示
    print(f"\n📅 シフト表:")
    print(schedule.to_string())
    
    # 休憩が含まれているかチェック
    has_break = False
    for col in schedule.columns:
        if 'h' in str(col) and col != 'desk':
            for idx, value in schedule[col].items():
                if str(value) == '休憩':
                    has_break = True
                    print(f"\n✅ 休憩がシフト表に反映されています: {schedule.at[idx, 'desk']} の {col}")
    
    if not has_break:
        print("\n⚠️ シフト表に休憩が反映されていません")
    
    print(f"\n🎯 テスト完了")

if __name__ == "__main__":
    test_break_constraint() 