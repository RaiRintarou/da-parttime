"""
アルゴリズム実行モジュール

シフトマッチングアルゴリズムの実行と結果処理を統合的に管理します。
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from io import StringIO

from algorithms.da_algorithm import da_match, greedy_match
from algorithms.multi_slot_da_algorithm import multi_slot_da_match
from algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match
from models.constraints import ConstraintValidator

from .schedule_converter import (
    convert_to_operator_schedule, convert_multi_day_to_operator_schedule,
    convert_assignments_to_operator_schedule, convert_multi_day_assignments_to_operator_schedule
)
from .data_converter import convert_ops_data_to_operator_availability
from .ui_components import (
    display_assignment_results, display_constraint_details, create_download_button,
    generate_filename, display_shift_info, display_individual_day_downloads
)


class AlgorithmExecutor:
    """アルゴリズム実行を管理するクラス"""
    
    def __init__(self, req_df: pd.DataFrame, ops_data: List[Dict[str, Any]], 
                 start_date: datetime, target_days: int, merge_method: str = "last"):
        """
        初期化
        
        Args:
            req_df: デスク要員数DataFrame
            ops_data: オペレーターデータのリスト
            start_date: 開始日
            target_days: 対象日数
            merge_method: 統合方法
        """
        self.req_df = req_df
        self.ops_data = ops_data
        self.start_date = start_date
        self.target_days = target_days
        self.merge_method = merge_method
        self.all_assignments = []
        self.all_schedules = []
        self.algorithm_name = ""
    
    def execute_constrained_multi_slot_da(self, constraints: List[Any]) -> pd.DataFrame:
        """
        制約付きMulti-slot DAアルゴリズムを実行
        
        Args:
            constraints: 制約のリスト
        
        Returns:
            最終的なスケジュールDataFrame
        """
        self.algorithm_name = "制約付きMulti-slot DAアルゴリズム"
        
        # 各日のマッチングを実行
        for day in range(self.target_days):
            current_date = datetime.combine(self.start_date, datetime.min.time()) + timedelta(days=day)
            assignments, schedule = constrained_multi_slot_da_match(
                pd.DataFrame(self.req_df.copy()), self.ops_data, constraints, current_date
            )
            self.all_assignments.extend(assignments)
            self.all_schedules.append(schedule)
        
        # 制約違反チェック
        self._check_constraint_violations(constraints)
        
        # 制約設定の詳細表示
        display_constraint_details(constraints)
        
        # 割り当て結果の表示
        display_assignment_results(self.all_assignments, self.algorithm_name)
        
        # オペレーター別シフト表の生成と表示
        return self._generate_operator_schedule_from_assignments()
    
    def execute_multi_slot_da(self) -> pd.DataFrame:
        """
        Multi-slot DAアルゴリズムを実行
        
        Returns:
            最終的なスケジュールDataFrame
        """
        self.algorithm_name = "Multi-slot DAアルゴリズム"
        
        # 各日のマッチングを実行
        for day in range(self.target_days):
            current_date = datetime.combine(self.start_date, datetime.min.time()) + timedelta(days=day)
            assignments, schedule = multi_slot_da_match(
                pd.DataFrame(self.req_df.copy()), self.ops_data, current_date
            )
            self.all_assignments.extend(assignments)
            self.all_schedules.append(schedule)
        
        # 割り当て結果の表示
        display_assignment_results(self.all_assignments, self.algorithm_name)
        
        # オペレーター別シフト表の生成と表示
        operator_schedule = self._generate_operator_schedule_from_assignments()
        
        # デスク別シフト表の表示
        self._display_desk_schedules()
        
        return operator_schedule
    
    def execute_da_algorithm(self) -> pd.DataFrame:
        """
        DAアルゴリズムを実行
        
        Returns:
            最終的なスケジュールDataFrame
        """
        self.algorithm_name = "DAアルゴリズム"
        
        # 各日のマッチングを実行
        for day in range(self.target_days):
            current_date = datetime.combine(self.start_date, datetime.min.time()) + timedelta(days=day)
            schedule = da_match(pd.DataFrame(self.req_df.copy()), self.ops_data)
            self.all_schedules.append(schedule)
        
        # デスク別シフト表の表示
        self._display_desk_schedules()
        
        # オペレーター別シフト表の生成と表示
        if self.target_days > 1:
            operator_schedule = convert_multi_day_to_operator_schedule(
                self.all_schedules, self.ops_data, self.target_days, 
                datetime.combine(self.start_date, datetime.min.time()), self.merge_method
            )
            st.subheader(f"👥 {self.target_days}日分の統合シフト表（オペレーター別）")
            st.dataframe(operator_schedule, use_container_width=True)
            
            # ダウンロードボタン
            filename = generate_filename("operator_shift", self.start_date, self.target_days)
            create_download_button(operator_schedule, "オペレーター別シフト表 CSV DL", filename)
        else:
            operator_schedule = convert_to_operator_schedule(self.all_schedules[0], self.ops_data)
            st.subheader("👥 生成されたシフト表（オペレーター別）")
            st.dataframe(operator_schedule, use_container_width=True)
            
            # ダウンロードボタン
            filename = generate_filename("operator_shift", self.start_date, self.target_days)
            create_download_button(operator_schedule, "オペレーター別シフト表 CSV DL", filename)
        
        return operator_schedule
    
    def execute_greedy_algorithm(self) -> pd.DataFrame:
        """
        貪欲アルゴリズムを実行
        
        Returns:
            最終的なスケジュールDataFrame
        """
        self.algorithm_name = "貪欲アルゴリズム"
        
        # 各日のマッチングを実行
        for day in range(self.target_days):
            current_date = datetime.combine(self.start_date, datetime.min.time()) + timedelta(days=day)
            schedule = greedy_match(pd.DataFrame(self.req_df.copy()), self.ops_data)
            self.all_schedules.append(schedule)
        
        # デスク別シフト表の表示
        self._display_desk_schedules()
        
        # オペレーター別シフト表の生成と表示
        if self.target_days > 1:
            operator_schedule = convert_multi_day_to_operator_schedule(
                self.all_schedules, self.ops_data, self.target_days, 
                datetime.combine(self.start_date, datetime.min.time()), self.merge_method
            )
            
            # 表示タイトルを動的に設定
            if self.merge_method == "all":
                st.subheader(f"👥 {self.target_days}日分のオペレーター別シフト表（全日表示）")
            elif self.merge_method == "first":
                st.subheader(f"👥 {self.target_days}日分の統合シフト表（オペレーター別・最初の割り当て優先）")
            else:  # "last"
                st.subheader(f"👥 {self.target_days}日分の統合シフト表（オペレーター別・最後の割り当て優先）")
            
            st.dataframe(operator_schedule, use_container_width=True)
            
            # ダウンロードボタン
            filename = generate_filename("operator_shift", self.start_date, self.target_days)
            create_download_button(operator_schedule, "オペレーター別シフト表 CSV DL", filename)
        else:
            operator_schedule = convert_to_operator_schedule(self.all_schedules[0], self.ops_data)
            st.subheader("👥 生成されたシフト表（オペレーター別）")
            st.dataframe(operator_schedule, use_container_width=True)
            
            # ダウンロードボタン
            filename = generate_filename("operator_shift", self.start_date, self.target_days)
            create_download_button(operator_schedule, "オペレーター別シフト表 CSV DL", filename)
        
        return operator_schedule
    
    def _check_constraint_violations(self, constraints: List[Any]) -> None:
        """
        制約違反をチェック
        
        Args:
            constraints: 制約のリスト
        """
        validator = ConstraintValidator(constraints)
        operators = convert_ops_data_to_operator_availability(self.ops_data)
        violations = validator.get_violations(self.all_assignments, operators)
        
        if violations:
            st.warning("⚠️ 制約違反が検出されました:")
            for violation in violations:
                st.write(f"  • {violation}")
        else:
            st.success("✅ すべての制約を満たしています")
    
    def _generate_operator_schedule_from_assignments(self) -> pd.DataFrame:
        """
        割り当て結果からオペレーター別シフト表を生成
        
        Returns:
            オペレーター別シフト表
        """
        if self.target_days > 1:
            operator_schedule = convert_multi_day_assignments_to_operator_schedule(
                self.all_assignments, self.ops_data, self.target_days, 
                datetime.combine(self.start_date, datetime.min.time()), self.merge_method
            )
            
            # 表示タイトルを動的に設定
            if self.merge_method == "all":
                st.subheader(f"👥 {self.target_days}日分のオペレーター別シフト表（詳細割り当て結果から生成・全日表示）")
            elif self.merge_method == "first":
                st.subheader(f"👥 {self.target_days}日分のオペレーター別シフト表（詳細割り当て結果から生成・最初の割り当て優先）")
            else:  # "last"
                st.subheader(f"👥 {self.target_days}日分のオペレーター別シフト表（詳細割り当て結果から生成・最後の割り当て優先）")
        else:
            operator_schedule = convert_assignments_to_operator_schedule(self.all_assignments, self.ops_data)
            st.subheader("👥 生成されたシフト表（オペレーター別・詳細割り当て結果から生成）")
        
        st.dataframe(operator_schedule, use_container_width=True)
        
        # ダウンロードボタン
        filename = generate_filename("operator_shift_from_assignments", self.start_date, self.target_days)
        create_download_button(
            operator_schedule, 
            "オペレーター別シフト表 CSV DL（詳細割り当て結果から生成）", 
            filename
        )
        
        return operator_schedule
    
    def _display_desk_schedules(self) -> None:
        """デスク別シフト表を表示"""
        if self.target_days > 1:
            st.subheader(f"📅 {self.target_days}日分の統合シフト表（デスク別）")
            # 各日のシフト表に日付を追加して列名を一意にする
            renamed_schedules = []
            for i, day_schedule in enumerate(self.all_schedules):
                day_date = self.start_date + timedelta(days=i)
                date_str = day_date.strftime('%m-%d')
                # 列名に日付を追加
                renamed_cols = {col: f"{col}_{date_str}" for col in day_schedule.columns}
                renamed_schedule = day_schedule.rename(columns=renamed_cols)
                renamed_schedules.append(renamed_schedule)
            
            combined_schedule = pd.concat(renamed_schedules, axis=1)
            st.dataframe(combined_schedule, use_container_width=True)
        else:
            st.subheader("📅 生成されたシフト表（デスク別）")
            st.dataframe(self.all_schedules[0], use_container_width=True)
    
    def get_final_schedule(self) -> pd.DataFrame:
        """
        最終的なスケジュールを取得
        
        Returns:
            最終的なスケジュールDataFrame
        """
        if self.target_days == 1:
            return self.all_schedules[0] if self.all_schedules else pd.DataFrame()
        else:
            # 複数日の場合はオペレーター別シフト表を返す
            return convert_multi_day_assignments_to_operator_schedule(
                self.all_assignments, self.ops_data, self.target_days, 
                datetime.combine(self.start_date, datetime.min.time()), self.merge_method
            ) if self.all_assignments else pd.DataFrame()
    
    def display_results(self, point_unit: int) -> None:
        """
        結果を表示
        
        Args:
            point_unit: ポイント単位
        """
        from .point_calculator import calc_points
        
        # シフト情報の表示
        display_shift_info(self.start_date, self.target_days, self.algorithm_name)
        
        # 最終的なスケジュールを取得
        final_schedule = self.get_final_schedule()
        
        # ポイント計算
        pt_df = calc_points(final_schedule, self.ops_data, point_unit)
        st.subheader("🏅 デスク別ポイント補填")
        st.dataframe(pt_df, use_container_width=True)
        
        # ダウンロードボタン
        shift_filename = generate_filename("shift", self.start_date, self.target_days)
        create_download_button(final_schedule, "シフト表 CSV DL", shift_filename)
        
        points_filename = generate_filename("points", self.start_date, self.target_days)
        create_download_button(pt_df, "ポイント集計 CSV DL", points_filename)
        
        # 個別日のダウンロード
        if self.target_days > 1:
            display_individual_day_downloads(self.all_schedules, self.start_date) 