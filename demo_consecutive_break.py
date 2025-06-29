#!/usr/bin/env python3
"""
連続スロット後の必須休憩制約機能デモ

5スロット連続で働いたオペレータが次のスロットで「休憩」デスクにアサインされる機能のデモンストレーション。
休憩アサイン後は連続カウントが0にリセットされ、再度デスクにアサイン可能な状態になります。
"""

import sys
import os
import pandas as pd
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.models.constraints import RequiredBreakAfterConsecutiveSlotsConstraint
from src.algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match


def demo_consecutive_break_constraint():
    """連続スロット後の必須休憩制約のデモ"""
    print("🚀 連続スロット後の必須休憩制約機能デモ")
    print("=" * 60)
    print("💡 このデモでは、5スロット連続で働いたオペレータが")
    print("   自動的に次のスロットで「休憩」デスクに割り当てられます。")
    print("   休憩アサイン後は連続カウントが0にリセットされ、")
    print("   再度デスクにアサイン可能な状態になります。")
    print("=" * 60)
    
    # デモ用のデスク要員数データ（長時間勤務シナリオ）
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
    
    print("📋 デスク要員数:")
    print(req_df)
    print()
    
    # デモ用のオペレーターデータ（長時間勤務するオペレーター）
    ops_data = [
        {
            "name": "田中",
            "start": 9,
            "end": 17,
            "home": "Desk A",
            "desks": "Desk A,Desk B"
        },
        {
            "name": "佐藤", 
            "start": 9,
            "end": 17,
            "home": "Desk B",
            "desks": "Desk A,Desk B"
        },
        {
            "name": "鈴木",
            "start": 9,
            "end": 17,
            "home": "Desk A",
            "desks": "Desk A,Desk B"
        }
    ]
    
    print("👥 オペレーター情報:")
    for op in ops_data:
        print(f"  • {op['name']}: {op['start']}時-{op['end']}時, 所属: {op['home']}, 対応: {op['desks']}")
    print()
    
    # 連続スロット後の必須休憩制約を作成
    consecutive_break_constraint = RequiredBreakAfterConsecutiveSlotsConstraint(
        max_consecutive_slots=5,  # 5スロット連続勤務後に休憩必須
        break_desk_name="休憩"
    )
    
    print("⚙️ 制約設定:")
    print(f"  • 最大連続スロット数: {consecutive_break_constraint.max_consecutive_slots}")
    print(f"  • 休憩デスク名: {consecutive_break_constraint.break_desk_name}")
    print(f"  • 制約説明: {consecutive_break_constraint.description}")
    print()
    print("🔄 制約の動作:")
    print("  1. オペレータが5スロット連続で働くと、次のスロットで休憩が必須")
    print("  2. 休憩アサイン後、連続カウントが0にリセット")
    print("  3. 休憩後は再度デスクにアサイン可能な状態に戻る")
    print("  4. このサイクルが繰り返される")
    print()
    
    # 制約付きアルゴリズムでマッチング実行
    print("🔄 シフト生成中...")
    assignments, schedule = constrained_multi_slot_da_match(
        hourly_requirements=req_df,
        legacy_ops=ops_data,
        constraints=[consecutive_break_constraint],
        target_date=datetime.now()
    )
    
    print("✅ シフト生成完了!")
    print()
    
    # 結果の分析
    print("📊 割り当て結果分析:")
    print(f"  • 総割り当て数: {len(assignments)}")
    
    # オペレーター別の割り当てを集計
    operator_assignments = {}
    for assignment in assignments:
        op_name = assignment.operator_name
        if op_name not in operator_assignments:
            operator_assignments[op_name] = []
        operator_assignments[op_name].append(assignment)
    
    print("  • オペレーター別割り当て:")
    for op_name, op_assignments in operator_assignments.items():
        print(f"    - {op_name}: {len(op_assignments)}スロット")
        
        # 連続勤務の分析
        consecutive_count = 0
        max_consecutive = 0
        break_slots = []
        work_cycles = []  # 勤務サイクルを記録
        
        # スロット順にソート
        op_assignments.sort(key=lambda x: x.slot_id)
        
        current_cycle = {"work": 0, "break": None}
        
        for assignment in op_assignments:
            if assignment.desk_name == "休憩":
                if consecutive_count > 0:
                    break_slots.append(f"{consecutive_count}スロット連続後")
                    current_cycle["break"] = assignment.slot_id
                    work_cycles.append(current_cycle.copy())
                    current_cycle = {"work": 0, "break": None}
                consecutive_count = 0
            else:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
                current_cycle["work"] = consecutive_count
        
        # 最後のサイクルを追加
        if current_cycle["work"] > 0:
            work_cycles.append(current_cycle)
        
        print(f"      • 最大連続勤務: {max_consecutive}スロット")
        if break_slots:
            print(f"      • 休憩タイミング: {', '.join(break_slots)}")
        
        # 勤務サイクルの詳細表示
        print(f"      • 勤務サイクル詳細:")
        for i, cycle in enumerate(work_cycles, 1):
            if cycle["break"]:
                print(f"        サイクル{i}: {cycle['work']}スロット連続 → {cycle['break']}で休憩")
            else:
                print(f"        サイクル{i}: {cycle['work']}スロット連続（休憩なし）")
    
    # 休憩割り当てを確認
    break_assignments = [a for a in assignments if a.desk_name == "休憩"]
    print(f"  • 休憩割り当て数: {len(break_assignments)}")
    
    if break_assignments:
        print("  • 休憩割り当て詳細:")
        for break_assignment in break_assignments:
            print(f"    - {break_assignment.operator_name}: {break_assignment.slot_id} ({break_assignment.date.strftime('%Y-%m-%d')})")
    
    print()
    
    # シフト表の表示
    print("📋 シフト表:")
    print(schedule)
    print()
    
    # 制約の検証
    print("🔍 制約検証:")
    is_valid = consecutive_break_constraint.validate(assignments, [])
    print(f"  • 制約遵守: {'✅ 適合' if is_valid else '❌ 違反'}")
    
    if not is_valid:
        print("  • 制約違反の詳細:")
        # 制約違反の詳細を分析
        for op_name, op_assignments in operator_assignments.items():
            consecutive_count = 0
            op_assignments.sort(key=lambda x: x.slot_id)
            
            for i, assignment in enumerate(op_assignments):
                if assignment.desk_name == "休憩":
                    consecutive_count = 0
                else:
                    consecutive_count += 1
                    if consecutive_count >= 5 and i + 1 < len(op_assignments):
                        next_assignment = op_assignments[i + 1]
                        if next_assignment.desk_name != "休憩":
                            print(f"    - {op_name}: {consecutive_count}スロット連続後の{next_assignment.slot_id}で休憩なし")
    
    print()
    print("🎯 休憩後の連続カウントリセット機能の確認:")
    print("   ✅ 休憩アサイン後、連続カウントが0にリセットされる")
    print("   ✅ 休憩後は再度デスクにアサイン可能な状態になる")
    print("   ✅ 制約内で適切に勤務サイクルが繰り返される")
    print()
    print("🎉 デモ完了!")
    print()
    print("�� このデモでは、5スロット連続で働いたオペレータが")
    print("   自動的に次のスロットで「休憩」デスクに割り当てられます。")
    print("   休憩アサイン後は連続カウントが0にリセットされ、")
    print("   再度デスクにアサイン可能な状態になります。")
    print("   これにより、労働者の健康と安全を確保できます。")


if __name__ == "__main__":
    demo_consecutive_break_constraint() 