"""
制約管理モジュール

制約設定のUIと制約オブジェクトの生成を管理します。
"""

import streamlit as st
from typing import List, Dict, Any

from models.constraints import (
    create_default_constraints, MinRestHoursConstraint, MaxConsecutiveDaysConstraint,
    MaxWeeklyHoursConstraint, MaxNightShiftsPerWeekConstraint, RequiredDayOffAfterNightConstraint,
    RequiredBreakAfterLongShiftConstraint, RequiredBreakAfterConsecutiveSlotsConstraint
)

from .constants import DEFAULT_CONSTRAINTS


class ConstraintManager:
    """制約設定を管理するクラス"""
    
    def __init__(self):
        """初期化"""
        self.constraints_config = DEFAULT_CONSTRAINTS.copy()
        self._load_saved_constraints()
    
    def _load_saved_constraints(self) -> None:
        """保存された制約設定を読み込み"""
        if "saved_constraints" in st.session_state:
            saved = st.session_state.saved_constraints
            for key in self.constraints_config:
                if key in saved:
                    self.constraints_config[key] = saved[key]
    
    def render_constraint_ui(self) -> None:
        """制約設定UIを表示"""
        with st.sidebar.expander("制約設定 (クリックで開閉)", expanded=False):
            st.write("**労働法規制などの制約を設定してください**")
            
            # 制約設定の保存/読み込み
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 設定を保存"):
                    st.session_state.saved_constraints = self.constraints_config
                    st.success("✅ 設定を保存しました")
            
            with col2:
                if st.button("📂 設定を読み込み"):
                    if "saved_constraints" in st.session_state:
                        saved = st.session_state.saved_constraints
                        st.info("📋 保存された設定:")
                        for key, value in saved.items():
                            st.write(f"  • {key}: {value}")
                    else:
                        st.warning("⚠️ 保存された設定がありません")
            
            # デフォルト設定に戻すボタン
            if st.button("🔄 デフォルト設定に戻す"):
                st.session_state.saved_constraints = None
                st.success("✅ デフォルト設定に戻しました")
            
            st.divider()
            
            # 最小休息時間制約
            st.subheader("🛌 最小休息時間")
            self.constraints_config["min_rest_hours"] = st.slider(
                "最小休息時間（時間）",
                min_value=8.0,
                max_value=16.0,
                value=self.constraints_config["min_rest_hours"],
                step=0.5,
                help="連続する勤務の間に必要な最小休息時間"
            )
            
            # 最大連勤日数制約
            st.subheader("📅 最大連勤日数")
            self.constraints_config["max_consecutive_days"] = st.slider(
                "最大連勤日数（日）",
                min_value=3,
                max_value=10,
                value=self.constraints_config["max_consecutive_days"],
                step=1,
                help="連続して勤務できる最大日数"
            )
            
            # 最大週間労働時間制約
            st.subheader("⏰ 最大週間労働時間")
            self.constraints_config["max_weekly_hours"] = st.slider(
                "最大週間労働時間（時間）",
                min_value=20.0,
                max_value=60.0,
                value=self.constraints_config["max_weekly_hours"],
                step=1.0,
                help="1週間あたりの最大労働時間"
            )
            
            # 週間最大夜勤数制約
            st.subheader("🌙 週間最大夜勤数")
            self.constraints_config["max_night_shifts_per_week"] = st.slider(
                "週間最大夜勤数（回）",
                min_value=1,
                max_value=5,
                value=self.constraints_config["max_night_shifts_per_week"],
                step=1,
                help="1週間あたりの最大夜勤回数"
            )
            
            # 夜勤後の必須休日制約
            st.subheader("🏖️ 夜勤後の必須休日")
            self.constraints_config["required_day_off_after_night"] = st.checkbox(
                "夜勤後の翌日を休日とする",
                value=self.constraints_config["required_day_off_after_night"],
                help="夜勤の翌日は必ず休日にする"
            )
            
            # 長時間シフト後の必須休憩制約
            st.subheader("☕ 長時間シフト後の必須休憩")
            self.constraints_config["long_shift_threshold_hours"] = st.slider(
                "長時間シフトの閾値（時間）",
                min_value=3.0,
                max_value=8.0,
                value=self.constraints_config["long_shift_threshold_hours"],
                step=0.5,
                help="この時間以上のシフトを長時間シフトとみなす"
            )
            
            self.constraints_config["required_break_hours"] = st.slider(
                "必須休憩時間（時間）",
                min_value=0.5,
                max_value=2.0,
                value=self.constraints_config["required_break_hours"],
                step=0.25,
                help="長時間シフト後に必要な休憩時間"
            )
            
            st.info(f"💡 連続稼働{self.constraints_config['long_shift_threshold_hours']}時間以上の場合、{self.constraints_config['required_break_hours']}時間の休憩が必須となります")
            
            # 連続スロット後の必須休憩制約設定
            st.subheader("🔄 連続スロット後の必須休憩制約")
            self.constraints_config["max_consecutive_slots"] = st.slider(
                "最大連続スロット数",
                min_value=3,
                max_value=8,
                value=self.constraints_config.get("max_consecutive_slots", 5),
                step=1,
                help="このスロット数以上連続で働いた場合、次のスロットで休憩が必須"
            )
            
            self.constraints_config["break_desk_name"] = st.text_input(
                "休憩デスク名",
                value=self.constraints_config.get("break_desk_name", "休憩"),
                help="休憩時に割り当てられるデスク名"
            )
            
            st.info(f"💡 連続{self.constraints_config['max_consecutive_slots']}スロット以上の場合、次のスロットで{self.constraints_config['break_desk_name']}が必須となります")
            
            # 制約の有効/無効設定
            st.subheader("⚙️ 制約の有効/無効")
            self.constraints_config["enable_min_rest"] = st.checkbox("最小休息時間制約を有効にする", value=self.constraints_config["enable_min_rest"])
            self.constraints_config["enable_consecutive"] = st.checkbox("最大連勤日数制約を有効にする", value=self.constraints_config["enable_consecutive"])
            self.constraints_config["enable_weekly_hours"] = st.checkbox("最大週間労働時間制約を有効にする", value=self.constraints_config["enable_weekly_hours"])
            self.constraints_config["enable_night_shifts"] = st.checkbox("週間最大夜勤数制約を有効にする", value=self.constraints_config["enable_night_shifts"])
            self.constraints_config["enable_day_off_after_night"] = st.checkbox("夜勤後の必須休日制約を有効にする", value=self.constraints_config["enable_day_off_after_night"])
            self.constraints_config["enable_break_after_long_shift"] = st.checkbox("長時間シフト後の必須休憩制約を有効にする", value=self.constraints_config["enable_break_after_long_shift"])
            self.constraints_config["enable_break_after_consecutive_slots"] = st.checkbox("連続スロット後の必須休憩制約を有効にする", value=self.constraints_config.get("enable_break_after_consecutive_slots", True))
            
            # 制約設定のプレビュー
            self._display_constraint_preview()
    
    def _display_constraint_preview(self) -> None:
        """制約設定のプレビューを表示"""
        st.subheader("📋 制約設定プレビュー")
        constraints_preview = []
        
        if self.constraints_config["enable_min_rest"]:
            constraints_preview.append(f"• 最小休息時間: {self.constraints_config['min_rest_hours']}時間")
        if self.constraints_config["enable_consecutive"]:
            constraints_preview.append(f"• 最大連勤日数: {self.constraints_config['max_consecutive_days']}日")
        if self.constraints_config["enable_weekly_hours"]:
            constraints_preview.append(f"• 最大週間労働時間: {self.constraints_config['max_weekly_hours']}時間")
        if self.constraints_config["enable_night_shifts"]:
            constraints_preview.append(f"• 週間最大夜勤数: {self.constraints_config['max_night_shifts_per_week']}回")
        if self.constraints_config["enable_day_off_after_night"]:
            constraints_preview.append("• 夜勤後の必須休日: 有効")
        if self.constraints_config["enable_break_after_long_shift"]:
            constraints_preview.append(f"• 長時間シフト後の必須休憩: {self.constraints_config['long_shift_threshold_hours']}時間以上→{self.constraints_config['required_break_hours']}時間休憩")
        if self.constraints_config["enable_break_after_consecutive_slots"]:
            constraints_preview.append(f"• 連続スロット後の必須休憩: {self.constraints_config['max_consecutive_slots']}スロット以上→{self.constraints_config['break_desk_name']}")
        
        if constraints_preview:
            for constraint in constraints_preview:
                st.write(constraint)
        else:
            st.warning("⚠️ 有効な制約が設定されていません")
    
    def create_constraints(self) -> List[Any]:
        """
        制約オブジェクトのリストを作成
        
        Returns:
            制約オブジェクトのリスト
        """
        constraints = []
        
        if self.constraints_config["enable_min_rest"]:
            constraints.append(MinRestHoursConstraint(min_rest_hours=self.constraints_config["min_rest_hours"]))
        if self.constraints_config["enable_consecutive"]:
            constraints.append(MaxConsecutiveDaysConstraint(max_consecutive_days=self.constraints_config["max_consecutive_days"]))
        if self.constraints_config["enable_weekly_hours"]:
            constraints.append(MaxWeeklyHoursConstraint(max_weekly_hours=self.constraints_config["max_weekly_hours"]))
        if self.constraints_config["enable_night_shifts"]:
            constraints.append(MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=self.constraints_config["max_night_shifts_per_week"]))
        if self.constraints_config["enable_day_off_after_night"]:
            constraints.append(RequiredDayOffAfterNightConstraint())
        if self.constraints_config["enable_break_after_long_shift"]:
            constraints.append(RequiredBreakAfterLongShiftConstraint(
                long_shift_threshold_hours=self.constraints_config["long_shift_threshold_hours"],
                required_break_hours=self.constraints_config["required_break_hours"]
            ))
        if self.constraints_config["enable_break_after_consecutive_slots"]:
            constraints.append(RequiredBreakAfterConsecutiveSlotsConstraint(
                max_consecutive_slots=self.constraints_config["max_consecutive_slots"],
                break_desk_name=self.constraints_config["break_desk_name"]
            ))
        
        # 制約が設定されていない場合の警告
        if not constraints:
            st.sidebar.warning("⚠️ 制約が設定されていません。デフォルト制約が適用されます。")
            constraints = create_default_constraints()
        
        return constraints 