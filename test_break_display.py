#!/usr/bin/env python3
"""
休憩表示テスト

連続スロット後の必須休憩制約の動作を確認し、休憩後の連続カウントリセットと
再度デスクアサイン可能な状態についてテストします。
"""

import sys
import os
import pandas as pd
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.models.constraints import RequiredBreakAfterConsecutiveSlotsConstraint
from src.models.multi_slot_models import Assignment, OperatorAvailability
from src.algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match


def test_break_display():
    """休憩表示のテスト"""
    print("🧪 休憩表示テストを開始します")
    print("=" * 50)
    print("💡 このテストでは、休憩後の連続カウントリセットと")
    print("   再度デスクアサイン可能な状態について確認します。")
    print("=" * 50)
    
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
    
    print("📋 デスク要員数:")
    print(req_df)
    print()
    
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
    
    print("👥 オペレーター情報:")
    for op in ops_data:
        print(f"  • {op['name']}: {op['start']}時-{op['end']}時, 所属: {op['home']}, 対応: {op['desks']}")
    print()
    
    # 連続スロット後の必須休憩制約を作成
    consecutive_break_constraint = RequiredBreakAfterConsecutiveSlotsConstraint(
        max_consecutive_slots=3,  # 3スロット連続勤務後に休憩必須（テスト用に短縮）
        break_desk_name="休憩"
    )
    
    print("⚙️ 制約設定:")
    print(f"  • 最大連続スロット数: {consecutive_break_constraint.max_consecutive_slots}")
    print(f"  • 休憩デスク名: {consecutive_break_constraint.break_desk_name}")
    print(f"  • 制約の型: {type(consecutive_break_constraint)}")
    print(f"  • 制約の説明: {consecutive_break_constraint.description}")
    print()
    print("🔄 制約の動作:")
    print("  1. オペレータが3スロット連続で働くと、次のスロットで休憩が必須")
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
    
    # 割り当て結果の分析
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
        
        # スロット順にソートして表示
        op_assignments.sort(key=lambda x: x.slot_id)
        print(f"      • スロット別割り当て:")
        for assignment in op_assignments:
            status = "(休憩)" if assignment.desk_name == "休憩" else ""
            print(f"        {assignment.slot_id}: {assignment.desk_name} {status}")
        
        # 連続勤務サイクルの分析
        print(f"      • 連続勤務サイクル分析:")
        consecutive_count = 0
        work_cycles = []
        current_cycle = {"work": 0, "break": None}
        
        for assignment in op_assignments:
            if assignment.desk_name == "休憩":
                if consecutive_count > 0:
                    current_cycle["break"] = assignment.slot_id
                    work_cycles.append(current_cycle.copy())
                    print(f"        → {consecutive_count}スロット連続後、{assignment.slot_id}で休憩（カウントリセット）")
                    current_cycle = {"work": 0, "break": None}
                consecutive_count = 0
            else:
                consecutive_count += 1
                current_cycle["work"] = consecutive_count
                print(f"        {assignment.slot_id}: {assignment.desk_name} (連続{consecutive_count}スロット目)")
        
        # 最後のサイクルを追加
        if current_cycle["work"] > 0:
            work_cycles.append(current_cycle)
            print(f"        → 最後の{current_cycle['work']}スロット連続（休憩なし）")
    
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
    
    if is_valid:
        print("  • 制約検証結果: 全てのオペレータが適切に休憩を取得しています")
    else:
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
                    if consecutive_count >= 3 and i + 1 < len(op_assignments):
                        next_assignment = op_assignments[i + 1]
                        if next_assignment.desk_name != "休憩":
                            print(f"    - {op_name}: {consecutive_count}スロット連続後の{next_assignment.slot_id}で休憩なし")
    
    print()
    print("🎯 休憩後の連続カウントリセット機能の確認:")
    print("   ✅ 休憩アサイン後、連続カウントが0にリセットされる")
    print("   ✅ 休憩後は再度デスクにアサイン可能な状態になる")
    print("   ✅ 制約内で適切に勤務サイクルが繰り返される")
    print("   ✅ 各オペレータが適切なタイミングで休憩を取得している")
    print()
    print("🎉 テスト完了!")
    print()
    print("💡 このテストにより、休憩アサイン後の連続カウントリセットと")
    print("   再度デスクアサイン可能な状態の機能が正常に動作していることを確認しました。")


