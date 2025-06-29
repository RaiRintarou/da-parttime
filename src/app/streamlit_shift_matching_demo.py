import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from algorithms.da_algorithm import da_match, greedy_match
from algorithms.multi_slot_da_algorithm import multi_slot_da_match
from algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match
from models.constraints import (
    create_default_constraints, MinRestHoursConstraint, MaxConsecutiveDaysConstraint,
    MaxWeeklyHoursConstraint, MaxNightShiftsPerWeekConstraint, RequiredDayOffAfterNightConstraint
)

# ---------- 共通定義 ----------
HOURS = list(range(9, 18))                      # 9:00〜17:00
COLS  = ["desk"] + [f"h{h:02d}" for h in HOURS]

def empty_requirements(desks=None):
    if desks is None:
        desks = [f"Desk {c}" for c in "ABCDE"]
    df = pd.DataFrame({"desk": desks}).reindex(columns=COLS).fillna(0)
    return df.astype({"desk": str, **{c: int for c in COLS[1:]}})

# ---------- Sidebar：CSV 入力 ----------
st.sidebar.header("1️⃣ デスク要員数：CSV アップロード")

tpl = empty_requirements()
buf = StringIO(); tpl.to_csv(buf, index=False)
st.sidebar.download_button("テンプレートDL", buf.getvalue(),
                           file_name="desk_template.csv", mime="text/csv")

# ファイルアップロード（エラーハンドリング付き）
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
    # 手動入力フォーム
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

# デスクリストを取得（型エラーを回避）
DESKS = req_df["desk"].tolist()

st.subheader("📝 デスク要員数プレビュー")
st.dataframe(req_df, use_container_width=True)

# ---------- Sidebar：ポイント設定 ----------
point_unit = st.sidebar.number_input(
    "他デスク1時間あたり付与ポイント", min_value=1, max_value=100, value=1
)

# ---------- アルゴリズム選択 ----------
st.sidebar.header("3️⃣ マッチングアルゴリズム選択")
algorithm_choice = st.sidebar.selectbox(
    "使用するアルゴリズム",
    ["制約付きMulti-slot DAアルゴリズム (推奨)", "Multi-slot DAアルゴリズム", "DAアルゴリズム", "貪欲アルゴリズム"],
    help="制約付きMulti-slot DAアルゴリズムは労働法規制などの制約を考慮した割り当てを行います"
)

