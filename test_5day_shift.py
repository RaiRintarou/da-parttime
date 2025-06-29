#!/usr/bin/env python3
"""
5日分シフト生成機能のテスト

連続5日のシフト生成と1日分の拡張機能をテストします。
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match
from algorithms.multi_slot_da_algorithm import multi_slot_da_match
from models.constraints import create_default_constraints

def test_5day_shift_generation():
    """5日分シフト生成のテスト"""
    print("🧪 5日分シフト生成テスト開始")
    print("=" * 50)
    
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
    
    # 開始日設定
    start_date = datetime.now().date()
    target_days = 5
    
    print(f"📅 シフト期間: {start_date.strftime('%Y-%m-%d')} から {target_days}日間")
    print()
    
    # 制約付きMulti-slot DAアルゴリズムで5日分生成
    print("🚀 制約付きMulti-slot DAアルゴリズムで5日分シフト生成中...")
    try:
        constraints = create_default_constraints()
        all_assignments = []
        all_schedules = []
        
        for day in range(target_days):
            current_date = datetime.combine(start_date, datetime.min.time()) + timedelta(days=day)
            print(f"  📅 {current_date.strftime('%Y-%m-%d')} のシフト生成中...")
            
            assignments, schedule = constrained_multi_slot_da_match(
                hourly_requirements, operators_data, constraints, current_date
            )
            all_assignments.extend(assignments)
            all_schedules.append(schedule)
        
        print("✅ 5日分シフト生成成功!")
        print()
        
        # 結果表示
        print("📋 5日分の割り当て結果:")
        for i, day_assignments in enumerate([all_assignments[i:i+2] for i in range(0, len(all_assignments), 2)]):
            day_date = start_date + timedelta(days=i)
            print(f"  {day_date.strftime('%Y-%m-%d')}:")
            for assignment in day_assignments:
                print(f"    {assignment.operator_name} → {assignment.desk_name} ({assignment.slot_id})")
        print()
        
        # 統合スケジュール表
        print("📅 5日分の統合シフト表:")
        # 各日のシフト表に日付を追加して列名を一意にする
        renamed_schedules = []
        for i, day_schedule in enumerate(all_schedules):
            day_date = start_date + timedelta(days=i)
            date_str = day_date.strftime('%m-%d')
            # 列名に日付を追加
            renamed_cols = {col: f"{col}_{date_str}" for col in day_schedule.columns}
            renamed_schedule = day_schedule.rename(columns=renamed_cols)
            renamed_schedules.append(renamed_schedule)
        
        combined_schedule = pd.concat(renamed_schedules, axis=1)
        print(combined_schedule)
        print()
        
        # 検証
        print("🔍 結果検証:")
        print(f"  総割り当て数: {len(all_assignments)}")
        print(f"  生成日数: {target_days}日")
        print(f"  1日あたりの割り当て数: {len(all_assignments) // target_days}")
        
        # 制約違反チェック
        from models.constraints import ConstraintValidator
        validator = ConstraintValidator(constraints)
        violations = validator.get_violations(all_assignments, [])
        
        if violations:
            print("⚠️ 制約違反が検出されました:")
            for violation in violations:
                print(f"  • {violation}")
        else:
            print("✅ すべての制約を満たしています")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        print("詳細なエラー情報:")
        print(traceback.format_exc())

def test_1day_to_5day_expansion():
    """1日分から5日分への拡張テスト"""
    print("\n🔄 1日分から5日分への拡張テスト")
    print("=" * 45)
    
    # 1日分のシフトを生成
    print("📊 1日分のシフト生成中...")
    
    desks_data = {
        "desk": ["Desk A"],
        "h09": [1],
        "h10": [1],
        "h11": [1],
        "h12": [0],
        "h13": [0],
        "h14": [0],
        "h15": [0],
        "h16": [0],
        "h17": [0]
    }
    
    hourly_requirements = pd.DataFrame(desks_data)
    
    operators_data = [
        {
            "name": "Op1",
            "start": 9,
            "end": 12,
            "home": "Desk A",
            "desks": ["Desk A"]
        }
    ]
    
    start_date = datetime.now().date()
    
    try:
        # 1日分のシフト生成
        assignments, schedule = multi_slot_da_match(hourly_requirements, operators_data, datetime.combine(start_date, datetime.min.time()))
        
        print("✅ 1日分シフト生成成功!")
        print("📅 1日分シフト表:")
        print(schedule)
        print()
        
        # 1日分を5日分に拡張
        print("🔄 1日分を5日分に拡張中...")
        expanded_schedules = []
        
        for day in range(5):
            current_date = datetime.combine(start_date, datetime.min.time()) + timedelta(days=day)
            # 同じシフトを5日分コピー
            day_schedule = schedule.copy()
            expanded_schedules.append(day_schedule)
        
        # 統合
        combined_expanded = pd.concat(expanded_schedules, axis=1)
        
        print("✅ 5日分拡張成功!")
        print("📅 拡張された5日分シフト表:")
        print(combined_expanded)
        print()
        
        print("🔍 拡張結果検証:")
        print(f"  元のシフト行数: {len(schedule)}")
        print(f"  拡張後のシフト行数: {len(combined_expanded)}")
        print(f"  拡張後の列数: {len(combined_expanded.columns)}")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")

if __name__ == "__main__":
    test_5day_shift_generation()
    test_1day_to_5day_expansion()
    
    print("\n🎉 5日分シフト生成テスト完了!")
    print("Streamlitアプリで5日分シフト生成機能をテストしてください。") 