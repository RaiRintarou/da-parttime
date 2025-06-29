"""
シフトマッチングデモアプリケーション（リファクタリング版）

Streamlitを使用したシフトマッチングシステムのデモアプリケーションです。
制約付きMulti-slot DAアルゴリズム、Multi-slot DAアルゴリズム、DAアルゴリズム、貪欲アルゴリズムを提供します。
"""

import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# ユーティリティモジュールをインポート
from utils import (
    HOURS, COLS, DEFAULT_DESKS, ALGORITHM_CHOICES, SHIFT_PERIOD_CHOICES, 
    OPERATOR_SCHEDULE_METHODS, DEFAULT_CONSTRAINTS,
    create_desk_requirements_template, create_operators_template,
    validate_csv_upload, validate_operators_csv,
    create_manual_desk_input_form, create_manual_operator_input_form,
    display_operator_preview, AlgorithmExecutor, ConstraintManager
)


def empty_requirements(desks=None):
    """空のデスク要員数テンプレートを生成"""
    if desks is None:
        desks = DEFAULT_DESKS
    df = pd.DataFrame({"desk": desks}).reindex(columns=COLS).fillna(0)
    return df.astype({"desk": str, **{c: int for c in COLS[1:]}})


def setup_desk_requirements_section():
    """デスク要員数設定セクション"""
    st.sidebar.header("1️⃣ デスク要員数：CSV アップロード")

    # テンプレートダウンロード
    tpl = empty_requirements()
    buf = StringIO()
    tpl.to_csv(buf, index=False)
    st.sidebar.download_button("テンプレートDL", buf.getvalue(),
                               file_name="desk_template.csv", mime="text/csv")

    # ファイルアップロード
    try:
        up_file = st.sidebar.file_uploader("CSV をアップロード", type="csv", 
                                          help="CSVファイルをアップロードするか、手動入力を使用してください")
    except Exception as e:
        st.sidebar.error(f"ファイルアップロードエラー: {str(e)}")
        up_file = None

    # 手動入力オプション
    st.sidebar.subheader("または手動入力")
    manual_input = st.sidebar.checkbox("手動でデスク情報を入力", value=False)

    if manual_input:
        req_df, desk_names = create_manual_desk_input_form()
        st.success("手動入力完了 ✅")
    elif up_file:
        try:
            req_df = pd.read_csv(up_file)
            if miss := set(COLS) - set(req_df.columns):
                st.error(f"列不足: {miss}")
                st.info("テンプレートをダウンロードして正しい形式でアップロードしてください")
                st.stop()
            req_df = req_df[COLS].fillna(0).astype({"desk": str, **{c: int for c in COLS[1:]}})
            st.success("CSV 読込完了 ✅")
        except Exception as e:
            st.error(f"CSV読み込みエラー: {str(e)}")
            st.info("ファイル形式を確認するか、手動入力を使用してください")
            req_df = empty_requirements()
    else:
        st.info("CSV 未アップロード → 0 で初期化")
        req_df = empty_requirements()

    # デスクリストを取得
    desks = req_df["desk"].tolist()

    st.subheader("📝 デスク要員数プレビュー")
    st.dataframe(req_df, use_container_width=True)
    
    return req_df, desks


def setup_operator_section(desks):
    """オペレーター設定セクション"""
    st.sidebar.header("2️⃣ オペレータ情報")

    # オペレーターCSV読み込み機能
    st.sidebar.subheader("📁 オペレーターCSV読み込み")

    # オペレーターCSVテンプレートのダウンロード
    operators_template_data = create_operators_template()
    st.sidebar.download_button(
        "オペレーターCSVテンプレートDL", 
        operators_template_data,
        file_name="operators_template.csv", 
        mime="text/csv"
    )

    # オペレーターCSVファイルアップロード
    try:
        operators_file = st.sidebar.file_uploader(
            "オペレーターCSVをアップロード", 
            type="csv",
            help="オペレーター情報のCSVファイルをアップロードするか、手動入力を使用してください"
        )
    except Exception as e:
        st.sidebar.error(f"オペレーターファイルアップロードエラー: {str(e)}")
        operators_file = None

    # 手動入力オプション
    st.sidebar.subheader("または手動入力")
    manual_operator_input = st.sidebar.checkbox("手動でオペレーター情報を入力", value=False)

    if manual_operator_input or not operators_file:
        ops_data = create_manual_operator_input_form(desks)
        if operators_file:
            st.sidebar.warning("⚠️ CSVファイルがアップロードされていますが、手動入力が優先されます")
    elif operators_file:
        try:
            operators_df = pd.read_csv(operators_file)
            
            # 必要な列の存在チェック
            required_columns = ["name", "start", "end", "home", "desks"]
            missing_columns = [col for col in required_columns if col not in operators_df.columns]
            
            if missing_columns:
                st.sidebar.error(f"必要な列が不足しています: {missing_columns}")
                st.sidebar.info("テンプレートをダウンロードして正しい形式でアップロードしてください")
                st.stop()
            
            # データの検証と変換
            ops_data, errors = validate_operators_csv(operators_df, desks)
            
            # エラーメッセージの表示
            for error in errors:
                st.sidebar.warning(error)
            
            if ops_data:
                st.sidebar.success(f"✅ オペレーターCSV読み込み完了: {len(ops_data)}人")
                display_operator_preview(ops_data)
            else:
                st.sidebar.error("❌ 有効なオペレーターデータがありません")
                st.stop()
                
        except Exception as e:
            st.sidebar.error(f"オペレーターCSV読み込みエラー: {str(e)}")
            st.sidebar.info("ファイル形式を確認するか、手動入力を使用してください")
            st.stop()
    
    return ops_data