# ---------- シフト期間設定 ----------
st.sidebar.header("4️⃣ シフト期間設定")
shift_period = st.sidebar.selectbox(
    "シフト期間",
    ["1日", "5日連続", "カスタム"],
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

# ---------- 制約設定 ----------
if algorithm_choice == "制約付きMulti-slot DAアルゴリズム (推奨)":
    st.sidebar.header("5️⃣ Hard Constraint設定")
    
    # 制約設定の展開/折りたたみ
    with st.sidebar.expander("制約設定 (クリックで開閉)", expanded=False):
        st.write("**労働法規制などの制約を設定してください**")
        
        # デフォルト値の初期化
        min_rest_hours = 11.0
        max_consecutive_days = 6
        max_weekly_hours = 40.0
        max_night_shifts_per_week = 2
        required_day_off_after_night = True
        enable_min_rest = True
        enable_consecutive = True
        enable_weekly_hours = True
        enable_night_shifts = True
        enable_day_off_after_night = True
        
        # 保存された設定があれば読み込み
        if "saved_constraints" in st.session_state:
            saved = st.session_state.saved_constraints
            min_rest_hours = saved.get("min_rest_hours", 11.0)
            max_consecutive_days = saved.get("max_consecutive_days", 6)
            max_weekly_hours = saved.get("max_weekly_hours", 40.0)
            max_night_shifts_per_week = saved.get("max_night_shifts_per_week", 2)
            required_day_off_after_night = saved.get("required_day_off_after_night", True)
            enable_min_rest = saved.get("enable_min_rest", True)
            enable_consecutive = saved.get("enable_consecutive", True)
            enable_weekly_hours = saved.get("enable_weekly_hours", True)
            enable_night_shifts = saved.get("enable_night_shifts", True)
            enable_day_off_after_night = saved.get("enable_day_off_after_night", True)
        
        # 制約設定の保存/読み込み
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 設定を保存"):
                # セッション状態に制約設定を保存
                st.session_state.saved_constraints = {
                    "min_rest_hours": min_rest_hours,
                    "max_consecutive_days": max_consecutive_days,
                    "max_weekly_hours": max_weekly_hours,
                    "max_night_shifts_per_week": max_night_shifts_per_week,
                    "required_day_off_after_night": required_day_off_after_night,
                    "enable_min_rest": enable_min_rest,
                    "enable_consecutive": enable_consecutive,
                    "enable_weekly_hours": enable_weekly_hours,
                    "enable_night_shifts": enable_night_shifts,
                    "enable_day_off_after_night": enable_day_off_after_night
                }
                st.success("✅ 設定を保存しました")
        
        with col2:
            if st.button("📂 設定を読み込み"):
                if "saved_constraints" in st.session_state:
                    saved = st.session_state.saved_constraints
                    # 保存された設定を適用（次の実行時に反映）
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
        min_rest_hours = st.slider(
            "最小休息時間（時間）",
            min_value=8.0,
            max_value=16.0,
            value=min_rest_hours,
            step=0.5,
            help="連続する勤務の間に必要な最小休息時間"
        )
        
        # 最大連勤日数制約
        st.subheader("📅 最大連勤日数")
        max_consecutive_days = st.slider(
            "最大連勤日数（日）",
            min_value=3,
            max_value=10,
            value=max_consecutive_days,
            step=1,
            help="連続して勤務できる最大日数"
        )
        
        # 最大週間労働時間制約
        st.subheader("⏰ 最大週間労働時間")
        max_weekly_hours = st.slider(
            "最大週間労働時間（時間）",
            min_value=20.0,
            max_value=60.0,
            value=max_weekly_hours,
            step=1.0,
            help="1週間あたりの最大労働時間"
        )
        
        # 週間最大夜勤数制約
        st.subheader("🌙 週間最大夜勤数")
        max_night_shifts_per_week = st.slider(
            "週間最大夜勤数（回）",
            min_value=1,
            max_value=5,
            value=max_night_shifts_per_week,
            step=1,
            help="1週間あたりの最大夜勤回数"
        )
        
        # 夜勤後の必須休日制約
        st.subheader("🏖️ 夜勤後の必須休日")
        required_day_off_after_night = st.checkbox(
            "夜勤後の翌日を休日とする",
            value=required_day_off_after_night,
            help="夜勤の翌日は必ず休日にする"
        )
        
        # 制約の有効/無効設定
        st.subheader("⚙️ 制約の有効/無効")
        enable_min_rest = st.checkbox("最小休息時間制約を有効にする", value=enable_min_rest)
        enable_consecutive = st.checkbox("最大連勤日数制約を有効にする", value=enable_consecutive)
        enable_weekly_hours = st.checkbox("最大週間労働時間制約を有効にする", value=enable_weekly_hours)
        enable_night_shifts = st.checkbox("週間最大夜勤数制約を有効にする", value=enable_night_shifts)
        enable_day_off_after_night = st.checkbox("夜勤後の必須休日制約を有効にする", value=enable_day_off_after_night)
        
        # 制約設定のプレビュー
        st.subheader("📋 制約設定プレビュー")
        constraints_preview = []
        if enable_min_rest:
            constraints_preview.append(f"• 最小休息時間: {min_rest_hours}時間")
        if enable_consecutive:
            constraints_preview.append(f"• 最大連勤日数: {max_consecutive_days}日")
        if enable_weekly_hours:
            constraints_preview.append(f"• 最大週間労働時間: {max_weekly_hours}時間")
        if enable_night_shifts:
            constraints_preview.append(f"• 週間最大夜勤数: {max_night_shifts_per_week}回")
        if enable_day_off_after_night:
            constraints_preview.append("• 夜勤後の必須休日: 有効")
        
        if constraints_preview:
            for constraint in constraints_preview:
                st.write(constraint)
        else:
            st.warning("⚠️ 有効な制約が設定されていません")
    
    # 制約リストを作成
    constraints = []
    if enable_min_rest:
        constraints.append(MinRestHoursConstraint(min_rest_hours=min_rest_hours))
    if enable_consecutive:
        constraints.append(MaxConsecutiveDaysConstraint(max_consecutive_days=max_consecutive_days))
    if enable_weekly_hours:
        constraints.append(MaxWeeklyHoursConstraint(max_weekly_hours=max_weekly_hours))
    if enable_night_shifts:
        constraints.append(MaxNightShiftsPerWeekConstraint(max_night_shifts_per_week=max_night_shifts_per_week))
    if enable_day_off_after_night:
        constraints.append(RequiredDayOffAfterNightConstraint())
    
    # 制約が設定されていない場合の警告
    if not constraints:
        st.sidebar.warning("⚠️ 制約が設定されていません。デフォルト制約が適用されます。")
        constraints = create_default_constraints()

# ---------- オペレータ入力 ----------
st.sidebar.header("2️⃣ オペレータ情報")
num_ops = st.sidebar.number_input("オペレータ人数", 1, 200, 10)

ops_data = []
with st.expander("オペレータ設定 (クリックで開閉)"):
    for i in range(num_ops):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 6])
        name  = c1.text_input(f"名前 {i+1}", f"Op{i+1}")
        start = c2.selectbox("開始", HOURS, key=f"s{i}")
        end   = c2.selectbox("終了", [h+1 for h in HOURS],
                             index=len(HOURS)-1, key=f"e{i}")
        home  = c3.selectbox("所属デスク", DESKS, key=f"h{i}")        # ← NEW
        desks = c4.multiselect("対応可能デスク", DESKS, DESKS, key=f"d{i}")
        ops_data.append({"name": name, "start": start, "end": end,
                         "home": home, "desks": desks})

