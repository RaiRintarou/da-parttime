"""
Multi-slot日次モデル対応のDAアルゴリズム

このモジュールは、時間単位からスロット単位の日次モデルに拡張された
DA（Deferred Acceptance）アルゴリズムを提供します。
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, date
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models.multi_slot_models import (
    TimeSlot, DailySchedule, OperatorAvailability, 
    DeskRequirement, Assignment, MultiSlotScheduler,
    create_default_slots, convert_hourly_to_slots
)

class MultiSlotDAMatchingAlgorithm:
    """Multi-slot日次モデル対応のDAアルゴリズム"""
    
    def __init__(self, slots: List[TimeSlot], desks: List[str]):
        self.slots = slots
        self.slot_ids = [slot.slot_id for slot in slots]
        self.desks = desks
        self.scheduler = MultiSlotScheduler(slots)
    
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
        """1日分のDAアルゴリズムによるマッチング実行"""
        assignments = []
        
        # 各スロットでDAアルゴリズムを実行
        for slot in self.slots:
            print(f"DEBUG: スロット {slot.slot_id} のマッチング開始")
            
            # 初期マッチングを実行
            slot_assignments = self._match_slot(
                operators, desk_requirements, slot.slot_id, target_date
            )
            assignments.extend(slot_assignments)
            
            # 要員不足解消プロセスを実行
            print(f"DEBUG: スロット {slot.slot_id} の要員不足解消プロセス開始")
            assignments = self._optimize_assignments_for_shortage(
                assignments, operators, desk_requirements, slot.slot_id, target_date
            )
            
            print(f"DEBUG: スロット {slot.slot_id} のマッチング完了 - 割り当て数: {len([a for a in assignments if a.slot_id == slot.slot_id])}")
        
        return assignments
    
    def _match_slot(self, operators: List[OperatorAvailability], 
                   desk_requirements: List[DeskRequirement], 
                   slot_id: str, target_date: datetime) -> List[Assignment]:
        """特定のスロットでのDAアルゴリズム実行"""
        # このスロットで利用可能なオペレータを取得
        available_ops = [
            op for op in operators 
            if op.can_work_slot(slot_id)
        ]
        
        if not available_ops:
            return []
        
        # 各デスクの要件を取得
        slot_requirements = {}
        for desk_req in desk_requirements:
            slot_requirements[desk_req.desk_name] = desk_req.get_requirement_for_slot(slot_id)
        
        # 各デスクのオペレータ優先順位を作成
        desk_preferences = self._create_slot_preferences(operators)
        
        # 各オペレータのデスク優先順位を作成
        op_preferences = self._create_operator_slot_preferences(operators)
        
        # 初期化
        proposals = {op.operator_name: 0 for op in available_ops}
        desk_assignments = {desk: [] for desk in self.desks}
        matches = {op.operator_name: "" for op in available_ops}
        
        # DAアルゴリズムのメインループ
        while True:
            # まだマッチしていないオペレータを取得
            unmatched_ops = [op for op in available_ops if matches[op.operator_name] == ""]
            
            if not unmatched_ops:
                break
            
            for op in unmatched_ops:
                op_prefs = op_preferences[op.operator_name].get(slot_id, [])
                if proposals[op.operator_name] >= len(op_prefs):
                    continue  # このオペレータは全てのデスクに提案済み
                
                # 次に提案するデスクを取得
                target_desk = op_prefs[proposals[op.operator_name]]
                
                # そのデスクの要件をチェック
                if slot_requirements.get(target_desk, 0) > 0:
                    # デスクに空きがある場合
                    desk_assignments[target_desk].append(op.operator_name)
                    matches[op.operator_name] = target_desk
                    slot_requirements[target_desk] -= 1
                else:
                    # デスクが満杯の場合、優先順位に基づいて競合を解決
                    if desk_assignments[target_desk]:
                        current_ops = desk_assignments[target_desk]
                        desk_pref = desk_preferences[target_desk].get(slot_id, [])
                        
                        # 優先度の低いオペレータを見つける
                        worst_op = None
                        worst_rank = -1
                        
                        for current_op in current_ops:
                            if current_op in desk_pref:
                                rank = desk_pref.index(current_op)
                                if rank > worst_rank:
                                    worst_rank = rank
                                    worst_op = current_op
                        
                        # 新しいオペレータの優先度をチェック
                        if op.operator_name in desk_pref and worst_op is not None:
                            new_rank = desk_pref.index(op.operator_name)
                            if new_rank < worst_rank:
                                # 新しいオペレータの方が優先度が高い場合、置き換え
                                desk_assignments[target_desk].remove(worst_op)
                                matches[worst_op] = ""
                                desk_assignments[target_desk].append(op.operator_name)
                                matches[op.operator_name] = target_desk
                
                proposals[op.operator_name] += 1
        
        # 割り当て結果をAssignmentオブジェクトに変換
        assignments = []
        for op_name, assigned_desk in matches.items():
            if assigned_desk:
                assignment = Assignment(
                    operator_name=op_name,
                    desk_name=assigned_desk,
                    slot_id=slot_id,
                    date=target_date
                )
                assignments.append(assignment)
        
        return assignments
    
    def validate_constraints(self, assignments: List[Assignment], 
                           operators: List[OperatorAvailability]) -> List[str]:
        """制約違反をチェック"""
        errors = []
        
        # 重複チェック
        assignment_keys = set()
        for assignment in assignments:
            key = (assignment.operator_name, assignment.slot_id, assignment.date)
            if key in assignment_keys:
                errors.append(f"重複割り当て: {assignment.operator_name} が {assignment.slot_id} に重複して割り当て")
            assignment_keys.add(key)
        
        # 労働時間制約チェック
        for op in operators:
            daily_hours = self.scheduler.calculate_work_hours(
                assignments, op.operator_name, assignments[0].date if assignments else datetime.now()
            )
            if daily_hours > op.max_work_hours_per_day:
                errors.append(f"労働時間超過: {op.operator_name} の労働時間が {daily_hours}h で上限 {op.max_work_hours_per_day}h を超過")
        
        return errors

    def _optimize_assignments_for_shortage(self, assignments: List[Assignment], 
                                         operators: List[OperatorAvailability],
                                         desk_requirements: List[DeskRequirement],
                                         slot_id: str, target_date: datetime) -> List[Assignment]:
        """
        要員不足を解消するための再アサインプロセス
        
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
        
        # ステップ1: アサインされていないオペレータを不足デスクに割り当て
        for operator in unassigned_operators:
            # このオペレータが対応可能で、かつ要員不足のデスクを探す
            for desk_name, status in desk_status.items():
                if status['shortage'] <= 0:
                    continue  # 要員不足でない場合はスキップ
                
                if not operator.can_work_desk(desk_name):
                    continue  # 対応可能でないデスクはスキップ
                
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
        
        # デバッグ情報を出力
        print(f"DEBUG: {op_data['name']} - 時間: {start_hour}-{end_hour}, 利用可能スロット: {available_slots}, 対応可能デスク: {desks}")
        
        op = OperatorAvailability(
            operator_name=op_data["name"],
            available_slots=available_slots,
            preferred_slots=preferred_slots,
            desks=desks  # 対応可能なデスクを設定
        )
        operators.append(op)
    
    return operators

