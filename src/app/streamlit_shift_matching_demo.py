import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from algorithms.da_algorithm import da_match, greedy_match
from algorithms.multi_slot_da_algorithm import multi_slot_da_match
from algorithms.constrained_multi_slot_da_algorithm import constrained_multi_slot_da_match
from models.constraints import create_default_constraints

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
        constraints = create_default_constraints()
        assignments, schedule = constrained_multi_slot_da_match(pd.DataFrame(req_df.copy()), ops_data, constraints)
        algorithm_name = "制約付きMulti-slot DAアルゴリズム"
        
        # 制約違反チェック
        from models.constraints import ConstraintValidator
        validator = ConstraintValidator(constraints)
        violations = validator.get_violations(assignments, [])
        
        if violations:
            st.warning("⚠️ 制約違反が検出されました:")
            for violation in violations:
                st.write(f"  • {violation}")
        else:
            st.success("✅ すべての制約を満たしています")
        
        # 割り当て結果の詳細表示
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
        
    elif algorithm_choice == "Multi-slot DAアルゴリズム":
        # Multi-slot DAアルゴリズムを使用
        assignments, schedule = multi_slot_da_match(pd.DataFrame(req_df.copy()), ops_data)
        algorithm_name = "Multi-slot DAアルゴリズム"
        
        # 割り当て結果の詳細表示
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
        
    elif algorithm_choice == "DAアルゴリズム":
        # 従来のDAアルゴリズムを使用
        schedule = da_match(pd.DataFrame(req_df.copy()), ops_data)
        algorithm_name = "DAアルゴリズム"
    else:
        # 貪欲アルゴリズムを使用
        schedule = greedy_match(pd.DataFrame(req_df.copy()), ops_data)
        algorithm_name = "貪欲アルゴリズム"

    st.subheader(f"📅 生成されたシフト表 ({algorithm_name})")
    st.dataframe(schedule, use_container_width=True)

    pt_df = calc_points(schedule, ops_data, point_unit)
    st.subheader("🏅 デスク別ポイント補填")
    st.dataframe(pt_df, use_container_width=True)

    csv_sched = StringIO(); schedule.to_csv(csv_sched)
    st.download_button("シフト表 CSV DL",
                       csv_sched.getvalue(),
                       file_name=f"shift_{datetime.now():%Y%m%d_%H%M}.csv")

    csv_pts = StringIO(); pt_df.to_csv(csv_pts, index=False)
    st.download_button("ポイント集計 CSV DL",
                       csv_pts.getvalue(),
                       file_name=f"points_{datetime.now():%Y%m%d_%H%M}.csv")
