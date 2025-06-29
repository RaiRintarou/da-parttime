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
        # 1時間単位のスロットタイプに基づいて終了時刻を推定
        current_hour = int(current.slot_id[1:]) if current.slot_id.startswith('h') else 9
        next_hour = int(next_shift.slot_id[1:]) if next_shift.slot_id.startswith('h') else 9
        
        current_end = current_hour + 1  # スロットの終了時刻
        next_start = next_hour  # 次のスロットの開始時刻
        
        # 正しい休息時間計算（翌日の開始時刻 - 前日の終了時刻、負なら+24）
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
        
        # 1時間単位のスロットの時間定義
        slot_hours = {f"h{hour:02d}": 1.0 for hour in range(9, 18)}
        
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
    
    def get_required_break_slots(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> List[Dict[str, Any]]:
        """必要な休憩スロットを取得"""
        from .multi_slot_models import Assignment
        
        # 1時間単位のスロットの時間定義
        slot_hours = {f"h{hour:02d}": 1.0 for hour in range(9, 18)}
        
        break_slots = []
        
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
                    
                    # 後続のシフトがある場合、休憩スロットを追加
                    if current_index < len(same_day_assignments) - 1:
                        next_assignment = same_day_assignments[current_index + 1]
                        break_slots.append({
                            'operator_name': operator.operator_name,
                            'date': assignment.date,
                            'break_start': self._get_break_start_time(assignment),
                            'break_end': self._get_break_end_time(next_assignment),
                            'duration_hours': self.required_break_hours,
                            'reason': f"連続稼働{current_hours}時間後の必須休憩"
                        })
        
        return break_slots
    
    def _get_break_start_time(self, assignment: 'Assignment') -> str:
        """休憩開始時刻を取得"""
        if assignment.slot_id.startswith('h'):
            hour = int(assignment.slot_id[1:])
            return f"{hour+1:02d}:00"
        return "17:00"
    
    def _get_break_end_time(self, assignment: 'Assignment') -> str:
        """休憩終了時刻を取得"""
        if assignment.slot_id.startswith('h'):
            hour = int(assignment.slot_id[1:])
            return f"{hour:02d}:00"
        return "09:00"

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

class ConstraintParser:
    """制約DSLパーサー"""
    
    def __init__(self):
        self.constraint_patterns = {
            r'min_rest_hours\s*=\s*(\d+(?:\.\d+)?)': self._parse_min_rest_hours,
            r'max_consecutive_days\s*=\s*(\d+)': self._parse_max_consecutive_days,
            r'max_weekly_hours\s*=\s*(\d+(?:\.\d+)?)': self._parse_max_weekly_hours,
            r'max_night_shifts_per_week\s*=\s*(\d+)': self._parse_max_night_shifts,
            r'required_day_off_after_night': self._parse_required_day_off_after_night,
        }
    
    def parse_constraints(self, constraint_text: str) -> List[Constraint]:
        """制約テキストを解析して制約リストを生成"""
        constraints = []
        
        # 各制約タイプの正規表現パターン
        patterns = [
            (r'min_rest_hours\s*=\s*(\d+(?:\.\d+)?)', self._parse_min_rest_hours),
            (r'max_consecutive_days\s*=\s*(\d+)', self._parse_max_consecutive_days),
            (r'max_weekly_hours\s*=\s*(\d+(?:\.\d+)?)', self._parse_max_weekly_hours),
            (r'max_night_shifts_per_week\s*=\s*(\d+)', self._parse_max_night_shifts),
            (r'required_day_off_after_night\s*=\s*true', self._parse_required_day_off_after_night),
            (r'required_break_after_long_shift\s*=\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)', self._parse_required_break_after_long_shift),
        ]
        
        for pattern, parser_func in patterns:
            matches = re.finditer(pattern, constraint_text, re.IGNORECASE)
            for match in matches:
                constraint = parser_func(match)
                if constraint:
                    constraints.append(constraint)
        
        return constraints
    
    def _parse_min_rest_hours(self, match) -> Constraint:
        hours = float(match.group(1))
        return MinRestHoursConstraint(min_rest_hours=hours)
    
    def _parse_max_consecutive_days(self, match) -> Constraint:
        days = int(match.group(1))
        return MaxConsecutiveDaysConstraint(max_consecutive_days=days)
    
    def _parse_max_weekly_hours(self, match) -> Constraint:
        hours = float(match.group(1))
        return MaxWeeklyHoursConstraint(max_weekly_hours=hours)
    
    def _parse_max_night_shifts(self, match) -> Constraint:
        shifts = int(match.group(1))
        return MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=shifts)
    
    def _parse_required_day_off_after_night(self, match) -> Constraint:
        """夜勤後の必須休日制約をパース"""
        return RequiredDayOffAfterNightConstraint()
    
    def _parse_required_break_after_long_shift(self, match) -> Constraint:
        """長時間シフト後の必須休憩制約をパース"""
        threshold = float(match.group(1))
        break_hours = float(match.group(2))
        return RequiredBreakAfterLongShiftConstraint(
            long_shift_threshold_hours=threshold,
            required_break_hours=break_hours
        )

class ConstraintValidator:
    """制約バリデーター"""
    
    def __init__(self, constraints: List[Constraint]):
        self.constraints = constraints
    
    def validate_all(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> Dict[str, bool]:
        """全ての制約を検証"""
        results = {}
        
        for constraint in self.constraints:
            constraint_name = constraint.constraint_type.value
            results[constraint_name] = constraint.validate(assignments, operators)
        
        return results
    
    def get_violations(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> List[str]:
        """違反している制約のリストを取得"""
        violations = []
        validation_results = self.validate_all(assignments, operators)
        
        for constraint_name, is_valid in validation_results.items():
            if not is_valid:
                violations.append(constraint_name)
        
        return violations
    
    def calculate_total_violation_score(self, assignments: List['Assignment'], operators: List['OperatorAvailability']) -> float:
        """総違反スコアを計算"""
        total_score = 0.0
        
        for constraint in self.constraints:
            total_score += constraint.get_violation_score(assignments, operators)
        
        return total_score

# デフォルト制約セット
def create_default_constraints() -> List[Constraint]:
    """デフォルトの制約セットを作成"""
    return [
        MinRestHoursConstraint(min_rest_hours=11.0),
        MaxConsecutiveDaysConstraint(max_consecutive_days=6),
        MaxWeeklyHoursConstraint(max_weekly_hours=40.0),
        MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=2),
        RequiredDayOffAfterNightConstraint(),
        RequiredBreakAfterLongShiftConstraint(long_shift_threshold_hours=5.0, required_break_hours=1.0),
    ]

# 制約DSLのサンプル
DEFAULT_CONSTRAINT_DSL = """
# シフト制約定義
min_rest_hours = 11.0
max_consecutive_days = 6
max_weekly_hours = 40.0
max_night_shifts_per_week = 2
required_day_off_after_night
""" 