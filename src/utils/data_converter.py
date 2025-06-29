"""
データ変換モジュール

オペレーターデータの形式変換機能を提供します。
"""

from typing import List, Dict, Any


def convert_ops_data_to_operator_availability(ops_data: list):
    """
    辞書形式のオペレーターデータをOperatorAvailabilityオブジェクトに変換（1時間単位）
    
    Args:
        ops_data: 辞書形式のオペレーターデータのリスト
    
    Returns:
        OperatorAvailabilityオブジェクトのリスト
    """
    from models.multi_slot_models import OperatorAvailability
    
    operators = []
    for op_data in ops_data:
        # スロット対応可能判定
        available_slots = set()
        preferred_slots = set()
        
        # オペレータの勤務時間
        op_hours = list(range(op_data["start"], op_data["end"]))
        
        # 対応可能なスロットを判定（1時間単位）
        for hour in op_hours:
            if 9 <= hour < 18:  # 9時から17時まで
                slot_id = f"h{hour:02d}"
                available_slots.add(slot_id)
                # 所属デスクが対応可能デスクに含まれている場合を優先
                if op_data["home"] in op_data["desks"]:
                    preferred_slots.add(slot_id)
        
        operator = OperatorAvailability(
            operator_name=op_data["name"],
            available_slots=available_slots,
            preferred_slots=preferred_slots
        )
        operators.append(operator)
    
    return operators 