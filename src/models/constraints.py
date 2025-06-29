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
        # スロットタイプに基づいて終了時刻を推定
        slot_end_times = {
            "morning": 12,
            "afternoon": 17,
            "evening": 21,
            "night": 9  # 翌日の9時
        }
        
        current_end = slot_end_times.get(current.slot_id, 17)
        next_start = slot_end_times.get(next_shift.slot_id, 9)
        
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
        
        # スロットの時間定義
        slot_hours = {
            "morning": 3.0,
            "afternoon": 5.0,
            "evening": 4.0,
            "night": 12.0
        }
        
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
                if assignment.slot_id == "night":
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
                if assignment.slot_id == "night":
                    # 夜勤の翌日をチェック
                    next_day = assignment.date + timedelta(days=1)
                    
                    # 翌日に割り当てがあるかチェック
                    next_day_assignments = [a for a in op_assignments if a.date == next_day]
                    if next_day_assignments:
                        return False
        
        return True

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
        """制約テキストをパースして制約オブジェクトのリストを返す"""
        constraints = []
        lines = constraint_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            for pattern, parser_func in self.constraint_patterns.items():
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    constraint = parser_func(match)
                    if constraint:
                        constraints.append(constraint)
                    break
        
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
        return RequiredDayOffAfterNightConstraint()

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