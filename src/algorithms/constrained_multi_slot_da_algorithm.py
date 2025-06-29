"""
制約を適用したMulti-slot DAアルゴリズム

このモジュールは、Hard Constraint DSLを統合した
Multi-slot DAアルゴリズムを提供します。
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, date, timedelta
import sys
import os
import time

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models.multi_slot_models import (
    TimeSlot, DailySchedule, OperatorAvailability, 
    DeskRequirement, Assignment, MultiSlotScheduler,
    create_default_slots, convert_hourly_to_slots
)
from models.constraints import (
    Constraint, MinRestHoursConstraint, MaxConsecutiveDaysConstraint,
    MaxWeeklyHoursConstraint, MaxNightShiftsPerWeekConstraint,
    RequiredDayOffAfterNightConstraint, RequiredBreakAfterLongShiftConstraint,
    RequiredBreakAfterConsecutiveSlotsConstraint,
    ConstraintValidator, create_default_constraints
)
from algorithms.multi_slot_da_algorithm import (
    MultiSlotDAMatchingAlgorithm, create_default_slots, 
    convert_hourly_to_slots
)

class ConstrainedMultiSlotDAMatchingAlgorithm:
    """制約付きMulti-slot DAアルゴリズム"""
    
    def __init__(self, slots: List[TimeSlot], desks: List[str], constraints: Optional[List[Constraint]] = None):
        self.slots = slots
        self.slot_ids = [slot.slot_id for slot in slots]  # slot_ids属性を追加
        self.desks = desks
        self.constraints = constraints or []
        self.constraint_validator = None  # ConstraintValidatorを削除
        
        # パフォーマンス最適化用のキャッシュ
        self._assignment_cache = {}  # 割り当てのキャッシュ
        self._constraint_cache = {}  # 制約チェック結果のキャッシュ
        self._max_iterations = 1000  # 無限ループ防止
    
    def _get_cache_key(self, assignments: List[Assignment], operator_name: str, desk_name: str, slot_id: str) -> str:
        """キャッシュキーを生成"""
        # 割り当てのハッシュを生成（日付とスロットIDのみ）
        assignment_hash = hash(tuple((a.date, a.slot_id, a.operator_name, a.desk_name) for a in assignments))
        return f"{assignment_hash}_{operator_name}_{desk_name}_{slot_id}"
    
    def _check_constraints_cached(self, assignments: List[Assignment], 
                                operator_name: str, desk_name: str, slot_id: str,
                                target_date: datetime, operators: List[OperatorAvailability]) -> bool:
        """キャッシュ付き制約チェック"""
        if not self.constraint_validator:
            return True
        
        # テスト用の割り当てを作成
        test_assignment = Assignment(
            operator_name=operator_name,
            desk_name=desk_name,
            slot_id=slot_id,
            date=target_date
        )
        
        # 既存の割り当てから同じスロットのものを除去
        filtered_assignments = [a for a in assignments 
                               if not (a.slot_id == slot_id and a.date == target_date)]
        test_assignments = filtered_assignments + [test_assignment]
        
        # キャッシュキーを生成
        cache_key = self._get_cache_key(test_assignments, operator_name, desk_name, slot_id)
        
        # キャッシュをチェック
        if cache_key in self._constraint_cache:
            return self._constraint_cache[cache_key]
        
        # 制約チェックを実行（高速化のため主要な制約のみチェック）
        is_valid = self._check_critical_constraints(test_assignments, operators)
        
        # キャッシュに保存
        self._constraint_cache[cache_key] = is_valid
        
        return is_valid
    
    def _check_critical_constraints(self, assignments: List[Assignment], 
                                  operators: List[OperatorAvailability]) -> bool:
        """重要な制約のみをチェック（高速化）"""
        if not self.constraint_validator:
            return True
        
        # 連続スロット後の必須休憩制約のみをチェック（最も影響が大きい）
        for constraint in self.constraints:
            if isinstance(constraint, RequiredBreakAfterConsecutiveSlotsConstraint):
                if not constraint.validate(assignments, operators):
                    return False
        
        return True
    
    def _create_slot_preferences(self, operators: List[OperatorAvailability]) -> Dict[str, Dict[str, List[str]]]:
        """各デスクの各スロットにおけるオペレータ優先順位を作成"""
        preferences = {}
        
        for desk in self.desks:
            desk_prefs = {}
            for slot_id in self.slot_ids:
                # このスロットで利用可能なオペレータを取得
                available_ops = [
                    op for op in operators 
                    if op.can_work_slot(slot_id)
                ]
                
                # 優先順位を決定（好ましいスロットのオペレータを優先）
                preferred_ops = [op for op in available_ops if op.prefers_slot(slot_id)]
                other_ops = [op for op in available_ops if not op.prefers_slot(slot_id)]
                
                # 好ましいスロットのオペレータを先に、その後他のオペレータを追加
                desk_prefs[slot_id] = [op.operator_name for op in preferred_ops + other_ops]
            
            preferences[desk] = desk_prefs
        
        return preferences
    
    def _create_operator_slot_preferences(self, operators: List[OperatorAvailability]) -> Dict[str, Dict[str, List[str]]]:
        """各オペレータの各スロットにおけるデスク優先順位を作成"""
        preferences = {}
        
        for op in operators:
            op_prefs = {}
            for slot_id in self.slot_ids:
                if op.can_work_slot(slot_id):
                    # オペレータのデスク優先順位（対応可能なデスクのみ）
                    available_desks = [desk for desk in self.desks if op.can_work_desk(desk)]
                    if op.prefers_slot(slot_id):
                        # 好ましいスロットの場合、より高い優先度
                        op_prefs[slot_id] = available_desks
                    else:
                        # 好ましくないスロットの場合、通常の優先度
                        op_prefs[slot_id] = available_desks
                else:
                    # 利用できないスロットの場合、空リスト
                    op_prefs[slot_id] = []
            
            preferences[op.operator_name] = op_prefs
        
        return preferences
    
    def match_daily(self, operators: List[OperatorAvailability], 
                   desk_requirements: List[DeskRequirement], 
                   target_date: datetime) -> List[Assignment]:
        """1日分の制約付きDAアルゴリズムによるマッチング実行"""
        assignments = []
        
        # 各スロットでDAアルゴリズムを実行
        for slot in self.slots:
            print(f"DEBUG: スロット {slot.slot_id} のマッチング開始")
            
            # 初期マッチングを実行
            slot_assignments = self._match_slot_with_constraints(
                operators, desk_requirements, slot.slot_id, target_date, assignments
            )
            assignments.extend(slot_assignments)
            
            # 要員不足解消プロセスを実行
            print(f"DEBUG: スロット {slot.slot_id} の要員不足解消プロセス開始")
            assignments = self._optimize_assignments_for_shortage(
                assignments, operators, desk_requirements, slot.slot_id, target_date
            )
            
            print(f"DEBUG: スロット {slot.slot_id} のマッチング完了 - 割り当て数: {len([a for a in assignments if a.slot_id == slot.slot_id])}")
        
        return assignments
    
    def _match_slot_with_constraints(self, operators: List[OperatorAvailability], 
                                   desk_requirements: List[DeskRequirement], 
                                   slot_id: str, target_date: datetime,
                                   existing_assignments: List[Assignment]) -> List[Assignment]:
        """
        制約を考慮したスロット別マッチング（連続スロット制約対応版）
        
        Args:
            operators: オペレータ利用可能性リスト
            desk_requirements: デスク要件リスト
            slot_id: 対象スロットID
            target_date: 対象日付
            existing_assignments: 既存の割り当てリスト
            
        Returns:
            List[Assignment]: このスロットの割り当てリスト
        """
        # 連続スロット制約を取得
        consecutive_break_constraint = None
        if self.constraints:
            consecutive_break_constraint = next((c for c in self.constraints 
                                               if isinstance(c, RequiredBreakAfterConsecutiveSlotsConstraint)), None)
            print(f"DEBUG: 制約チェック - 制約数: {len(self.constraints)}, 連続スロット制約: {consecutive_break_constraint is not None}")
        
        # 既存の割り当てから、このスロットで既に割り当てられているオペレータを除外
        existing_slot_assignments = [a for a in existing_assignments if a.slot_id == slot_id]
        assigned_operators = {a.operator_name for a in existing_slot_assignments}
        
        # 連続スロット制約がある場合、休憩が必要なオペレータを特定
        required_break_operators = set()
        if consecutive_break_constraint:
            print(f"DEBUG: 連続スロット制約チェック開始 - 最大連続スロット数: {consecutive_break_constraint.max_consecutive_slots}")
            # 各オペレータの連続勤務状況をチェック
            for operator in operators:
                if operator.operator_name in assigned_operators:
                    continue  # 既に割り当て済み
                
                # このオペレータの既存割り当てを取得（現在のスロットより前のもののみ）
                # スロットIDから時間を抽出して数値比較
                current_hour = int(slot_id[1:]) if slot_id.startswith('h') else 9
                op_assignments = [a for a in existing_assignments 
                                if a.operator_name == operator.operator_name]
                
                # 現在のスロットより前の割り当てのみをフィルタ
                filtered_assignments = []
                for assignment in op_assignments:
                    assignment_hour = int(assignment.slot_id[1:]) if assignment.slot_id.startswith('h') else 9
                    if assignment_hour < current_hour:
                        filtered_assignments.append(assignment)
                
                filtered_assignments.sort(key=lambda x: (x.date, x.slot_id))
                
                # 連続カウントを計算（休憩後のリセットを考慮）
                consecutive_count = 0
                print(f"DEBUG: {operator.operator_name} - 連続カウント計算開始（スロット{slot_id}）")
                for assignment in filtered_assignments:
                    if assignment.desk_name == consecutive_break_constraint.break_desk_name:
                        print(f"  {assignment.slot_id}: 休憩（カウントリセット: {consecutive_count} → 0）")
                        consecutive_count = 0  # 休憩後は連続カウントをリセット
                    else:
                        consecutive_count += 1
                        print(f"  {assignment.slot_id}: {assignment.desk_name}（連続{consecutive_count}スロット目）")
                
                print(f"DEBUG: {operator.operator_name} - 最終連続カウント: {consecutive_count}, 既存割り当て数: {len(filtered_assignments)}")
                
                # 連続スロット数が上限に達している場合、このスロットで休憩が必要
                if consecutive_count >= consecutive_break_constraint.max_consecutive_slots:
                    required_break_operators.add(operator.operator_name)
                    print(f"DEBUG: {operator.operator_name} - 休憩が必要（連続{consecutive_count}スロット）")
        
        print(f"DEBUG: 休憩が必要なオペレータ: {required_break_operators}")
        
        # 各デスクの要件を確認
        slot_requirements = []
        for req in desk_requirements:
            requirement_count = req.get_requirement_for_slot(slot_id)
            if requirement_count > 0:
                slot_requirements.append({
                    'desk_name': req.desk_name,
                    'required_count': requirement_count
                })
        
        # 連続スロット制約がある場合、休憩デスクの要件を追加
        if consecutive_break_constraint:
            # 休憩が必要なオペレータ数を計算
            break_required_count = len(required_break_operators)
            if break_required_count > 0:
                slot_requirements.append({
                    'desk_name': consecutive_break_constraint.break_desk_name,
                    'required_count': break_required_count
                })
                print(f"DEBUG: 休憩デスク要件追加 - {consecutive_break_constraint.break_desk_name}: {break_required_count}人")
            else:
                # 休憩が必要なオペレータがいない場合、休憩デスクの要件は0
                slot_requirements.append({
                    'desk_name': consecutive_break_constraint.break_desk_name,
                    'required_count': 0
                })
                print(f"DEBUG: 休憩デスク要件追加 - {consecutive_break_constraint.break_desk_name}: 0人（休憩不要）")
        
        print(f"DEBUG: スロット{slot_id}の要件: {slot_requirements}")
        
        # 各デスクの要件を処理（休憩デスクを最後に処理）
        assignments = []
        
        if consecutive_break_constraint:
            # 通常のデスクを先に処理
            normal_requirements = [req for req in slot_requirements if req['desk_name'] != consecutive_break_constraint.break_desk_name]
            break_requirements = [req for req in slot_requirements if req['desk_name'] == consecutive_break_constraint.break_desk_name]
            
            # 通常のデスクを処理
            for req in normal_requirements:
                desk_name = req['desk_name']
                required_count = req['required_count']
                
                # 既存の割り当てを確認
                existing_desk_assignments = [a for a in existing_slot_assignments if a.desk_name == desk_name]
                current_count = len(existing_desk_assignments)
                
                # 追加で必要な人数を計算
                additional_needed = required_count - current_count
                
                if additional_needed <= 0:
                    # 既に要件を満たしている場合、既存の割り当てをそのまま使用
                    assignments.extend(existing_desk_assignments)
                    continue
                
                # 利用可能なオペレータを取得（休憩が必要でないオペレータを優先）
                available_operators = []
                for operator in operators:
                    if (operator.operator_name not in assigned_operators and
                        slot_id in operator.available_slots):
                        
                        # デスク制約のチェック：オペレータがこのデスクで働けるかチェック
                        if not operator.can_work_desk(desk_name):
                            continue  # このデスクでは働けない場合はスキップ
                        
                        # 連続スロット制約のチェック
                        # 休憩が必要でないオペレータのみを通常のデスクに割り当て
                        if operator.operator_name not in required_break_operators:
                            available_operators.append(operator)
                
                # オペレータの優先度を考慮してソート
                available_operators.sort(key=lambda op: (
                    slot_id in op.preferred_slots,  # 好ましいスロットを優先
                    op.operator_name  # 名前順で安定化
                ), reverse=True)
                
                # 必要な人数分のオペレータを割り当て
                for i in range(min(additional_needed, len(available_operators))):
                    operator = available_operators[i]
                    assignment = Assignment(
                        operator_name=operator.operator_name,
                        desk_name=desk_name,
                        slot_id=slot_id,
                        date=target_date
                    )
                    assignments.append(assignment)
                    assigned_operators.add(operator.operator_name)
            
            # 休憩デスクを最後に処理
            for req in break_requirements:
                desk_name = req['desk_name']
                required_count = req['required_count']
                
                # 既存の割り当てを確認
                existing_desk_assignments = [a for a in existing_slot_assignments if a.desk_name == desk_name]
                current_count = len(existing_desk_assignments)
                
                # 追加で必要な人数を計算
                additional_needed = required_count - current_count
                
                if additional_needed <= 0:
                    # 既に要件を満たしている場合、既存の割り当てをそのまま使用
                    assignments.extend(existing_desk_assignments)
                    continue
                
                # 休憩が必要なオペレータのみを休憩デスクに割り当て
                available_operators = []
                for operator in operators:
                    if (operator.operator_name not in assigned_operators and
                        slot_id in operator.available_slots and
                        operator.operator_name in required_break_operators):
                        
                        available_operators.append(operator)
                
                # 必要な人数分のオペレータを割り当て
                for i in range(min(additional_needed, len(available_operators))):
                    operator = available_operators[i]
                    assignment = Assignment(
                        operator_name=operator.operator_name,
                        desk_name=desk_name,
                        slot_id=slot_id,
                        date=target_date
                    )
                    assignments.append(assignment)
                    assigned_operators.add(operator.operator_name)
        else:
            # 制約がない場合は通常の処理
            for req in slot_requirements:
                desk_name = req['desk_name']
                required_count = req['required_count']
                
                # 既存の割り当てを確認
                existing_desk_assignments = [a for a in existing_slot_assignments if a.desk_name == desk_name]
                current_count = len(existing_desk_assignments)
                
                # 追加で必要な人数を計算
                additional_needed = required_count - current_count
                
                if additional_needed <= 0:
                    # 既に要件を満たしている場合、既存の割り当てをそのまま使用
                    assignments.extend(existing_desk_assignments)
                    continue
                
                # 利用可能なオペレータを取得
                available_operators = []
                for operator in operators:
                    if (operator.operator_name not in assigned_operators and
                        slot_id in operator.available_slots):
                        
                        # デスク制約のチェック：オペレータがこのデスクで働けるかチェック
                        if not operator.can_work_desk(desk_name):
                            continue  # このデスクでは働けない場合はスキップ
                        
                        # 制約がない場合は対応可能なデスクに割り当て可能
                        available_operators.append(operator)
                
                # オペレータの優先度を考慮してソート
                available_operators.sort(key=lambda op: (
                    slot_id in op.preferred_slots,  # 好ましいスロットを優先
                    op.operator_name  # 名前順で安定化
                ), reverse=True)
                
                # 必要な人数分のオペレータを割り当て
                for i in range(min(additional_needed, len(available_operators))):
                    operator = available_operators[i]
                    assignment = Assignment(
                        operator_name=operator.operator_name,
                        desk_name=desk_name,
                        slot_id=slot_id,
                        date=target_date
                    )
                    assignments.append(assignment)
                    assigned_operators.add(operator.operator_name)
        
        return assignments
    
    def validate_constraints(self, assignments: List[Assignment], 
                           operators: List[OperatorAvailability]) -> List[str]:
        """制約違反をチェック"""
        if not self.constraint_validator:
            return []
        return self.constraint_validator.get_violations(assignments, operators)
    
    def get_constraint_violations(self, assignments: List[Assignment], 
                                operators: List['OperatorAvailability']) -> Dict[str, bool]:
        """各制約の違反状況を取得"""
        if not self.constraint_validator:
            return {}
        return self.constraint_validator.validate_all(assignments, operators)

    def _optimize_assignments_for_shortage(self, assignments: List[Assignment], 
                                         operators: List[OperatorAvailability],
                                         desk_requirements: List[DeskRequirement],
                                         slot_id: str, target_date: datetime) -> List[Assignment]:
        """
        要員不足を解消するための再アサインプロセス（制約考慮版）
        
        Args:
            assignments: 現在の割り当てリスト
            operators: オペレータリスト
            desk_requirements: デスク要件リスト
            slot_id: 対象スロットID
            target_date: 対象日付
            
        Returns:
            最適化された割り当てリスト
        """
        print(f"DEBUG: 要員不足解消プロセス開始 - スロット: {slot_id}")
        
        # 連続スロット制約を取得
        consecutive_break_constraint = None
        if self.constraints:
            consecutive_break_constraint = next((c for c in self.constraints 
                                               if isinstance(c, RequiredBreakAfterConsecutiveSlotsConstraint)), None)
        
        # 各デスクの現在の割り当て状況と要件を確認
        desk_status = {}
        for req in desk_requirements:
            desk_name = req.desk_name
            required_count = req.get_requirement_for_slot(slot_id)
            current_assignments = [a for a in assignments if a.desk_name == desk_name and a.slot_id == slot_id]
            current_count = len(current_assignments)
            
            desk_status[desk_name] = {
                'required': required_count,
                'current': current_count,
                'shortage': max(0, required_count - current_count),
                'surplus': max(0, current_count - required_count),
                'assignments': current_assignments
            }
        
        print(f"DEBUG: デスク状況: {desk_status}")
        
        # アサインされていないオペレータを取得
        assigned_operators = {a.operator_name for a in assignments if a.slot_id == slot_id}
        unassigned_operators = [
            op for op in operators 
            if op.operator_name not in assigned_operators and op.can_work_slot(slot_id)
        ]
        
        print(f"DEBUG: アサインされていないオペレータ: {[op.operator_name for op in unassigned_operators]}")
        
        # 連続スロット制約がある場合、休憩が必要なオペレータを特定
        required_break_operators = set()
        if consecutive_break_constraint:
            for operator in operators:
                if operator.operator_name in assigned_operators:
                    continue  # 既に割り当て済み
                
                # このオペレータの既存割り当てを取得（現在のスロットより前のもののみ）
                # スロットIDから時間を抽出して数値比較
                current_hour = int(slot_id[1:]) if slot_id.startswith('h') else 9
                op_assignments = [a for a in assignments 
                                if a.operator_name == operator.operator_name]
                
                # 現在のスロットより前の割り当てのみをフィルタ
                filtered_assignments = []
                for assignment in op_assignments:
                    assignment_hour = int(assignment.slot_id[1:]) if assignment.slot_id.startswith('h') else 9
                    if assignment_hour < current_hour:
                        filtered_assignments.append(assignment)
                
                filtered_assignments.sort(key=lambda x: (x.date, x.slot_id))
                
                # 連続カウントを計算（休憩後のリセットを考慮）
                consecutive_count = 0
                print(f"DEBUG: {operator.operator_name} - 連続カウント計算開始（スロット{slot_id}）")
                for assignment in filtered_assignments:
                    if assignment.desk_name == consecutive_break_constraint.break_desk_name:
                        print(f"  {assignment.slot_id}: 休憩（カウントリセット: {consecutive_count} → 0）")
                        consecutive_count = 0  # 休憩後は連続カウントをリセット
                    else:
                        consecutive_count += 1
                        print(f"  {assignment.slot_id}: {assignment.desk_name}（連続{consecutive_count}スロット目）")
                
                print(f"DEBUG: {operator.operator_name} - 最終連続カウント: {consecutive_count}, 既存割り当て数: {len(filtered_assignments)}")
                
                # 連続スロット数が上限に達している場合、このスロットで休憩が必要
                if consecutive_count >= consecutive_break_constraint.max_consecutive_slots:
                    required_break_operators.add(operator.operator_name)
        
        print(f"DEBUG: 休憩が必要なオペレータ: {required_break_operators}")
        
        # ステップ1: アサインされていないオペレータを不足デスクに割り当て
        for operator in unassigned_operators:
            # このオペレータが対応可能で、かつ要員不足のデスクを探す
            for desk_name, status in desk_status.items():
                if status['shortage'] <= 0:
                    continue  # 要員不足でない場合はスキップ
                
                if not operator.can_work_desk(desk_name):
                    continue  # 対応可能でないデスクはスキップ
                
                # 連続スロット制約のチェック
                if consecutive_break_constraint:
                    # このオペレータが休憩が必要な場合
                    if operator.operator_name in required_break_operators:
                        # 休憩デスクにのみ割り当て可能
                        if desk_name != consecutive_break_constraint.break_desk_name:
                            continue
                    else:
                        # 通常のデスクにのみ割り当て可能（休憩デスクは除外）
                        if desk_name == consecutive_break_constraint.break_desk_name:
                            continue
                
                # 新しい割り当てを作成
                new_assignment = Assignment(
                    operator_name=operator.operator_name,
                    desk_name=desk_name,
                    slot_id=slot_id,
                    date=target_date
                )
                assignments.append(new_assignment)
                
                # 状況を更新
                desk_status[desk_name]['current'] += 1
                desk_status[desk_name]['shortage'] -= 1
                desk_status[desk_name]['assignments'].append(new_assignment)
                
                print(f"DEBUG: {operator.operator_name} を {desk_name} に再アサイン（要員不足解消）")
                break
        
        # ステップ1-2: 要員満たされているデスクからの最適化
        # アサインされていないオペレータがまだ残っている場合
        remaining_unassigned = [
            op for op in unassigned_operators 
            if op.operator_name not in {a.operator_name for a in assignments if a.slot_id == slot_id}
        ]
        
        if remaining_unassigned:
            print(f"DEBUG: ステップ1-2開始 - 残りのアサインされていないオペレータ: {[op.operator_name for op in remaining_unassigned]}")
            
            for operator in remaining_unassigned:
                # このオペレータが対応可能なデスクを探す
                for desk_name, status in desk_status.items():
                    if not operator.can_work_desk(desk_name):
                        continue  # 対応可能でないデスクはスキップ
                    
                    # 連続スロット制約のチェック
                    if consecutive_break_constraint:
                        # このオペレータが休憩が必要な場合
                        if operator.operator_name in required_break_operators:
                            # 休憩デスクにのみ割り当て可能
                            if desk_name != consecutive_break_constraint.break_desk_name:
                                continue
                        else:
                            # 通常のデスクにのみ割り当て可能
                            if desk_name == consecutive_break_constraint.break_desk_name:
                                continue
                    
                    # このデスクの現在の割り当てを確認
                    current_assignments = status['assignments']
                    
                    # このデスクから移動可能なオペレータを探す
                    for current_assignment in current_assignments[:]:  # コピーでイテレート
                        current_operator_name = current_assignment.operator_name
                        current_operator = next((op for op in operators if op.operator_name == current_operator_name), None)
                        
                        if not current_operator:
                            continue
                        
                        # このオペレータが他の不足デスクに移動可能かチェック
                        for other_desk_name, other_status in desk_status.items():
                            if other_desk_name == desk_name:
                                continue  # 同じデスクはスキップ
                            
                            if other_status['shortage'] <= 0:
                                continue  # 要員不足でないデスクはスキップ
                            
                            if not current_operator.can_work_desk(other_desk_name):
                                continue  # 対応可能でないデスクはスキップ
                            
                            # 連続スロット制約のチェック
                            if consecutive_break_constraint:
                                # このオペレータが休憩が必要な場合
                                if current_operator_name in required_break_operators:
                                    # 休憩デスクにのみ移動可能
                                    if other_desk_name != consecutive_break_constraint.break_desk_name:
                                        continue
                                else:
                                    # 通常のデスクにのみ移動可能
                                    if other_desk_name == consecutive_break_constraint.break_desk_name:
                                        continue
                            
                            # 移動を実行
                            # 1. 現在のデスクからオペレータを削除
                            current_assignment.desk_name = other_desk_name
                            
                            # 状況を更新
                            # 元のデスクの状況を更新
                            desk_status[desk_name]['current'] -= 1
                            desk_status[desk_name]['assignments'].remove(current_assignment)
                            
                            # 新しいデスクの状況を更新
                            desk_status[other_desk_name]['current'] += 1
                            desk_status[other_desk_name]['shortage'] -= 1
                            desk_status[other_desk_name]['assignments'].append(current_assignment)
                            
                            print(f"DEBUG: {current_operator_name} を {desk_name} から {other_desk_name} に移動（要員不足解消のため）")
                            
                            # 2. アサインされていないオペレータを空いたデスクに割り当て
                            new_assignment = Assignment(
                                operator_name=operator.operator_name,
                                desk_name=desk_name,
                                slot_id=slot_id,
                                date=target_date
                            )
                            assignments.append(new_assignment)
                            
                            # 状況を更新
                            desk_status[desk_name]['current'] += 1
                            desk_status[desk_name]['assignments'].append(new_assignment)
                            
                            print(f"DEBUG: {operator.operator_name} を {desk_name} にアサイン（移動後の空き枠）")
                            
                            # このオペレータの処理は完了
                            break
                        
                        # 移動が実行された場合は、このデスクの処理は完了
                        if current_assignment.desk_name != desk_name:
                            break
                    
                    # 移動が実行された場合は、このオペレータの処理は完了
                    if any(a.desk_name != desk_name for a in current_assignments if a.operator_name == operator.operator_name):
                        break
        
        # ステップ2: 余剰デスクから不足デスクへの移動
        # 余剰があるデスクを特定
        surplus_desks = [(desk_name, status) for desk_name, status in desk_status.items() 
                         if status['surplus'] > 0]
        
        # 不足しているデスクを特定
        shortage_desks = [(desk_name, status) for desk_name, status in desk_status.items() 
                          if status['shortage'] > 0]
        
        print(f"DEBUG: 余剰デスク: {[d[0] for d in surplus_desks]}")
        print(f"DEBUG: 不足デスク: {[d[0] for d in shortage_desks]}")
        
        # 余剰デスクから不足デスクへの移動を試行
        for surplus_desk_name, surplus_status in surplus_desks:
            if not shortage_desks:
                break  # 不足デスクがなくなったら終了
            
            # この余剰デスクの割り当てを取得
            surplus_assignments = surplus_status['assignments']
            
            for assignment in surplus_assignments[:]:  # コピーでイテレート
                if not shortage_desks:
                    break
                
                operator_name = assignment.operator_name
                operator = next((op for op in operators if op.operator_name == operator_name), None)
                
                if not operator:
                    continue
                
                # このオペレータが移動可能な不足デスクを探す
                for shortage_desk_name, shortage_status in shortage_desks[:]:  # コピーでイテレート
                    if shortage_status['shortage'] <= 0:
                        continue  # 要員不足でない場合はスキップ
                    
                    if not operator.can_work_desk(shortage_desk_name):
                        continue  # 対応可能でないデスクはスキップ
                    
                    # 連続スロット制約のチェック
                    if consecutive_break_constraint:
                        # このオペレータが休憩が必要な場合
                        if operator.operator_name in required_break_operators:
                            # 休憩デスクにのみ移動可能
                            if shortage_desk_name != consecutive_break_constraint.break_desk_name:
                                continue
                        else:
                            # 通常のデスクにのみ移動可能（休憩デスクは除外）
                            if shortage_desk_name == consecutive_break_constraint.break_desk_name:
                                continue
                    
                    # 割り当てを移動
                    assignment.desk_name = shortage_desk_name
                    
                    # 状況を更新
                    # 元のデスク（余剰デスク）の状況を更新
                    desk_status[surplus_desk_name]['current'] -= 1
                    desk_status[surplus_desk_name]['surplus'] -= 1
                    desk_status[surplus_desk_name]['assignments'].remove(assignment)
                    
                    # 新しいデスク（不足デスク）の状況を更新
                    desk_status[shortage_desk_name]['current'] += 1
                    desk_status[shortage_desk_name]['shortage'] -= 1
                    desk_status[shortage_desk_name]['assignments'].append(assignment)
                    
                    print(f"DEBUG: {operator_name} を {surplus_desk_name} から {shortage_desk_name} に移動")
                    
                    # 不足デスクの状況を再チェック
                    if desk_status[shortage_desk_name]['shortage'] <= 0:
                        shortage_desks = [(d[0], d[1]) for d in shortage_desks 
                                        if d[0] != shortage_desk_name]
                    
                    break
        
        # 最終的な状況を確認
        final_status = {}
        for desk_name, status in desk_status.items():
            final_status[desk_name] = {
                'required': status['required'],
                'current': status['current'],
                'shortage': status['shortage']
            }
        
        print(f"DEBUG: 最適化後のデスク状況: {final_status}")
        
        return assignments

def convert_legacy_operators_to_multi_slot(legacy_ops: List[Dict]) -> List[OperatorAvailability]:
    """従来のオペレータデータをMulti-slot形式に変換（1時間単位）"""
    operators = []
    
    for op_data in legacy_ops:
        # 従来の時間範囲からスロットを推定
        start_hour = op_data["start"]
        end_hour = op_data["end"]
        
        available_slots = set()
        preferred_slots = set()
        
        # 時間範囲に基づいて利用可能なスロットを決定（1時間単位）
        for hour in range(start_hour, end_hour):
            if 9 <= hour < 18:  # 9時から17時まで
                slot_id = f"h{hour:02d}"
                available_slots.add(slot_id)
        
        # 所属デスクを好ましいスロットとして設定
        home_desk = op_data.get("home", "")
        if home_desk:
            # 利用可能なスロットを全て好ましいスロットとして設定
            preferred_slots = available_slots.copy()
        
        # 対応可能なデスクを設定
        desks = set(op_data.get("desks", []))
        
        op = OperatorAvailability(
            operator_name=op_data["name"],
            available_slots=available_slots,
            preferred_slots=preferred_slots,
            desks=desks  # 対応可能なデスクを設定
        )
        operators.append(op)
    
    return operators

def constrained_multi_slot_da_match(hourly_requirements: pd.DataFrame, legacy_ops: List[Dict], 
                                  constraints: Optional[List[Constraint]] = None,
                                  target_date: Optional[datetime] = None) -> Tuple[List[Assignment], pd.DataFrame]:
    """制約付きMulti-slot DAアルゴリズムによるマッチング実行（最適化版）"""
    start_time = time.time()
    
    if target_date is None:
        target_date = datetime.now()
    
    print(f"DEBUG: マッチング開始 - オペレータ数: {len(legacy_ops)}, 制約数: {len(constraints) if constraints else 0}")
    
    # デフォルトスロットを作成
    slots = create_default_slots()
    
    # デスクリストを取得（休憩デスクを追加）
    desks = hourly_requirements["desk"].tolist()
    from utils.constants import BREAK_DESK_NAME
    if BREAK_DESK_NAME not in desks:
        desks.append(BREAK_DESK_NAME)
    
    # 時間単位の要件をスロット単位に変換
    desk_requirements = convert_hourly_to_slots(hourly_requirements)
    
    # レガシーオペレータをMulti-slot形式に変換
    operators = convert_legacy_operators_to_multi_slot(legacy_ops)
    
    # 制約付きアルゴリズムを作成
    algorithm = ConstrainedMultiSlotDAMatchingAlgorithm(slots, desks, constraints)
    
    # 1日分のマッチングを実行
    print("DEBUG: スロット別マッチング開始...")
    assignments = algorithm.match_daily(operators, desk_requirements, target_date)
    
    slot_time = time.time()
    print(f"DEBUG: スロット別マッチング完了 - 時間: {slot_time - start_time:.2f}秒")
    
    # 休憩時間制約がある場合、休憩割り当てを追加
    if constraints:
        # 連続スロット後の必須休憩制約をチェック
        consecutive_break_constraint = next((c for c in constraints if isinstance(c, RequiredBreakAfterConsecutiveSlotsConstraint)), None)
        if consecutive_break_constraint:
            break_assignments = consecutive_break_constraint.get_required_break_assignments(assignments, operators)
            # 休憩割り当てを既存の割り当てに追加
            print(f"DEBUG: 連続スロット後の休憩割り当て数: {len(break_assignments)}")
            for break_assignment in break_assignments:
                print(f"DEBUG: 休憩割り当て: {break_assignment}")
                # 休憩割り当てをAssignmentオブジェクトとして追加
                from models.multi_slot_models import Assignment
                break_assignment_obj = Assignment(
                    operator_name=break_assignment['operator_name'],
                    desk_name=break_assignment['desk_name'],
                    slot_id=break_assignment['slot_id'],
                    date=break_assignment['date']
                )
                assignments.append(break_assignment_obj)
        
        # 長時間シフト後の必須休憩制約をチェック（既存の処理）
        break_constraint = next((c for c in constraints if isinstance(c, RequiredBreakAfterLongShiftConstraint)), None)
        if break_constraint:
            break_assignments = break_constraint.get_break_assignments(assignments, operators)
            print(f"DEBUG: 長時間シフト後の休憩割り当て数: {len(break_assignments)}")
            for break_assignment in break_assignments:
                print(f"DEBUG: 休憩割り当て: {break_assignment}")
    
    # 割り当て結果をDataFrameに変換
    print("DEBUG: DataFrame変換開始...")
    schedule = convert_assignments_to_dataframe(assignments, slots, desks, target_date)
    
    end_time = time.time()
    print(f"DEBUG: マッチング完了 - 総時間: {end_time - start_time:.2f}秒, 割り当て数: {len(assignments)}")
    
    # キャッシュをクリア（メモリ使用量削減）
    if algorithm.constraint_validator:
        algorithm.constraint_validator.clear_cache()
    
    return assignments, schedule

def convert_assignments_to_dataframe(assignments: List[Assignment], 
                                   slots: List[TimeSlot], 
                                   desks: List[str], 
                                   target_date: datetime) -> pd.DataFrame:
    """割り当て結果をDataFrameに変換（1時間単位）"""
    # 1時間単位のスロットの時間定義
    slot_hours = {f"h{hour:02d}": 1.0 for hour in range(9, 18)}
    
    # 各デスクの各スロットの割り当てを集計
    schedule_data = []
    
    for desk in desks:
        row = {"desk": desk}
        
        for slot in slots:
            # このデスクのこのスロットの割り当てをカウント
            slot_assignments = [
                a for a in assignments 
                if a.desk_name == desk and a.slot_id == slot.slot_id
            ]
            
            # 割り当て人数を記録
            row[slot.slot_id] = str(len(slot_assignments))
            
            # 割り当てられたオペレータ名も記録
            if slot_assignments:
                operator_names = [a.operator_name for a in slot_assignments]
                # 休憩デスクの場合は特別な表示
                if desk == "休憩":
                    row[f"{slot.slot_id}_operators"] = ", ".join([f"{name} (休憩)" for name in operator_names])
                else:
                    row[f"{slot.slot_id}_operators"] = ", ".join(operator_names)
            else:
                row[f"{slot.slot_id}_operators"] = ""
        
        schedule_data.append(row)
    
    # DataFrameを作成
    schedule_df = pd.DataFrame(schedule_data)
    
    return schedule_df 