#!/usr/bin/env python3
"""
Multi-slot DAアルゴリズムのデバッグテスト

2人のオペレーターで3時間の動作を確認します。
"""

import sys
import os
import pandas as pd
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from algorithms.multi_slot_da_algorithm import multi_slot_da_match
from models.multi_slot_models import create_default_slots, convert_hourly_to_slots

def test_multi_slot_with_2_operators():
    """2人のオペレーターで3時間の動作テスト"""
    print("🧪 Multi-slot DAアルゴリズム デバッグテスト開始")
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
    
    # Multi-slot DAアルゴリズム実行
    print("🚀 Multi-slot DAアルゴリズム実行中...")
    try:
        assignments, schedule_df = multi_slot_da_match(hourly_requirements, operators_data)
        
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
        
        # 検証
        print("🔍 結果検証:")
        print(f"  割り当て数: {len(assignments)}")
        print(f"  オペレーター数: {len(operators_data)}")
        print(f"  デスク数: {len(hourly_requirements)}")
        
        # 各デスクの割り当て状況を確認
        for desk in hourly_requirements["desk"]:
            desk_assignments = [a for a in assignments if a.desk_name == desk]
            print(f"  {desk}: {len(desk_assignments)}人割り当て")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        print("詳細なエラー情報:")
        print(traceback.format_exc())

def test_slot_conversion():
    """スロット変換のテスト"""
    print("\n🔧 スロット変換テスト")
    print("=" * 30)
    
    # テストデータ
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
    
    try:
        desk_requirements = convert_hourly_to_slots(hourly_requirements)
        print("スロット変換結果:")
        for req in desk_requirements:
            print(f"  {req.desk_name}: {req.slot_requirements}")
    except Exception as e:
        print(f"❌ スロット変換エラー: {str(e)}")

if __name__ == "__main__":
    test_slot_conversion()
    test_multi_slot_with_2_operators() 