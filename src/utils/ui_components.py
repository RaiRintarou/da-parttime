"""
UIコンポーネントモジュール

Streamlitアプリケーションで使用する共通UIコンポーネントを提供します。
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from io import StringIO

from .constants import HOURS, COLS, DEFAULT_DESKS


def create_manual_desk_input_form() -> Tuple[pd.DataFrame, List[str]]:
    """
    手動デスク入力フォームを作成
    
    Returns:
        (デスク要員数DataFrame, デスク名リスト)のタプル
    """
    num_desks = st.sidebar.number_input("デスク数", min_value=1, max_value=10, value=5)
    desk_names = []
    desk_requirements = {}
    
    for i in range(num_desks):
        col1, col2 = st.sidebar.columns([2, 1])
        with col1:
            desk_name = st.text_input(f"デスク名 {i+1}", f"Desk {chr(65+i)}", key=f"desk_name_{i}")
        desk_names.append(desk_name)
        
        # 各時間帯の要件を入力
        hour_reqs = {}
        for hour in HOURS:
            hour_col = f"h{hour:02d}"
            with col2:
                req = st.number_input(f"{hour}時", min_value=0, max_value=10, value=0, key=f"req_{i}_{hour}")
            hour_reqs[hour_col] = req
        
        desk_requirements[desk_name] = hour_reqs
    
    # 手動入力データをDataFrameに変換
    req_data = []
    for desk_name in desk_names:
        row = {"desk": desk_name}
        row.update(desk_requirements[desk_name])
        req_data.append(row)
    
    req_df = pd.DataFrame(req_data)
    return req_df, desk_names


def create_manual_operator_input_form(desks: List[str]) -> List[Dict[str, Any]]:
    """
    手動オペレーター入力フォームを作成
    
    Args:
        desks: 利用可能なデスクのリスト
    
    Returns:
        オペレーターデータのリスト
    """
    num_ops = st.sidebar.number_input("オペレータ人数", 1, 200, 10)
    
    ops_data = []
    with st.expander("オペレータ設定 (クリックで開閉)"):
        for i in range(num_ops):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 6])
            name  = c1.text_input(f"名前 {i+1}", f"Op{i+1}")
            start = c2.selectbox("開始", HOURS, key=f"s{i}")
            end   = c2.selectbox("終了", [h+1 for h in HOURS],
                                 index=len(HOURS)-1, key=f"e{i}")
            home  = c3.selectbox("所属デスク", desks, key=f"h{i}")
            operator_desks = c4.multiselect("対応可能デスク", desks, desks, key=f"d{i}")
            ops_data.append({"name": name, "start": start, "end": end,
                             "home": home, "desks": operator_desks})
    
    return ops_data


def display_operator_preview(ops_data: List[Dict[str, Any]]) -> None:
    """
    オペレーター情報のプレビューを表示
    
    Args:
        ops_data: オペレーターデータのリスト
    """
    st.subheader("👥 オペレーター情報プレビュー")
    preview_data = []
    for op in ops_data:
        preview_data.append({
            "名前": op["name"],
            "勤務時間": f"{op['start']}時-{op['end']}時",
            "所属デスク": op["home"],
            "対応可能デスク": ", ".join(op["desks"])
        })
    
    preview_df = pd.DataFrame(preview_data)
    st.dataframe(preview_df, use_container_width=True)


def display_assignment_results(assignments: List[Any], algorithm_name: str) -> None:
    """
    割り当て結果の詳細表示
    
    Args:
        assignments: 割り当て結果のリスト
        algorithm_name: アルゴリズム名
    """
    st.subheader("📋 詳細割り当て結果")
    assignment_data = []
    for assignment in assignments:
        assignment_data.append({
            "オペレータ": assignment.operator_name,
            "デスク": assignment.desk_name,
            "スロット": assignment.slot_id,
            "日付": assignment.date.strftime("%Y-%m-%d"),
            "タイプ": assignment.assignment_type
        })
    
    if assignment_data:
        assignment_df = pd.DataFrame(assignment_data)
        st.dataframe(assignment_df, use_container_width=True)


def display_constraint_details(constraints: List[Any]) -> None:
    """
    制約設定の詳細表示
    
    Args:
        constraints: 制約のリスト
    """
    st.subheader("🔒 適用された制約")
    constraint_details = []
    for constraint in constraints:
        constraint_details.append({
            "制約タイプ": constraint.constraint_type.value,
            "説明": constraint.description,
            "タイプ": "ハード制約" if constraint.is_hard else "ソフト制約"
        })
    
    if constraint_details:
        constraint_df = pd.DataFrame(constraint_details)
        st.dataframe(constraint_df, use_container_width=True)


def create_download_button(data: pd.DataFrame, button_text: str, filename: str) -> None:
    """
    CSVダウンロードボタンを作成
    
    Args:
        data: ダウンロードするデータ
        button_text: ボタンのテキスト
        filename: ファイル名
    """
    csv_data = StringIO()
    data.to_csv(csv_data)
    st.download_button(
        button_text,
        csv_data.getvalue(),
        file_name=filename
    )


def generate_filename(prefix: str, start_date: datetime, target_days: int, suffix: str = "") -> str:
    """
    ファイル名を生成
    
    Args:
        prefix: ファイル名のプレフィックス
        start_date: 開始日
        target_days: 対象日数
        suffix: サフィックス
    
    Returns:
        生成されたファイル名
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    base_filename = f"{prefix}_{start_date.strftime('%Y%m%d')}_{target_days}days_{timestamp}"
    if suffix:
        base_filename += f"_{suffix}"
    return f"{base_filename}.csv"


def display_shift_info(start_date: datetime, target_days: int, algorithm_name: str) -> None:
    """
    シフト情報を表示
    
    Args:
        start_date: 開始日
        target_days: 対象日数
        algorithm_name: アルゴリズム名
    """
    st.subheader("📊 シフト情報")
    st.write(f"**期間**: {start_date.strftime('%Y-%m-%d')} から {target_days}日間")
    st.write(f"**アルゴリズム**: {algorithm_name}")
    st.write(f"**生成日数**: {target_days}日")


def display_individual_day_downloads(all_schedules: List[pd.DataFrame], start_date: datetime) -> None:
    """
    個別日のシフト表ダウンロードを表示
    
    Args:
        all_schedules: 全期間のスケジュールリスト
        start_date: 開始日
    """
    st.subheader("📁 個別日のシフト表ダウンロード")
    for i, day_schedule in enumerate(all_schedules):
        day_date = start_date + timedelta(days=i)
        csv_individual = StringIO()
        day_schedule.to_csv(csv_individual)
        st.download_button(
            f"{day_date.strftime('%Y-%m-%d')} シフト表 CSV DL",
            csv_individual.getvalue(),
            file_name=f"shift_{day_date.strftime('%Y%m%d')}_{datetime.now():%Y%m%d_%H%M}.csv"
        ) 