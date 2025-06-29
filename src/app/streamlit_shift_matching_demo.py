import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from algorithms import da_match, greedy_match, multi_slot_da_match

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

up_file = st.sidebar.file_uploader("CSV をアップロード", type="csv")

if up_file:
    req_df = pd.read_csv(up_file)
    if miss := set(COLS) - set(req_df.columns):
        st.error(f"列不足: {miss}"); st.stop()
    req_df = req_df[COLS].fillna(0).astype({"desk": str, **{c: int for c in COLS[1:]}})
    st.success("CSV 読込完了 ✅")
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
    ["Multi-slot DAアルゴリズム (推奨)", "DAアルゴリズム", "貪欲アルゴリズム"],
    help="Multi-slot DAアルゴリズムは日次スロットベースでより柔軟な割り当てを行います"
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
    if algorithm_choice == "Multi-slot DAアルゴリズム (推奨)":
        # Multi-slot DAアルゴリズムを使用
        assignments, schedule = multi_slot_da_match(req_df.copy(), ops_data)
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
        schedule = da_match(req_df.copy(), ops_data)
        algorithm_name = "DAアルゴリズム"
    else:
        # 貪欲アルゴリズムを使用
        schedule = greedy_match(req_df.copy(), ops_data)
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
