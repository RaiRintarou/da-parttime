#!/usr/bin/env python3
"""
パフォーマンステストスクリプト

シフト生成のパフォーマンスを測定し、改善効果を確認します。
"""

import sys
import os
import time
import pandas as pd
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.constraints import RequiredBreakAfterConsecutiveSlotsConstraint
from algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match


def create_test_data(operator_count: int, desk_count: int) -> tuple:
    """テストデータを作成"""
    # デスク要員数データ
    req_data = {"desk": []}
    for i in range(desk_count):
        req_data["desk"].append(f"Desk {chr(65+i)}")
    
    # 各時間帯の要員数を設定
    for hour in range(9, 18):
        hour_col = f"h{hour:02d}"
        req_data[hour_col] = [1] * desk_count  # 各デスクに1人ずつ
    
    req_df = pd.DataFrame(req_data)
    
    # オペレーターデータ
    ops_data = []
    for i in range(operator_count):
        op_data = {
            "name": f"Op{i+1:03d}",
            "start": 9,
            "end": 17,
            "home": f"Desk {chr(65 + (i % desk_count))}",
            "desks": ", ".join([f"Desk {chr(65+j)}" for j in range(desk_count)])
        }
        ops_data.append(op_data)
    
    return req_df, ops_data


def performance_test():
    """パフォーマンステスト実行"""
    print("🚀 シフト生成パフォーマンステスト")
    print("=" * 60)
    
    # テストケース
    test_cases = [
        {"operators": 10, "desks": 3, "name": "小規模"},
        {"operators": 20, "desks": 5, "name": "中規模"},
        {"operators": 50, "desks": 8, "name": "大規模"},
        {"operators": 100, "desks": 10, "name": "超大規模"}
    ]
    
    # 制約設定
    constraints = [
        RequiredBreakAfterConsecutiveSlotsConstraint(
            max_consecutive_slots=5,
            break_desk_name="休憩"
        )
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n📊 {test_case['name']}テストケース")
        print(f"   • オペレータ数: {test_case['operators']}")
        print(f"   • デスク数: {test_case['desks']}")
        print(f"   • 制約数: {len(constraints)}")
        
        # テストデータ作成
        req_df, ops_data = create_test_data(test_case['operators'], test_case['desks'])
        
        # パフォーマンス測定
        start_time = time.time()
        
        try:
            assignments, schedule = constrained_multi_slot_da_match(
                hourly_requirements=req_df,
                legacy_ops=ops_data,
                constraints=constraints,
                target_date=datetime.now()
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 結果を記録
            result = {
                "test_case": test_case['name'],
                "operators": test_case['operators'],
                "desks": test_case['desks'],
                "execution_time": execution_time,
                "assignments": len(assignments),
                "break_assignments": len([a for a in assignments if a.desk_name == "休憩"]),
                "status": "成功"
            }
            
            print(f"   ✅ 実行時間: {execution_time:.2f}秒")
            print(f"   📋 割り当て数: {len(assignments)}")
            print(f"   ☕ 休憩割り当て数: {len([a for a in assignments if a.desk_name == '休憩'])}")
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            result = {
                "test_case": test_case['name'],
                "operators": test_case['operators'],
                "desks": test_case['desks'],
                "execution_time": execution_time,
                "assignments": 0,
                "break_assignments": 0,
                "status": f"エラー: {str(e)}"
            }
            
            print(f"   ❌ エラー: {str(e)}")
            print(f"   ⏱️ 実行時間: {execution_time:.2f}秒")
        
        results.append(result)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📈 パフォーマンステスト結果サマリー")
    print("=" * 60)
    
    print(f"{'テストケース':<12} {'オペレータ':<8} {'デスク':<6} {'実行時間':<10} {'割り当て':<8} {'休憩':<6} {'ステータス':<10}")
    print("-" * 70)
    
    for result in results:
        print(f"{result['test_case']:<12} {result['operators']:<8} {result['desks']:<6} "
              f"{result['execution_time']:<10.2f} {result['assignments']:<8} {result['break_assignments']:<6} "
              f"{result['status']:<10}")
    
    # パフォーマンス分析
    print("\n🔍 パフォーマンス分析")
    print("-" * 30)
    
    successful_results = [r for r in results if r['status'] == '成功']
    if successful_results:
        avg_time = sum(r['execution_time'] for r in successful_results) / len(successful_results)
        max_time = max(r['execution_time'] for r in successful_results)
        min_time = min(r['execution_time'] for r in successful_results)
        
        print(f"平均実行時間: {avg_time:.2f}秒")
        print(f"最大実行時間: {max_time:.2f}秒")
        print(f"最小実行時間: {min_time:.2f}秒")
        
        # スケーラビリティ分析
        if len(successful_results) >= 2:
            first_result = successful_results[0]
            last_result = successful_results[-1]
            
            time_ratio = last_result['execution_time'] / first_result['execution_time']
            operator_ratio = last_result['operators'] / first_result['operators']
            
            print(f"オペレータ数増加率: {operator_ratio:.1f}倍")
            print(f"実行時間増加率: {time_ratio:.1f}倍")
            
            if time_ratio < operator_ratio * 2:
                print("✅ 良好なスケーラビリティ")
            elif time_ratio < operator_ratio * 5:
                print("⚠️ 中程度のスケーラビリティ")
            else:
                print("❌ スケーラビリティに問題あり")
    
    print("\n🎉 パフォーマンステスト完了!")


if __name__ == "__main__":
    performance_test() 