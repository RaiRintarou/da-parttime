"""
Hard Constraint DSL (Domain Specific Language)

このモジュールは、シフト割り当てにおける制約を定義するための
ドメイン特化言語（DSL）を提供します。
"""

from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import re

if TYPE_CHECKING:
    from .multi_slot_models import Assignment, OperatorAvailability

class ConstraintType(Enum):
    """制約タイプの定義"""
    MIN_REST_HOURS = "min_rest_hours"           # 最小休息時間
    MAX_CONSECUTIVE_DAYS = "max_consecutive_days"  # 最大連勤日数
    MAX_WEEKLY_HOURS = "max_weekly_hours"       # 最大週間労働時間
    MIN_BREAK_BETWEEN_SHIFTS = "min_break_between_shifts"  # シフト間最小休憩
    MAX_NIGHT_SHIFTS_PER_WEEK = "max_night_shifts_per_week"  # 週間最大夜勤数
    REQUIRED_DAY_OFF_AFTER_NIGHT = "required_day_off_after_night"  # 夜勤後の必須休日
    REQUIRED_BREAK_AFTER_LONG_SHIFT = "required_break_after_long_shift"  # 長時間シフト後の必須休憩
    REQUIRED_BREAK_AFTER_CONSECUTIVE_SLOTS = "required_break_after_consecutive_slots"  # 連続スロット後の必須休憩
    SKILL_REQUIREMENT = "skill_requirement"     # スキル要件
    PREFERRED_SHIFT_PATTERN = "preferred_shift_pattern"  # 好ましいシフトパターン

