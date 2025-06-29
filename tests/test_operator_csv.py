#!/usr/bin/env python3
"""
オペレーターCSV読み込み機能のテスト

CSVファイルからオペレーター情報を読み込む機能をテストします。
"""

import sys
import os
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_operator_csv_parsing():
    """オペレーターCSV解析のテスト"""
    print("🧪 オペレーターCSV解析テスト開始")
    print("=" * 50)
    
    # テスト用CSVデータ
    test_csv_data = """name,start,end,home,desks
Op1,9,12,Desk A,"Desk A,Desk B"
Op2,9,12,Desk B,"Desk A,Desk B"
Op3,10,15,Desk C,"Desk C,Desk D"
Op4,11,16,Desk D,"Desk C,Desk D"
Op5,9,17,Desk A,"Desk A,Desk B,Desk C"
Op6,10,14,Desk B,"Desk A,Desk B"
Op7,13,17,Desk C,"Desk C,Desk D"
Op8,9,15,Desk D,"Desk C,Desk D"
Op9,11,16,Desk A,"Desk A,Desk B,Desk C"
Op10,9,13,Desk B,"Desk A,Desk B"
"""
    
    print("📊 テストCSVデータ:")
    print(test_csv_data)
    print()
    
    try:
        # CSVデータをDataFrameに変換
        operators_df = pd.read_csv(StringIO(test_csv_data))
        print("✅ CSV読み込み成功")
        print("📋 読み込まれたデータ:")
        print(operators_df)
        print()
        
        # 必要な列の存在チェック
        required_columns = ["name", "start", "end", "home", "desks"]
        missing_columns = [col for col in required_columns if col not in operators_df.columns]
        
        if missing_columns:
            print(f"❌ 必要な列が不足しています: {missing_columns}")
            return
        else:
            print("✅ 必要な列がすべて存在します")
        
        # デスクリスト（テスト用）
        DESKS = ["Desk A", "Desk B", "Desk C", "Desk D"]
        HOURS = list(range(9, 18))
        
        # データの検証と変換
        ops_data = []
        for _, row in operators_df.iterrows():
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
                    print(f"⚠️ オペレーター {row['name']}: 対応可能デスクが設定されていません")
                    continue
                
                # 存在しないデスクのチェック
                invalid_desks = [d for d in desks if d not in DESKS]
                if invalid_desks:
                    print(f"⚠️ オペレーター {row['name']}: 存在しないデスク {invalid_desks} が指定されています")
                    # 無効なデスクを除外
                    desks = [d for d in desks if d in DESKS]
                
                if not desks:
                    print(f"❌ オペレーター {row['name']}: 有効なデスクがありません")
                    continue
                
                # 所属デスクの検証
                home = str(row["home"]).strip()
                if home not in DESKS:
                    print(f"⚠️ オペレーター {row['name']}: 所属デスク {home} が存在しません。最初の対応可能デスクに設定します")
                    home = desks[0]
                
                # 時間の検証
                start = int(row["start"])
                end = int(row["end"])
                
                if start not in HOURS:
                    print(f"⚠️ オペレーター {row['name']}: 開始時間 {start} が無効です。9時に設定します")
                    start = 9
                
                if end not in [h+1 for h in HOURS]:
                    print(f"⚠️ オペレーター {row['name']}: 終了時間 {end} が無効です。18時に設定します")
                    end = 18
                
                if start >= end:
                    print(f"❌ オペレーター {row['name']}: 開始時間が終了時間以上です")
                    continue
                
                ops_data.append({
                    "name": str(row["name"]).strip(),
                    "start": start,
                    "end": end,
                    "home": home,
                    "desks": desks
                })
                
                print(f"✅ オペレーター {row['name']}: 正常に処理されました")
                
            except Exception as e:
                print(f"❌ オペレーター {row.get('name', 'Unknown')} のデータ処理エラー: {str(e)}")
                continue
        
        print()
        print("📋 処理結果:")
        print(f"  総オペレーター数: {len(operators_df)}")
        print(f"  正常に処理されたオペレーター数: {len(ops_data)}")
        print()
        
        if ops_data:
            print("👥 オペレーター情報詳細:")
            for i, op in enumerate(ops_data, 1):
                print(f"  {i}. {op['name']}: {op['start']}時-{op['end']}時, 所属: {op['home']}, 対応: {op['desks']}")
            
            # シフト生成テスト
            print()
            print("🚀 シフト生成テスト:")
            
            # デスク要件（テスト用）
            desks_data = {
                "desk": ["Desk A", "Desk B", "Desk C", "Desk D"],
                "h09": [2, 2, 1, 1],
                "h10": [2, 2, 1, 1],
                "h11": [2, 2, 1, 1],
                "h12": [1, 1, 1, 1],
                "h13": [1, 1, 1, 1],
                "h14": [1, 1, 1, 1],
                "h15": [1, 1, 1, 1],
                "h16": [1, 1, 1, 1],
                "h17": [1, 1, 1, 1]
            }
            
            hourly_requirements = pd.DataFrame(desks_data)
            print("デスク要件:")
            print(hourly_requirements)
            print()
            
            # Multi-slot DAアルゴリズムでテスト
            from algorithms.multi_slot_da_algorithm import multi_slot_da_match
            
            try:
                assignments, schedule = multi_slot_da_match(hourly_requirements, ops_data)
                print("✅ シフト生成成功!")
                print("📅 生成されたシフト表:")
                print(schedule)
                
            except Exception as e:
                print(f"❌ シフト生成エラー: {str(e)}")
        
    except Exception as e:
        print(f"❌ CSV読み込みエラー: {str(e)}")

def test_invalid_csv_handling():
    """無効なCSVデータの処理テスト"""
    print("\n🧪 無効なCSVデータ処理テスト")
    print("=" * 45)
    
    # 無効なデータのテストケース
    invalid_cases = [
        {
            "name": "列不足",
            "data": """name,start,end
Op1,9,12
Op2,9,12
"""
        },
        {
            "name": "無効な時間",
            "data": """name,start,end,home,desks
Op1,25,30,Desk A,"Desk A,Desk B"
Op2,9,12,Desk B,"Desk A,Desk B"
"""
        },
        {
            "name": "存在しないデスク",
            "data": """name,start,end,home,desks
Op1,9,12,Desk X,"Desk X,Desk Y"
Op2,9,12,Desk B,"Desk A,Desk B"
"""
        },
        {
            "name": "開始時間が終了時間以上",
            "data": """name,start,end,home,desks
Op1,15,10,Desk A,"Desk A,Desk B"
Op2,9,12,Desk B,"Desk A,Desk B"
"""
        }
    ]
    
    for case in invalid_cases:
        print(f"📋 テストケース: {case['name']}")
        try:
            operators_df = pd.read_csv(StringIO(case['data']))
            print("  CSV読み込み: ✅")
            
            # 基本的な検証
            required_columns = ["name", "start", "end", "home", "desks"]
            missing_columns = [col for col in required_columns if col not in operators_df.columns]
            
            if missing_columns:
                print(f"  列不足検出: ✅ ({missing_columns})")
            else:
                print("  列不足検出: ❌ (検出されませんでした)")
                
        except Exception as e:
            print(f"  CSV読み込みエラー: {str(e)}")
        
        print()

if __name__ == "__main__":
    test_operator_csv_parsing()
    test_invalid_csv_handling()
    
    print("\n🎉 オペレーターCSV読み込みテスト完了!")
    print("StreamlitアプリでオペレーターCSV読み込み機能をテストしてください。") 