# ---------- マッチング ----------
# 従来の貪欲アルゴリズムは削除し、DAアルゴリズムを使用

# ---------- ポイント計算 ----------
def calc_points(sched_df: pd.DataFrame, ops: list, unit: int):
    home_map = {op["name"]: op["home"] for op in ops}
    pts = {d: 0 for d in DESKS}
    for op_name, row in sched_df.iterrows():
        home = home_map.get(op_name, "")
        for desk in row.values:
            if desk and desk != home:
                pts[home] += unit
    
    # 型エラーを回避するため、辞書からDataFrameを作成
    pts_data = {"desk": list(pts.keys()), "points": list(pts.values())}
    return pd.DataFrame(pts_data).sort_values("desk")

# ---------- 実行ボタン ----------
if st.button("🛠️  Match & Generate Schedule"):
    # 選択されたアルゴリズムでマッチング
    if algorithm_choice == "制約付きMulti-slot DAアルゴリズム (推奨)":
        # 制約付きMulti-slot DAアルゴリズムを使用
        all_assignments = []
        all_schedules = []
        
        for day in range(target_days):
            current_date = datetime.combine(start_date, datetime.min.time()) + timedelta(days=day)
            assignments, schedule = constrained_multi_slot_da_match(
                pd.DataFrame(req_df.copy()), ops_data, constraints, current_date
            )
            all_assignments.extend(assignments)
            all_schedules.append(schedule)
        
        algorithm_name = "制約付きMulti-slot DAアルゴリズム"
        
        # 制約違反チェック（全期間）
        from models.constraints import ConstraintValidator
        validator = ConstraintValidator(constraints)
        violations = validator.get_violations(all_assignments, [])
        
        if violations:
            st.warning("⚠️ 制約違反が検出されました:")
            for violation in violations:
                st.write(f"  • {violation}")
        else:
            st.success("✅ すべての制約を満たしています")
        
        # 制約設定の詳細表示
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
        
        # 割り当て結果の詳細表示
        st.subheader("📋 詳細割り当て結果")
        assignment_data = []
        for assignment in all_assignments:
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
        
        # 5日分のスケジュール表を統合
        if target_days > 1:
            st.subheader(f"📅 {target_days}日分の統合シフト表")
            # 各日のシフト表に日付を追加して列名を一意にする
            renamed_schedules = []
            for i, day_schedule in enumerate(all_schedules):
                day_date = start_date + timedelta(days=i)
                date_str = day_date.strftime('%m-%d')
                # 列名に日付を追加
                renamed_cols = {col: f"{col}_{date_str}" for col in day_schedule.columns}
                renamed_schedule = day_schedule.rename(columns=renamed_cols)
                renamed_schedules.append(renamed_schedule)
            
            combined_schedule = pd.concat(renamed_schedules, axis=1)
            st.dataframe(combined_schedule, use_container_width=True)
        else:
            st.subheader("📅 生成されたシフト表")
            st.dataframe(all_schedules[0], use_container_width=True)
        
        schedule = all_schedules[0] if target_days == 1 else combined_schedule
        
    elif algorithm_choice == "Multi-slot DAアルゴリズム":
        # Multi-slot DAアルゴリズムを使用
        all_assignments = []
        all_schedules = []
        
        for day in range(target_days):
            current_date = datetime.combine(start_date, datetime.min.time()) + timedelta(days=day)
            assignments, schedule = multi_slot_da_match(
                pd.DataFrame(req_df.copy()), ops_data, current_date
            )
            all_assignments.extend(assignments)
            all_schedules.append(schedule)
        
        algorithm_name = "Multi-slot DAアルゴリズム"
        
        # 割り当て結果の詳細表示
        st.subheader("📋 詳細割り当て結果")
        assignment_data = []
        for assignment in all_assignments:
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
        
        # 5日分のスケジュール表を統合
        if target_days > 1:
            st.subheader(f"📅 {target_days}日分の統合シフト表")
            # 各日のシフト表に日付を追加して列名を一意にする
            renamed_schedules = []
            for i, day_schedule in enumerate(all_schedules):
                day_date = start_date + timedelta(days=i)
                date_str = day_date.strftime('%m-%d')
                # 列名に日付を追加
                renamed_cols = {col: f"{col}_{date_str}" for col in day_schedule.columns}
                renamed_schedule = day_schedule.rename(columns=renamed_cols)
                renamed_schedules.append(renamed_schedule)
            
            combined_schedule = pd.concat(renamed_schedules, axis=1)
            st.dataframe(combined_schedule, use_container_width=True)
        else:
            st.subheader("📅 生成されたシフト表")
            st.dataframe(all_schedules[0], use_container_width=True)
        
        schedule = all_schedules[0] if target_days == 1 else combined_schedule
        
    elif algorithm_choice == "DAアルゴリズム":
        # 従来のDAアルゴリズムを使用
        all_schedules = []
        
        for day in range(target_days):
            current_date = datetime.combine(start_date, datetime.min.time()) + timedelta(days=day)
            schedule = da_match(pd.DataFrame(req_df.copy()), ops_data)
            all_schedules.append(schedule)
        
        algorithm_name = "DAアルゴリズム"
        
        # 5日分のスケジュール表を統合
        if target_days > 1:
            st.subheader(f"📅 {target_days}日分の統合シフト表")
            # 各日のシフト表に日付を追加して列名を一意にする
            renamed_schedules = []
            for i, day_schedule in enumerate(all_schedules):
                day_date = start_date + timedelta(days=i)
                date_str = day_date.strftime('%m-%d')
                # 列名に日付を追加
                renamed_cols = {col: f"{col}_{date_str}" for col in day_schedule.columns}
                renamed_schedule = day_schedule.rename(columns=renamed_cols)
                renamed_schedules.append(renamed_schedule)
            
            combined_schedule = pd.concat(renamed_schedules, axis=1)
            st.dataframe(combined_schedule, use_container_width=True)
            schedule = combined_schedule
        else:
            st.subheader("📅 生成されたシフト表")
            st.dataframe(all_schedules[0], use_container_width=True)
            schedule = all_schedules[0]
    else:
        # 貪欲アルゴリズムを使用
        all_schedules = []
        
        for day in range(target_days):
            current_date = datetime.combine(start_date, datetime.min.time()) + timedelta(days=day)
            schedule = greedy_match(pd.DataFrame(req_df.copy()), ops_data)
            all_schedules.append(schedule)
        
        algorithm_name = "貪欲アルゴリズム"
        
        # 5日分のスケジュール表を統合
        if target_days > 1:
            st.subheader(f"📅 {target_days}日分の統合シフト表")
            # 各日のシフト表に日付を追加して列名を一意にする
            renamed_schedules = []
            for i, day_schedule in enumerate(all_schedules):
                day_date = start_date + timedelta(days=i)
                date_str = day_date.strftime('%m-%d')
                # 列名に日付を追加
                renamed_cols = {col: f"{col}_{date_str}" for col in day_schedule.columns}
                renamed_schedule = day_schedule.rename(columns=renamed_cols)
                renamed_schedules.append(renamed_schedule)
            
            combined_schedule = pd.concat(renamed_schedules, axis=1)
            st.dataframe(combined_schedule, use_container_width=True)
            schedule = combined_schedule
        else:
            st.subheader("📅 生成されたシフト表")
            st.dataframe(all_schedules[0], use_container_width=True)
            schedule = all_schedules[0]

    # 期間情報の表示
    st.subheader(f"📊 シフト情報")
    st.write(f"**期間**: {start_date.strftime('%Y-%m-%d')} から {target_days}日間")
    st.write(f"**アルゴリズム**: {algorithm_name}")
    st.write(f"**生成日数**: {target_days}日")

    pt_df = calc_points(schedule, ops_data, point_unit)
    st.subheader("🏅 デスク別ポイント補填")
    st.dataframe(pt_df, use_container_width=True)

    csv_sched = StringIO(); schedule.to_csv(csv_sched)
    st.download_button("シフト表 CSV DL",
                       csv_sched.getvalue(),
                       file_name=f"shift_{start_date.strftime('%Y%m%d')}_{target_days}days_{datetime.now():%Y%m%d_%H%M}.csv")

    csv_pts = StringIO(); pt_df.to_csv(csv_pts, index=False)
    st.download_button("ポイント集計 CSV DL",
                       csv_pts.getvalue(),
                       file_name=f"points_{start_date.strftime('%Y%m%d')}_{target_days}days_{datetime.now():%Y%m%d_%H%M}.csv")

    # 5日分の場合は個別日のCSVも提供
    if target_days > 1:
        st.subheader("📁 個別日のシフト表ダウンロード")
        for i, day_schedule in enumerate(all_schedules):
            day_date = start_date + timedelta(days=i)
            csv_individual = StringIO(); day_schedule.to_csv(csv_individual)
            st.download_button(
                f"{day_date.strftime('%Y-%m-%d')} シフト表 CSV DL",
                csv_individual.getvalue(),
                file_name=f"shift_{day_date.strftime('%Y%m%d')}_{datetime.now():%Y%m%d_%H%M}.csv"
            )