def multi_slot_da_match(hourly_requirements: pd.DataFrame, legacy_ops: List[Dict], 
                       target_date: Optional[datetime] = None) -> Tuple[List[Assignment], pd.DataFrame]:
    """Multi-slot DAアルゴリズムによるマッチング"""
    if target_date is None:
        target_date = datetime.now()
    
    # デフォルトスロットを作成
    slots = create_default_slots()
    
    # デスクリストを取得
    desks = hourly_requirements["desk"].astype(str).tolist()
    
    # 時間単位の要件をスロット単位に変換
    desk_requirements = convert_hourly_to_slots(hourly_requirements)
    
    # 従来のオペレータデータをMulti-slot形式に変換
    operators = convert_legacy_operators_to_multi_slot(legacy_ops)
    
    # DAアルゴリズムを実行
    da_algorithm = MultiSlotDAMatchingAlgorithm(slots, desks)
    assignments = da_algorithm.match_daily(operators, desk_requirements, target_date)
    
    # 結果を従来のDataFrame形式に変換（後方互換性のため）
    schedule_df = convert_assignments_to_dataframe(assignments, slots, desks, target_date)
    
    return assignments, schedule_df

def convert_assignments_to_dataframe(assignments: List[Assignment], 
                                   slots: List[TimeSlot], 
                                   desks: List[str], 
                                   target_date: datetime) -> pd.DataFrame:
    """割り当て結果を従来のDataFrame形式に変換（1時間単位）"""
    # オペレータ名のリストを取得
    operator_names = list(set(assignment.operator_name for assignment in assignments))
    
    # 従来の時間列を作成（9-17時）
    hours = list(range(9, 18))
    cols = ["desk"] + [f"h{h:02d}" for h in hours]
    
    # 1時間単位のスロットから時間へのマッピング
    slot_to_hours = {f"h{hour:02d}": [hour] for hour in range(9, 18)}
    
    # 各オペレータのスケジュールを作成
    schedule = {}
    for op_name in operator_names:
        schedule[op_name] = {f"h{h:02d}": "" for h in hours}
        
        # このオペレータの割り当てを処理
        for assignment in assignments:
            if assignment.operator_name == op_name:
                slot_id = assignment.slot_id
                desk_name = assignment.desk_name
                
                # スロットに対応する時間にデスク名を設定
                if slot_id in slot_to_hours:
                    for hour in slot_to_hours[slot_id]:
                        if 9 <= hour < 18:  # 従来の時間範囲内のみ
                            col_name = f"h{hour:02d}"
                            schedule[op_name][col_name] = desk_name
    
    return pd.DataFrame(schedule).T 