def setup_algorithm_section():
    """アルゴリズム設定セクション"""
    # ポイント設定
    point_unit = st.sidebar.number_input(
        "他デスク1時間あたり付与ポイント", min_value=1, max_value=100, value=1
    )

    # アルゴリズム選択
    st.sidebar.header("3️⃣ マッチングアルゴリズム選択")
    algorithm_choice = st.sidebar.selectbox(
        "使用するアルゴリズム",
        ALGORITHM_CHOICES,
        help="制約付きMulti-slot DAアルゴリズムは労働法規制などの制約を考慮した割り当てを行います"
    )

    return algorithm_choice, point_unit


def setup_shift_period_section():
    """シフト期間設定セクション"""
    st.sidebar.header("4️⃣ シフト期間設定")
    shift_period = st.sidebar.selectbox(
        "シフト期間",
        SHIFT_PERIOD_CHOICES,
        help="生成するシフトの期間を選択してください"
    )

    # カスタム期間の設定
    if shift_period == "カスタム":
        custom_days = st.sidebar.number_input(
            "日数",
            min_value=1,
            max_value=30,
            value=5,
            help="生成するシフトの日数を指定してください"
        )
        target_days = custom_days
    elif shift_period == "5日連続":
        target_days = 5
    else:
        target_days = 1

    # 開始日設定
    start_date = st.sidebar.date_input(
        "開始日",
        value=datetime.now().date(),
        help="シフトの開始日を選択してください"
    )

    return target_days, start_date


def setup_operator_schedule_section(target_days):
    """オペレーター別シフト表設定セクション"""
    if target_days > 1:
        st.sidebar.header("5️⃣ オペレーター別シフト表設定")
        operator_schedule_method = st.sidebar.selectbox(
            "表示方法",
            OPERATOR_SCHEDULE_METHODS,
            help="複数日のオペレーター別シフト表の表示方法を選択してください"
        )
        
        # 選択された方法をmerge_methodに変換
        if operator_schedule_method == "全日の割り当てを表示":
            merge_method = "all"
        elif operator_schedule_method == "統合シフト表（最初の割り当て優先）":
            merge_method = "first"
        else:  # "統合シフト表（最後の割り当て優先）"
            merge_method = "last"
    else:
        merge_method = "last"  # 1日の場合はデフォルト
    
    return merge_method


def setup_constraint_section(algorithm_choice):
    """制約設定セクション"""
    if algorithm_choice == "制約付きMulti-slot DAアルゴリズム (推奨)":
        st.sidebar.header("6️⃣ Hard Constraint設定")
        constraint_manager = ConstraintManager()
        constraint_manager.render_constraint_ui()
        return constraint_manager.create_constraints()
    return []


def execute_algorithm(algorithm_choice, req_df, ops_data, start_date, target_days, merge_method, constraints):
    """アルゴリズムを実行"""
    # DataFrameの型を確実にする
    req_df_copy = pd.DataFrame(req_df.copy())
    # dateをdatetimeに変換
    start_datetime = datetime.combine(start_date, datetime.min.time())
    
    executor = AlgorithmExecutor(req_df_copy, ops_data, start_datetime, target_days, merge_method)
    
    if algorithm_choice == "制約付きMulti-slot DAアルゴリズム (推奨)":
        return executor.execute_constrained_multi_slot_da(constraints)
    elif algorithm_choice == "Multi-slot DAアルゴリズム":
        return executor.execute_multi_slot_da()
    elif algorithm_choice == "DAアルゴリズム":
        return executor.execute_da_algorithm()
    else:  # 貪欲アルゴリズム
        return executor.execute_greedy_algorithm()


def main():
    """メイン関数"""
    # デスク要員数設定
    req_df, desks = setup_desk_requirements_section()
    
    # オペレーター設定
    ops_data = setup_operator_section(desks)
    
    # アルゴリズム設定
    algorithm_choice, point_unit = setup_algorithm_section()
    
    # シフト期間設定
    target_days, start_date = setup_shift_period_section()
    
    # オペレーター別シフト表設定
    merge_method = setup_operator_schedule_section(target_days)
    
    # 制約設定
    constraints = setup_constraint_section(algorithm_choice)
    
    # 実行ボタン
    if st.button("🛠️  Match & Generate Schedule"):
        # アルゴリズム実行
        final_schedule = execute_algorithm(
            algorithm_choice, req_df, ops_data, start_date, target_days, merge_method, constraints
        )
        
        # 結果表示
        req_df_copy = pd.DataFrame(req_df.copy())
        start_datetime = datetime.combine(start_date, datetime.min.time())
        executor = AlgorithmExecutor(req_df_copy, ops_data, start_datetime, target_days, merge_method)
        executor.display_results(point_unit)


if __name__ == "__main__":
    main() 