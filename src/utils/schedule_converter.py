"""
スケジュール変換モジュール

デスク別シフト表とオペレーター別シフト表の相互変換機能を提供します。
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any


def convert_to_operator_schedule(schedule_df: pd.DataFrame, ops_data: list) -> pd.DataFrame:
    """
    デスク別シフト表をオペレーター別シフト表に変換
    
    Args:
        schedule_df: デスク別シフト表（デスクを行、時間を列）
        ops_data: オペレーターデータのリスト
    
    Returns:
        オペレーター別シフト表（オペレーターを行、時間を列）
    """
    # オペレーター名のリストを取得
    operator_names = [op["name"] for op in ops_data]
    
    # 時間列を取得（desk列以外）
    time_columns = [col for col in schedule_df.columns if col != "desk"]
    
    # オペレーター別シフト表の初期化
    operator_schedule = pd.DataFrame(
        index=pd.Index(operator_names, name="operator"),
        columns=pd.Index(time_columns, name="time")
    )
    operator_schedule = operator_schedule.fillna("")
    
    # 各デスクの各時間帯で割り当てられているオペレーターを特定
    for _, row in schedule_df.iterrows():
        desk_name = row["desk"]
        
        for time_col in time_columns:
            assigned_operator = row[time_col]
            
            # 割り当てられているオペレーターがいる場合
            if bool(pd.notna(assigned_operator)) and str(assigned_operator) != "":
                # そのオペレーターの行にデスク名を設定
                if assigned_operator in operator_names:
                    operator_schedule.loc[assigned_operator, time_col] = desk_name
    
    return operator_schedule


def convert_multi_slot_to_operator_schedule(assignments: list, ops_data: list, target_days: int, start_date: datetime) -> pd.DataFrame:
    """
    Multi-slot割り当て結果をオペレーター別シフト表に変換
    
    Args:
        assignments: 割り当て結果のリスト
        ops_data: オペレーターデータのリスト
        target_days: 対象日数
        start_date: 開始日
    
    Returns:
        オペレーター別シフト表（オペレーターを行、時間を列）
    """
    # オペレーター名のリストを取得
    operator_names = [op["name"] for op in ops_data]
    
    # 時間列を生成（9-17時）
    time_columns = [f"h{h:02d}" for h in range(9, 18)]
    
    # オペレーター別シフト表の初期化
    operator_schedule = pd.DataFrame(
        index=pd.Index(operator_names, name="operator"),
        columns=pd.Index(time_columns, name="time")
    )
    operator_schedule = operator_schedule.fillna("")
    
    # 各割り当てを処理
    for assignment in assignments:
        operator_name = assignment.operator_name
        desk_name = assignment.desk_name
        slot_id = assignment.slot_id
        
        # 該当するセルにデスク名を設定
        if slot_id in operator_schedule.columns and operator_name in operator_schedule.index:
            operator_schedule.loc[operator_name, slot_id] = desk_name
    
    return operator_schedule


def convert_multi_day_to_operator_schedule(all_schedules: list, ops_data: list, target_days: int, start_date: datetime, merge_method: str = "last") -> pd.DataFrame:
    """
    複数日のデスク別シフト表をオペレーター別シフト表に変換
    
    Args:
        all_schedules: 各日のデスク別シフト表のリスト
        ops_data: オペレーターデータのリスト
        target_days: 対象日数
        start_date: 開始日
        merge_method: 統合方法 ("last": 最後の割り当てを優先, "first": 最初の割り当てを優先, "all": 全日の割り当てを表示)
    
    Returns:
        オペレーター別シフト表（オペレーターを行、時間を列）
    """
    # オペレーター名のリストを取得
    operator_names = [op["name"] for op in ops_data]
    
    # 時間列を生成（9-17時）
    time_columns = [f"h{h:02d}" for h in range(9, 18)]
    
    if merge_method == "all":
        # 全日の割り当てを表示する場合
        # 各日のシフト表を個別に変換して統合
        all_operator_schedules = []
        
        for day in range(target_days):
            if day < len(all_schedules):
                day_schedule = all_schedules[day]
                day_date = start_date + timedelta(days=day)
                date_str = day_date.strftime('%m-%d')
                
                # その日のオペレーター別シフト表を生成
                day_operator_schedule = convert_to_operator_schedule(day_schedule, ops_data)
                
                # 列名に日付を追加
                day_operator_schedule.columns = [f"{col}_{date_str}" for col in day_operator_schedule.columns]
                all_operator_schedules.append(day_operator_schedule)
        
        # 全日のシフト表を横に結合
        if all_operator_schedules:
            combined_operator_schedule = pd.concat(all_operator_schedules, axis=1)
            return combined_operator_schedule
        else:
            # 空のシフト表を返す
            return pd.DataFrame(
                index=pd.Index(operator_names, name="operator"),
                columns=pd.Index([], name="time")
            )
    
    else:
        # 統合されたシフト表を生成する場合
        # オペレーター別シフト表の初期化
        operator_schedule = pd.DataFrame(
            index=pd.Index(operator_names, name="operator"),
            columns=pd.Index(time_columns, name="time")
        )
        operator_schedule = operator_schedule.fillna("")
        
        # 各日のシフト表を処理
        for day in range(target_days):
            if day < len(all_schedules):
                day_schedule = all_schedules[day]
                
                # 各デスクの各時間帯で割り当てられているオペレーターを特定
                for _, row in day_schedule.iterrows():
                    desk_name = row["desk"]
                    
                    for time_col in time_columns:
                        if time_col in row:
                            assigned_operator = row[time_col]
                            
                            # 割り当てられているオペレーターがいる場合
                            if bool(pd.notna(assigned_operator)) and str(assigned_operator) != "":
                                # そのオペレーターの行にデスク名を設定
                                if assigned_operator in operator_names:
                                    if merge_method == "first":
                                        # 最初の割り当てのみを保持
                                        if operator_schedule.loc[assigned_operator, time_col] == "":
                                            operator_schedule.loc[assigned_operator, time_col] = desk_name
                                    else:  # "last"
                                        # 最後の割り当てで上書き
                                        operator_schedule.loc[assigned_operator, time_col] = desk_name
        
        return operator_schedule


def convert_assignments_to_operator_schedule(assignments: list, ops_data: list) -> pd.DataFrame:
    """
    詳細割り当て結果からオペレーター別シフト表を生成
    
    Args:
        assignments: 詳細割り当て結果のリスト
        ops_data: オペレーターデータのリスト
    
    Returns:
        オペレーター別シフト表（オペレーターを行、スロットを列）
    """
    # オペレーター名のリストを取得
    operator_names = [op["name"] for op in ops_data]
    
    # スロット列を生成（h09~h17）
    slot_columns = [f"h{h:02d}" for h in range(9, 18)]
    
    # オペレーター別シフト表の初期化
    operator_schedule = pd.DataFrame(
        index=pd.Index(operator_names, name="operator"),
        columns=pd.Index(slot_columns, name="slot")
    )
    operator_schedule = operator_schedule.fillna("")
    
    # 各割り当てを処理
    for assignment in assignments:
        operator_name = assignment.operator_name
        desk_name = assignment.desk_name
        slot_id = assignment.slot_id
        
        # 該当するセルにデスク名を設定
        if slot_id in operator_schedule.columns and operator_name in operator_schedule.index:
            operator_schedule.loc[operator_name, slot_id] = desk_name
    
    return operator_schedule


def convert_multi_day_assignments_to_operator_schedule(all_assignments: list, ops_data: list, target_days: int, start_date: datetime, merge_method: str = "last") -> pd.DataFrame:
    """
    複数日の詳細割り当て結果からオペレーター別シフト表を生成
    
    Args:
        all_assignments: 全期間の詳細割り当て結果のリスト
        ops_data: オペレーターデータのリスト
        target_days: 対象日数
        start_date: 開始日
        merge_method: 統合方法 ("last": 最後の割り当てを優先, "first": 最初の割り当てを優先, "all": 全日の割り当てを表示)
    
    Returns:
        オペレーター別シフト表（オペレーターを行、スロットを列）
    """
    # オペレーター名のリストを取得
    operator_names = [op["name"] for op in ops_data]
    
    # スロット列を生成（h09~h17）
    slot_columns = [f"h{h:02d}" for h in range(9, 18)]
    
    if merge_method == "all":
        # 全日の割り当てを表示する場合
        # 各日の割り当てを個別に処理して統合
        all_operator_schedules = []
        
        for day in range(target_days):
            day_date = start_date + timedelta(days=day)
            date_str = day_date.strftime('%m-%d')
            
            # その日の割り当てを抽出
            day_assignments = [a for a in all_assignments if a.date.date() == day_date.date()]
            
            # その日のオペレーター別シフト表を生成
            day_operator_schedule = convert_assignments_to_operator_schedule(day_assignments, ops_data)
            
            # 列名に日付を追加
            day_operator_schedule.columns = [f"{col}_{date_str}" for col in day_operator_schedule.columns]
            all_operator_schedules.append(day_operator_schedule)
        
        # 全日のシフト表を横に結合
        if all_operator_schedules:
            combined_operator_schedule = pd.concat(all_operator_schedules, axis=1)
            return combined_operator_schedule
        else:
            # 空のシフト表を返す
            return pd.DataFrame(
                index=pd.Index(operator_names, name="operator"),
                columns=pd.Index([], name="slot")
            )
    
    else:
        # 統合されたシフト表を生成する場合
        # オペレーター別シフト表の初期化
        operator_schedule = pd.DataFrame(
            index=pd.Index(operator_names, name="operator"),
            columns=pd.Index(slot_columns, name="slot")
        )
        operator_schedule = operator_schedule.fillna("")
        
        # 各割り当てを処理
        for assignment in all_assignments:
            operator_name = assignment.operator_name
            desk_name = assignment.desk_name
            slot_id = assignment.slot_id
            
            # 該当するセルにデスク名を設定
            if slot_id in operator_schedule.columns and operator_name in operator_schedule.index:
                if merge_method == "first":
                    # 最初の割り当てのみを保持
                    if operator_schedule.loc[operator_name, slot_id] == "":
                        operator_schedule.loc[operator_name, slot_id] = desk_name
                else:  # "last"
                    # 最後の割り当てで上書き
                    operator_schedule.loc[operator_name, slot_id] = desk_name
        
        return operator_schedule 