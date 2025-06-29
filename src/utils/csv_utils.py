"""
CSV処理モジュール

CSVファイルのテンプレート生成、検証、処理機能を提供します。
"""

import pandas as pd
from typing import List, Dict, Any, Tuple, Optional, Union
from io import BytesIO


def create_desk_requirements_template(desks: Optional[List[str]] = None) -> pd.DataFrame:
    """
    デスク要員数CSVテンプレートを生成
    
    Args:
        desks: デスク名のリスト（Noneの場合はデフォルト値を使用）
    
    Returns:
        デスク要員数テンプレートのDataFrame
    """
    if desks is None:
        desks = [f"Desk {c}" for c in "ABCDE"]
    
    # 時間列を生成（9-17時）
    hours = list(range(9, 18))
    cols = ["desk"] + [f"h{h:02d}" for h in hours]
    
    # テンプレートDataFrameを作成
    df = pd.DataFrame({"desk": desks}).reindex(columns=cols).fillna(0)
    return df.astype({"desk": str, **{c: int for c in cols[1:]}})


def create_operators_template() -> str:
    """
    オペレーターCSVテンプレートを生成
    
    Returns:
        オペレーターCSVテンプレートの文字列
    """
    template_data = """name,start,end,home,desks
Op1,9,12,Desk A,"Desk A,Desk B"
Op2,9,12,Desk B,"Desk A,Desk B"
Op3,10,15,Desk C,"Desk C,Desk D"
Op4,11,16,Desk D,"Desk C,Desk D"
Op5,9,17,Desk A,"Desk A,Desk B,Desk C"
"""
    return template_data


def validate_csv_upload(file_content: Union[bytes, BytesIO], required_columns: List[str], file_type: str = "CSV") -> Tuple[bool, Optional[pd.DataFrame], Optional[str]]:
    """
    CSVファイルのアップロードを検証
    
    Args:
        file_content: アップロードされたファイルの内容
        required_columns: 必要な列名のリスト
        file_type: ファイルタイプ（エラーメッセージ用）
    
    Returns:
        (成功フラグ, DataFrame, エラーメッセージ)のタプル
    """
    try:
        # bytesの場合はBytesIOに変換
        if isinstance(file_content, bytes):
            file_content = BytesIO(file_content)
        
        df = pd.read_csv(file_content)
        
        # 必要な列の存在チェック
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            error_msg = f"必要な列が不足しています: {missing_columns}"
            return False, None, error_msg
        
        return True, df, None
        
    except Exception as e:
        error_msg = f"{file_type}読み込みエラー: {str(e)}"
        return False, None, error_msg


def validate_operators_csv(df: pd.DataFrame, available_desks: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    オペレーターCSVデータを検証して変換
    
    Args:
        df: オペレーターCSVのDataFrame
        available_desks: 利用可能なデスクのリスト
    
    Returns:
        (有効なオペレーターデータのリスト, エラーメッセージのリスト)のタプル
    """
    ops_data = []
    errors = []
    
    for _, row in df.iterrows():
        try:
            # デスクリストの処理（カンマ区切りの文字列をリストに変換）
            desks_str = str(row["desks"]).strip()
            if desks_str.startswith('[') and desks_str.endswith(']'):
                # リスト形式の場合
                desks = eval(desks_str)
            else:
                # カンマ区切りの場合
                desks = [d.strip() for d in desks_str.split(',') if d.strip()]
            
            # データの検証
            if not desks:
                errors.append(f"オペレーター {row['name']}: 対応可能デスクが設定されていません")
                continue
            
            # 存在しないデスクのチェック
            invalid_desks = [d for d in desks if d not in available_desks]
            if invalid_desks:
                errors.append(f"オペレーター {row['name']}: 存在しないデスク {invalid_desks} が指定されています")
                # 無効なデスクを除外
                desks = [d for d in desks if d in available_desks]
            
            if not desks:
                errors.append(f"オペレーター {row['name']}: 有効なデスクがありません")
                continue
            
            # 所属デスクの検証
            home = str(row["home"]).strip()
            if home not in available_desks:
                errors.append(f"オペレーター {row['name']}: 所属デスク {home} が存在しません。最初の対応可能デスクに設定します")
                home = desks[0]
            
            # 時間の検証
            start = int(row["start"])
            end = int(row["end"])
            
            if start not in range(9, 18):
                errors.append(f"オペレーター {row['name']}: 開始時間 {start} が無効です。9時に設定します")
                start = 9
            
            if end not in range(10, 19):
                errors.append(f"オペレーター {row['name']}: 終了時間 {end} が無効です。18時に設定します")
                end = 18
            
            if start >= end:
                errors.append(f"オペレーター {row['name']}: 開始時間が終了時間以上です")
                continue
            
            ops_data.append({
                "name": str(row["name"]).strip(),
                "start": start,
                "end": end,
                "home": home,
                "desks": desks
            })
            
        except Exception as e:
            errors.append(f"オペレーター {row.get('name', 'Unknown')} のデータ処理エラー: {str(e)}")
            continue
    
    return ops_data, errors 