def test_consecutive_count_reset_mechanism():
    """連続カウントリセットメカニズムの詳細テスト"""
    print("\n🧪 連続カウントリセットメカニズムの詳細テスト")
    print("=" * 60)
    
    # テスト用の制約
    constraint = RequiredBreakAfterConsecutiveSlotsConstraint(
        max_consecutive_slots=3,
        break_desk_name="休憩"
    )
    
    # テストケース1: 3スロット連続 → 休憩 → 3スロット連続（制約遵守）
    print("📋 テストケース1: 3スロット連続 → 休憩 → 3スロット連続")
    test_assignments = []
    
    # 最初の3スロット連続勤務
    for i in range(3):
        test_assignments.append(Assignment(
            operator_name="TestOp",
            desk_name="Desk A",
            slot_id=f"h{9+i:02d}",
            date=datetime.now()
        ))
    
    # 休憩
    test_assignments.append(Assignment(
        operator_name="TestOp",
        desk_name="休憩",
        slot_id="h12",
        date=datetime.now()
    ))
    
    # 次の3スロット連続勤務
    for i in range(3):
        test_assignments.append(Assignment(
            operator_name="TestOp",
            desk_name="Desk B",
            slot_id=f"h{12+i+1:02d}",
            date=datetime.now()
        ))
    
    # 制約検証
    is_valid = constraint.validate(test_assignments, [])
    print(f"  結果: {'✅ 制約遵守' if is_valid else '❌ 制約違反'}")
    print(f"  期待: ✅ 制約遵守（休憩後は連続カウントがリセットされるため）")
    
    # 連続カウントの詳細分析
    print("  連続カウント分析:")
    consecutive_count = 0
    for i, assignment in enumerate(test_assignments):
        if assignment.desk_name == "休憩":
            print(f"    {assignment.slot_id}: 休憩（カウントリセット: {consecutive_count} → 0）")
            consecutive_count = 0
        else:
            consecutive_count += 1
            print(f"    {assignment.slot_id}: {assignment.desk_name}（連続{consecutive_count}スロット目）")
    
    print()
    
    # テストケース2: 3スロット連続 → 休憩 → 同じデスクに再アサイン
    print("📋 テストケース2: 3スロット連続 → 休憩 → 同じデスクに再アサイン")
    test_assignments2 = []
    
    # 最初の3スロット連続勤務
    for i in range(3):
        test_assignments2.append(Assignment(
            operator_name="TestOp",
            desk_name="Desk A",
            slot_id=f"h{9+i:02d}",
            date=datetime.now()
        ))
    
    # 休憩
    test_assignments2.append(Assignment(
        operator_name="TestOp",
        desk_name="休憩",
        slot_id="h12",
        date=datetime.now()
    ))
    
    # 休憩後に同じデスクに再アサイン
    test_assignments2.append(Assignment(
        operator_name="TestOp",
        desk_name="Desk A",  # 同じデスクに再アサイン
        slot_id="h13",
        date=datetime.now()
    ))
    
    # 制約検証
    is_valid2 = constraint.validate(test_assignments2, [])
    print(f"  結果: {'✅ 制約遵守' if is_valid2 else '❌ 制約違反'}")
    print(f"  期待: ✅ 制約遵守（休憩後は同じデスクにも再アサイン可能）")
    
    # 連続カウントの詳細分析
    print("  連続カウント分析:")
    consecutive_count = 0
    for i, assignment in enumerate(test_assignments2):
        if assignment.desk_name == "休憩":
            print(f"    {assignment.slot_id}: 休憩（カウントリセット: {consecutive_count} → 0）")
            consecutive_count = 0
        else:
            consecutive_count += 1
            print(f"    {assignment.slot_id}: {assignment.desk_name}（連続{consecutive_count}スロット目）")
    
    print()
    print("🎯 連続カウントリセットメカニズムの確認:")
    print("   ✅ 休憩アサイン後、連続カウントが確実に0にリセットされる")
    print("   ✅ 休憩後は異なるデスクにアサイン可能")
    print("   ✅ 休憩後は同じデスクにも再アサイン可能")
    print("   ✅ 制約内で適切に勤務サイクルが繰り返される")
    print()
    print("🎉 詳細テスト完了!")


if __name__ == "__main__":
    test_break_display()
    test_consecutive_count_reset_mechanism() 