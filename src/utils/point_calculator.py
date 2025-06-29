"""
ポイント計算モジュール

シフト割り当てに基づくポイント計算機能を提供します。
"""

import pandas as pd
from typing import List, Dict, Any


def calc_points(sched_df: pd.DataFrame, ops: list, unit: int) -> pd.DataFrame:
    """
    シフト表からデスク別ポイントを計算
    
    Args:
        sched_df: シフト表（オペレーターを行、デスクを列）
        ops: オペレーターデータのリスト
        unit: 他デスク1時間あたり付与ポイント
    
    Returns:
        デスク別ポイント集計のDataFrame
    """
    # オペレーター名から所属デスクへのマッピングを作成
    home_map = {op["name"]: op["home"] for op in ops}
    
    # デスク別ポイントを初期化
    pts = {}
    for op in ops:
        home = op["home"]
        if home not in pts:
            pts[home] = 0
    
    # 各オペレーターの他デスク勤務をカウント
    for op_name, row in sched_df.iterrows():
        home = home_map.get(op_name, "")
        for desk in row.values:
            if desk and desk != home:
                pts[home] += unit
    
    # 型エラーを回避するため、辞書からDataFrameを作成
    pts_data = {"desk": list(pts.keys()), "points": list(pts.values())}
    return pd.DataFrame(pts_data).sort_values("desk") 