"""
定数定義モジュール

シフトマッチングシステムで使用する定数を定義します。
"""

# 時間設定
HOURS = list(range(9, 18))  # 9:00〜17:00
COLS = ["desk"] + [f"h{h:02d}" for h in HOURS]

# デフォルトデスク設定
DEFAULT_DESKS = [f"Desk {c}" for c in "ABCDE"]

# 休憩デスク設定
BREAK_DESK_NAME = "休憩"
MAX_CONSECUTIVE_SLOTS_BEFORE_BREAK = 5  # 5スロット連続勤務後に休憩必須

# アルゴリズム選択肢
ALGORITHM_CHOICES = [
    "制約付きMulti-slot DAアルゴリズム (推奨)",
    "Multi-slot DAアルゴリズム", 
    "DAアルゴリズム",
    "貪欲アルゴリズム"
]

# シフト期間選択肢
SHIFT_PERIOD_CHOICES = ["1日", "5日連続", "カスタム"]

# オペレーター別シフト表表示方法
OPERATOR_SCHEDULE_METHODS = [
    "全日の割り当てを表示",
    "統合シフト表（最後の割り当て優先）",
    "統合シフト表（最初の割り当て優先）"
]

# 制約のデフォルト値
DEFAULT_CONSTRAINTS = {
    "min_rest_hours": 11.0,
    "max_consecutive_days": 6,
    "max_weekly_hours": 40.0,
    "max_night_shifts_per_week": 2,
    "required_day_off_after_night": True,
    "long_shift_threshold_hours": 5.0,
    "required_break_hours": 1.0,
    "max_consecutive_slots": 5,
    "break_desk_name": "休憩",
    "enable_min_rest": True,
    "enable_consecutive": True,
    "enable_weekly_hours": True,
    "enable_night_shifts": True,
    "enable_day_off_after_night": True,
    "enable_break_after_long_shift": True,
    "enable_break_after_consecutive_slots": True
} 