@dataclass
class Constraint:
    """制約の基本クラス"""
    constraint_type: ConstraintType
    description: str
    is_hard: bool = True  # True: ハード制約, False: ソフト制約
    weight: float = 1.0   # ソフト制約の場合の重み
    
    def validate(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> bool:
        """制約の妥当性をチェック"""
        raise NotImplementedError("サブクラスで実装してください")
    
    def get_violation_score(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> float:
        """制約違反のスコアを計算（ソフト制約用）"""
        return 0.0 if self.validate(assignments, operators) else self.weight

@dataclass
class MinRestHoursConstraint(Constraint):
    """最小休息時間制約"""
    min_rest_hours: float = 11.0
    
    def __init__(self, min_rest_hours: float = 11.0, **kwargs):
        super().__init__(ConstraintType.MIN_REST_HOURS, 
                        f"最小休息時間: {min_rest_hours}時間", **kwargs)
        self.min_rest_hours = min_rest_hours
    
    def validate(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> bool:
        """最小休息時間制約の検証"""
        from .multi_slot_models import Assignment
        
        for operator in operators:
            op_assignments = [a for a in assignments if a.operator_name == operator.operator_name]
            if len(op_assignments) < 2:
                continue
            
            # 日付順にソート
            op_assignments.sort(key=lambda x: x.date)
            
            for i in range(len(op_assignments) - 1):
                current = op_assignments[i]
                next_shift = op_assignments[i + 1]
                
                # 連続する日の場合のみチェック
                if (next_shift.date - current.date).days == 1:
                    # 前日の終了時刻と翌日の開始時刻の間隔を計算
                    # 簡略化のため、スロットの終了時刻を使用
                    rest_hours = self._calculate_rest_hours(current, next_shift)
                    if rest_hours < self.min_rest_hours:
                        return False
        
        return True
    
    def _calculate_rest_hours(self, current: 'Assignment', next_shift: 'Assignment') -> float:
        """休息時間を計算"""
        # スロットIDごとの開始・終了時刻定義
        slot_times = {
            "morning": (9, 13),
            "afternoon": (13, 17),
            "evening": (17, 21),
            "night": (22, 6),
        }
        # 1時間単位スロット
        if current.slot_id.startswith('h'):
            current_hour = int(current.slot_id[1:])
            current_end = current_hour + 1
        elif current.slot_id in slot_times:
            current_end = slot_times[current.slot_id][1]
        else:
            current_end = 9 + 1
        if next_shift.slot_id.startswith('h'):
            next_hour = int(next_shift.slot_id[1:])
            next_start = next_hour
        elif next_shift.slot_id in slot_times:
            next_start = slot_times[next_shift.slot_id][0]
        else:
            next_start = 9
        # 夜勤（22-6時）の場合、翌朝6時終了
        if current.slot_id == "night":
            current_end = 6
        if next_shift.slot_id == "night":
            next_start = 22
        rest_hours = (next_start - current_end) % 24
        return rest_hours

@dataclass
class MaxConsecutiveDaysConstraint(Constraint):
    """最大連勤日数制約"""
    max_consecutive_days: int = 6
    
    def __init__(self, max_consecutive_days: int = 6, **kwargs):
        super().__init__(ConstraintType.MAX_CONSECUTIVE_DAYS,
                        f"最大連勤日数: {max_consecutive_days}日", **kwargs)
        self.max_consecutive_days = max_consecutive_days
    
    def validate(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> bool:
        """最大連勤日数制約の検証"""
        from .multi_slot_models import Assignment
        
        for operator in operators:
            op_assignments = [a for a in assignments if a.operator_name == operator.operator_name]
            if not op_assignments:
                continue
            
            # 日付順にソート
            op_assignments.sort(key=lambda x: x.date)
            
            consecutive_days = 1
            max_consecutive = 1
            
            for i in range(1, len(op_assignments)):
                prev_date = op_assignments[i-1].date
                curr_date = op_assignments[i].date
                
                if (curr_date - prev_date).days == 1:
                    consecutive_days += 1
                    max_consecutive = max(max_consecutive, consecutive_days)
                else:
                    consecutive_days = 1
            
            if max_consecutive > self.max_consecutive_days:
                return False
        
        return True

@dataclass
class MaxWeeklyHoursConstraint(Constraint):
    """最大週間労働時間制約"""
    max_weekly_hours: float = 40.0
    
    def __init__(self, max_weekly_hours: float = 40.0, **kwargs):
        super().__init__(ConstraintType.MAX_WEEKLY_HOURS,
                        f"最大週間労働時間: {max_weekly_hours}時間", **kwargs)
        self.max_weekly_hours = max_weekly_hours
    
    def validate(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> bool:
        """最大週間労働時間制約の検証"""
        from .multi_slot_models import Assignment
        
        # スロットIDごとの労働時間定義
        slot_hours = {f"h{hour:02d}": 1.0 for hour in range(9, 18)}
        # 追加: 代表的なスロット名も対応
        slot_hours.update({
            "morning": 4.0,   # 例: 9-13時
            "afternoon": 4.0, # 例: 13-17時
            "evening": 4.0,   # 例: 17-21時
            "night": 8.0      # 例: 22-6時
        })
        
        for operator in operators:
            op_assignments = [a for a in assignments if a.operator_name == operator.operator_name]
            if not op_assignments:
                continue
            
            # 週ごとにグループ化
            weekly_hours = {}
            for assignment in op_assignments:
                week_start = assignment.date - timedelta(days=assignment.date.weekday())
                week_key = week_start.strftime("%Y-%W")
                
                if week_key not in weekly_hours:
                    weekly_hours[week_key] = 0.0
                
                weekly_hours[week_key] += slot_hours.get(assignment.slot_id, 0.0)
            
            # 各週の労働時間をチェック
            for week_hours in weekly_hours.values():
                if week_hours > self.max_weekly_hours:
                    return False
        
        return True

@dataclass
class MaxNightShiftsPerWeekConstraint(Constraint):
    """週間最大夜勤数制約"""
    max_night_shifts_per_week: int = 2
    
    def __init__(self, max_night_shifts_per_week: int = 2, **kwargs):
        super().__init__(ConstraintType.MAX_NIGHT_SHIFTS_PER_WEEK,
                        f"週間最大夜勤数: {max_night_shifts_per_week}回", **kwargs)
        self.max_night_shifts_per_week = max_night_shifts_per_week
    
    def validate(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> bool:
        """週間最大夜勤数制約の検証"""
        from .multi_slot_models import Assignment
        
        for operator in operators:
            op_assignments = [a for a in assignments if a.operator_name == operator.operator_name]
            if not op_assignments:
                continue
            
            # 週ごとにグループ化
            weekly_night_shifts = {}
            for assignment in op_assignments:
                # 夜勤の判定（22時以降または6時以前のスロット）
                is_night_shift = False
                if assignment.slot_id.startswith('h'):
                    hour = int(assignment.slot_id[1:])
                    is_night_shift = hour >= 22 or hour <= 6
                elif assignment.slot_id == "night":
                    is_night_shift = True
                
                if is_night_shift:
                    week_start = assignment.date - timedelta(days=assignment.date.weekday())
                    week_key = week_start.strftime("%Y-%W")
                    
                    if week_key not in weekly_night_shifts:
                        weekly_night_shifts[week_key] = 0
                    
                    weekly_night_shifts[week_key] += 1
            
            # 各週の夜勤数をチェック
            for night_shifts in weekly_night_shifts.values():
                if night_shifts > self.max_night_shifts_per_week:
                    return False
        
        return True

@dataclass
class RequiredDayOffAfterNightConstraint(Constraint):
    """夜勤後の必須休日制約"""
    
    def __init__(self, **kwargs):
        super().__init__(ConstraintType.REQUIRED_DAY_OFF_AFTER_NIGHT,
                        "夜勤後の必須休日", **kwargs)
    
    def validate(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> bool:
        """夜勤後の必須休日制約の検証"""
        from .multi_slot_models import Assignment
        
        for operator in operators:
            op_assignments = [a for a in assignments if a.operator_name == operator.operator_name]
            if not op_assignments:
                continue
            
            # 日付順にソート
            op_assignments.sort(key=lambda x: x.date)
            
            for i, assignment in enumerate(op_assignments):
                # 夜勤の判定（22時以降または6時以前のスロット）
                is_night_shift = False
                if assignment.slot_id.startswith('h'):
                    hour = int(assignment.slot_id[1:])
                    is_night_shift = hour >= 22 or hour <= 6
                elif assignment.slot_id == "night":
                    is_night_shift = True
                
                if is_night_shift:
                    # 夜勤の翌日をチェック
                    next_day = assignment.date + timedelta(days=1)
                    
                    # 翌日に割り当てがあるかチェック
                    next_day_assignments = [a for a in op_assignments if a.date == next_day]
                    if next_day_assignments:
                        return False
        
        return True

@dataclass
class RequiredBreakAfterLongShiftConstraint(Constraint):
    """長時間シフト後の必須休憩制約"""
    long_shift_threshold_hours: float = 5.0  # 長時間シフトの閾値（時間）
    required_break_hours: float = 1.0        # 必須休憩時間（時間）
    
    def __init__(self, long_shift_threshold_hours: float = 5.0, required_break_hours: float = 1.0, **kwargs):
        super().__init__(ConstraintType.REQUIRED_BREAK_AFTER_LONG_SHIFT,
                        f"連続稼働{long_shift_threshold_hours}時間以上後の{required_break_hours}時間休憩必須", **kwargs)
        self.long_shift_threshold_hours = long_shift_threshold_hours
        self.required_break_hours = required_break_hours
    
    def validate(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> bool:
        """長時間シフト後の必須休憩制約の検証"""
        from .multi_slot_models import Assignment
        
        # 1時間単位のスロットの時間定義
        slot_hours = {f"h{hour:02d}": 1.0 for hour in range(9, 18)}
        
        for operator in operators:
            op_assignments = [a for a in assignments if a.operator_name == operator.operator_name]
            if not op_assignments:
                continue
            
            # 日付順にソート
            op_assignments.sort(key=lambda x: x.date)
            
            for i, assignment in enumerate(op_assignments):
                current_hours = slot_hours.get(assignment.slot_id, 0.0)
                
                # 現在のシフトが長時間シフトの場合
                if current_hours >= self.long_shift_threshold_hours:
                    # 同日の後続シフトをチェック
                    same_day_assignments = [a for a in op_assignments if a.date == assignment.date]
                    current_index = same_day_assignments.index(assignment)
                    
                    # 後続のシフトがある場合、休憩時間をチェック
                    if current_index < len(same_day_assignments) - 1:
                        next_assignment = same_day_assignments[current_index + 1]
                        break_hours = self._calculate_break_hours(assignment, next_assignment)
                        
                        if break_hours < self.required_break_hours:
                            return False
        
        return True
    
    def _calculate_break_hours(self, current: 'Assignment', next_shift: 'Assignment') -> float:
        """休憩時間を計算"""
        # 1時間単位のスロットタイプに基づいて開始・終了時刻を推定
        current_hour = int(current.slot_id[1:]) if current.slot_id.startswith('h') else 9
        next_hour = int(next_shift.slot_id[1:]) if next_shift.slot_id.startswith('h') else 9
        
        current_start, current_end = current_hour, current_hour + 1
        next_start, next_end = next_hour, next_hour + 1
        
        # 休憩時間を計算
        if current_end <= next_start:
            # 同日内の休憩
            break_hours = next_start - current_end
        else:
            # 夜勤から翌日への休憩
            break_hours = (24 - current_end) + next_start
        
        return break_hours
    
    def get_break_assignments(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> List[Dict[str, Any]]:
        """必要な休憩割り当てを取得（既存の時間帯に割り当て）"""
        from .multi_slot_models import Assignment
        
        # 1時間単位のスロットの時間定義
        slot_hours = {f"h{hour:02d}": 1.0 for hour in range(9, 18)}
        
        break_assignments = []
        
        for operator in operators:
            op_assignments = [a for a in assignments if a.operator_name == operator.operator_name]
            if not op_assignments:
                continue
            
            # 日付順にソート
            op_assignments.sort(key=lambda x: x.date)
            
            for i, assignment in enumerate(op_assignments):
                current_hours = slot_hours.get(assignment.slot_id, 0.0)
                
                # 現在のシフトが長時間シフトの場合
                if current_hours >= self.long_shift_threshold_hours:
                    # 同日の後続シフトをチェック
                    same_day_assignments = [a for a in op_assignments if a.date == assignment.date]
                    current_index = same_day_assignments.index(assignment)
                    
                    # 後続のシフトがある場合、休憩割り当てを追加
                    if current_index < len(same_day_assignments) - 1:
                        # 連続勤務の真ん中付近に休憩を割り当て
                        break_hour = self._calculate_break_hour(assignment, same_day_assignments[current_index + 1])
                        
                        break_assignments.append({
                            'operator_name': operator.operator_name,
                            'date': assignment.date,
                            'break_hour': break_hour,
                            'desk_name': '休憩',
                            'reason': f"連続稼働{current_hours}時間後の必須休憩"
                        })
        
        return break_assignments
    
    def _calculate_break_hour(self, current: 'Assignment', next_shift: 'Assignment') -> int:
        """休憩を割り当てる時間帯を計算（連続勤務の真ん中付近）"""
        # 1時間単位のスロットタイプに基づいて開始・終了時刻を推定
        current_hour = int(current.slot_id[1:]) if current.slot_id.startswith('h') else 9
        next_hour = int(next_shift.slot_id[1:]) if next_shift.slot_id.startswith('h') else 9
        
        current_start, current_end = current_hour, current_hour + 1
        next_start, next_end = next_hour, next_hour + 1
        
        # 連続勤務の開始と終了を計算
        if current_end <= next_start:
            # 同日内の連続勤務
            work_start = current_start
            work_end = next_end
        else:
            # 夜勤から翌日への連続勤務
            work_start = current_start
            work_end = next_end
        
        # 連続勤務の真ん中付近の時間を返す
        break_hour = work_start + (work_end - work_start) // 2
        
        # 9-17時の範囲内に収める
        break_hour = max(9, min(17, break_hour))
        
        return break_hour

@dataclass
class RequiredBreakAfterConsecutiveSlotsConstraint(Constraint):
    """
    連続スロット後の必須休憩制約
    
    指定されたスロット数以上連続で働いた場合、次のスロットで休憩を必須とする制約。
    休憩アサイン後は連続カウントが0にリセットされ、再度デスクにアサイン可能な状態になります。
    
    Attributes:
        max_consecutive_slots (int): 最大連続スロット数（この数以上連続勤務すると休憩必須）
        break_desk_name (str): 休憩デスク名（休憩時に割り当てられるデスク名）
    """
    max_consecutive_slots: int = 5  # 最大連続スロット数
    break_desk_name: str = "休憩"   # 休憩デスク名
    
    def __init__(self, max_consecutive_slots: int = 5, break_desk_name: str = "休憩", **kwargs):
        super().__init__(ConstraintType.REQUIRED_BREAK_AFTER_CONSECUTIVE_SLOTS,
                        f"連続{max_consecutive_slots}スロット後の{break_desk_name}必須", **kwargs)
        self.max_consecutive_slots = max_consecutive_slots
        self.break_desk_name = break_desk_name
    
    def validate(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> bool:
        """
        連続スロット後の必須休憩制約の検証（最適化版）
        
        各オペレータの割り当てを時系列順にチェックし、連続スロット数が上限に達した場合、
        次のスロットで休憩デスクにアサインされているかを検証します。
        
        休憩デスクにアサインされた後は連続カウントが0にリセットされ、
        再度通常のデスクにアサイン可能な状態になります。
        
        Args:
            assignments: 割り当てリスト
            operators: オペレータ利用可能性リスト
            
        Returns:
            bool: 制約を満たしている場合はTrue、違反している場合はFalse
        """
        from .multi_slot_models import Assignment
        
        # オペレータ別に割り当てをグループ化（一度だけ実行）
        operator_assignments = {}
        for assignment in assignments:
            if assignment.operator_name not in operator_assignments:
                operator_assignments[assignment.operator_name] = []
            operator_assignments[assignment.operator_name].append(assignment)
        
        for operator in operators:
            op_assignments = operator_assignments.get(operator.operator_name, [])
            if not op_assignments:
                continue
            
            # 日付とスロット順にソート（一度だけ実行）
            op_assignments.sort(key=lambda x: (x.date, x.slot_id))
            
            consecutive_count = 0
            for i, assignment in enumerate(op_assignments):
                # 休憩デスクの場合は連続カウントをリセット
                # これにより、休憩後は再度デスクにアサイン可能な状態になります
                if assignment.desk_name == self.break_desk_name:
                    consecutive_count = 0
                    continue
                
                # 通常のデスクの場合は連続カウントを増加
                consecutive_count += 1
                
                # 連続スロット数が上限に達した場合、次のスロットで休憩が必要
                if consecutive_count >= self.max_consecutive_slots:
                    # 次のスロットがあるかチェック
                    if i + 1 < len(op_assignments):
                        next_assignment = op_assignments[i + 1]
                        # 次のスロットが休憩デスクでない場合は制約違反
                        if next_assignment.desk_name != self.break_desk_name:
                            return False  # 早期終了
                    consecutive_count = 0  # 休憩後はリセット
        
        return True
    
    def get_required_break_assignments(self, assignments: List['Assignment'], 
                                     operators: List['OperatorAvailability']) -> List[Dict[str, Any]]:
        """
        必要な休憩割り当てを取得
        
        連続スロット数が上限に達した場合、次のスロットに休憩割り当てを生成します。
        休憩アサイン後は連続カウントが0にリセットされ、再度デスクにアサイン可能な状態になります。
        
        Args:
            assignments: 現在の割り当てリスト
            operators: オペレータ利用可能性リスト
            
        Returns:
            List[Dict[str, Any]]: 必要な休憩割り当てのリスト
        """
        from .multi_slot_models import Assignment
        
        break_assignments = []
        
        # 利用可能なスロットを定義（9時から17時まで）
        available_slots = [f"h{hour:02d}" for hour in range(9, 18)]
        
        for operator in operators:
            op_assignments = [a for a in assignments if a.operator_name == operator.operator_name]
            if not op_assignments:
                continue
            
            # 日付とスロット順にソート
            op_assignments.sort(key=lambda x: (x.date, x.slot_id))
            
            consecutive_count = 0
            for i, assignment in enumerate(op_assignments):
                # 休憩デスクの場合は連続カウントをリセット
                # これにより、休憩後は再度デスクにアサイン可能な状態になります
                if assignment.desk_name == self.break_desk_name:
                    consecutive_count = 0
                    continue
                
                # 通常のデスクの場合は連続カウントを増加
                consecutive_count += 1
                
                # 連続スロット数が上限に達した場合、次のスロットで休憩が必要
                if consecutive_count >= self.max_consecutive_slots:
                    # 現在のスロットの次のスロットを計算
                    current_slot_index = available_slots.index(assignment.slot_id)
                    if current_slot_index + 1 < len(available_slots):
                        next_slot_id = available_slots[current_slot_index + 1]
                        
                        # 次のスロットに既に割り当てがあるかチェック
                        next_slot_assignment = next((a for a in op_assignments 
                                                   if a.slot_id == next_slot_id and a.date == assignment.date), None)
                        
                        # 次のスロットに割り当てがない場合、または休憩デスクでない場合は休憩割り当てを追加
                        if not next_slot_assignment or next_slot_assignment.desk_name != self.break_desk_name:
                            break_assignments.append({
                                'operator_name': operator.operator_name,
                                'date': assignment.date,
                                'slot_id': next_slot_id,
                                'desk_name': self.break_desk_name,
                                'reason': f"連続{consecutive_count}スロット後の必須休憩"
                            })
                    
                    consecutive_count = 0  # 休憩後はリセット
        
        return break_assignments

class ConstraintParser:
    """制約DSLパーサー"""
    
    def __init__(self):
        self.constraint_patterns = {
            r'max_consecutive_days\s*[:=]\s*(\d+)': self._parse_max_consecutive_days,
            r'max_weekly_hours\s*[:=]\s*(\d+(?:\.\d+)?)': self._parse_max_weekly_hours,
            r'max_night_shifts_per_week\s*[:=]\s*(\d+)': self._parse_max_night_shifts,
            r'required_break_after_long_shift\s*[:=]\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)': self._parse_required_break_after_long_shift,
            r'required_break_after_consecutive_slots\s*[:=]\s*(\d+)': self._parse_required_break_after_consecutive_slots,
        }
    
    def parse_constraints(self, constraint_text: str) -> List[Constraint]:
        """制約テキストを解析して制約リストを生成"""
        constraints = []
        
        # 各制約タイプの正規表現パターン（: または = に対応）
        patterns = [
            (r'max_consecutive_days\s*[:=]\s*(\d+)', self._parse_max_consecutive_days),
            (r'max_weekly_hours\s*[:=]\s*(\d+(?:\.\d+)?)', self._parse_max_weekly_hours),
            (r'max_night_shifts_per_week\s*[:=]\s*(\d+)', self._parse_max_night_shifts),
            (r'required_break_after_long_shift\s*[:=]\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)', self._parse_required_break_after_long_shift),
            (r'required_break_after_consecutive_slots\s*[:=]\s*(\d+)', self._parse_required_break_after_consecutive_slots),
        ]
        
        for pattern, parser_func in patterns:
            matches = re.finditer(pattern, constraint_text, re.IGNORECASE)
            for match in matches:
                constraint = parser_func(match)
                if constraint:
                    constraints.append(constraint)
        
        return constraints
    
    def _parse_max_consecutive_days(self, match) -> Constraint:
        days = int(match.group(1))
        return MaxConsecutiveDaysConstraint(max_consecutive_days=days)
    
    def _parse_max_weekly_hours(self, match) -> Constraint:
        hours = float(match.group(1))
        return MaxWeeklyHoursConstraint(max_weekly_hours=hours)
    
    def _parse_max_night_shifts(self, match) -> Constraint:
        shifts = int(match.group(1))
        return MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=shifts)
    
    def _parse_required_break_after_long_shift(self, match) -> Constraint:
        """長時間シフト後の必須休憩制約をパース"""
        threshold = float(match.group(1))
        break_hours = float(match.group(2))
        return RequiredBreakAfterLongShiftConstraint(
            long_shift_threshold_hours=threshold,
            required_break_hours=break_hours
        )

    def _parse_required_break_after_consecutive_slots(self, match) -> Constraint:
        """連続スロット後の必須休憩制約をパース"""
        slots = int(match.group(1))
        return RequiredBreakAfterConsecutiveSlotsConstraint(max_consecutive_slots=slots)

class ConstraintValidator:
    """制約バリデーター"""
    
    def __init__(self, constraints: List[Constraint]):
        self.constraints = constraints
        self._validation_cache = {}  # 検証結果のキャッシュ
    
    def _get_cache_key(self, assignments: List['Assignment']) -> str:
        """キャッシュキーを生成"""
        # 割り当てのハッシュを生成（日付、スロットID、オペレータ名、デスク名）
        assignment_hash = hash(tuple((a.date, a.slot_id, a.operator_name, a.desk_name) for a in assignments))
        return str(assignment_hash)
    
    def validate_all(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> Dict[str, bool]:
        """全ての制約を検証（キャッシュ付き）"""
        cache_key = self._get_cache_key(assignments)
        
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]
        
        results = {}
        
        for constraint in self.constraints:
            constraint_name = constraint.constraint_type.value
            results[constraint_name] = constraint.validate(assignments, operators)
        
        # キャッシュに保存
        self._validation_cache[cache_key] = results
        
        return results
    
    def get_violations(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> List[str]:
        """違反している制約のリストを取得（早期終了付き）"""
        violations = []
        validation_results = self.validate_all(assignments, operators)
        
        for constraint_name, is_valid in validation_results.items():
            if not is_valid:
                violations.append(constraint_name)
                # 早期終了: ハード制約の違反が見つかった場合は即座に終了
                constraint = next((c for c in self.constraints if c.constraint_type.value == constraint_name), None)
                if constraint and constraint.is_hard:
                    break
        
        return violations
    
    def calculate_total_violation_score(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> float:
        """総違反スコアを計算"""
        total_score = 0.0
        
        for constraint in self.constraints:
            total_score += constraint.get_violation_score(assignments, operators)
        
        return total_score
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self._validation_cache.clear()

# デフォルト制約セット
def create_default_constraints() -> List[Constraint]:
    """デフォルトの制約セットを作成"""
    return [
        MaxConsecutiveDaysConstraint(max_consecutive_days=6),
        MaxWeeklyHoursConstraint(max_weekly_hours=40.0),
        MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=2),
        RequiredBreakAfterLongShiftConstraint(long_shift_threshold_hours=5.0, required_break_hours=1.0),
        RequiredBreakAfterConsecutiveSlotsConstraint(max_consecutive_slots=5, break_desk_name="休憩"),
    ]

# 制約DSLのサンプル
DEFAULT_CONSTRAINT_DSL = """
# シフト制約定義
max_consecutive_days = 6
max_weekly_hours = 40.0
max_night_shifts_per_week = 2
required_break_after_long_shift 5.0, 1.0
""" 