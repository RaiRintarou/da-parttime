#!/usr/bin/env python3
"""
CSVファイルパスのテスト

新しいディレクトリ構造でCSVファイルが正しく読み込めることをテストします。
"""

import sys
import os
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_shift_csv_paths():
    """シフト表CSVファイルのパステスト"""
    print("🧪 シフト表CSVファイルパステスト")
    print("=" * 40)
    
    # 新しいディレクトリ構造でのパス
    shift_files = [
        "data/shifts/シフト表.csv",
        "data/shifts/名称未設定.csv"
    ]
    
    for file_path in shift_files:
        print(f"📁 テストファイル: {file_path}")
        
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                print(f"✅ 読み込み成功: {len(df)}行")
                print(f"   列: {list(df.columns)}")
            except Exception as e:
                print(f"❌ 読み込みエラー: {str(e)}")
        else:
            print(f"❌ ファイルが存在しません: {file_path}")
        
        print()

def test_operator_csv_paths():
    """オペレーターCSVファイルのパステスト"""
    print("🧪 オペレーターCSVファイルパステスト")
    print("=" * 40)
    
    # 新しいディレクトリ構造でのパス
    operator_files = [
        "data/operators/operators_default.csv",
        "data/operators/operators_template.csv"
    ]
    
    for file_path in operator_files:
        print(f"📁 テストファイル: {file_path}")
        
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                print(f"✅ 読み込み成功: {len(df)}行")
                print(f"   列: {list(df.columns)}")
                
                # オペレーターCSVの場合は内容も確認
                if "name" in df.columns:
                    print(f"   オペレーター数: {len(df)}")
                    if len(df) > 0:
                        print(f"   最初のオペレーター: {df.iloc[0]['name']}")
                
            except Exception as e:
                print(f"❌ 読み込みエラー: {str(e)}")
        else:
            print(f"❌ ファイルが存在しません: {file_path}")
        
        print()

def test_directory_structure():
    """ディレクトリ構造のテスト"""
    print("🧪 ディレクトリ構造テスト")
    print("=" * 30)
    
    # 期待されるディレクトリ構造
    expected_dirs = [
        "data/shifts",
        "data/operators"
    ]
    
    for dir_path in expected_dirs:
        print(f"📁 ディレクトリ: {dir_path}")
        
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            files = os.listdir(dir_path)
            print(f"✅ 存在: {len(files)}個のファイル")
            for file in files:
                print(f"   📄 {file}")
        else:
            print(f"❌ ディレクトリが存在しません: {dir_path}")
        
        print()

def test_old_directory_removed():
    """古いディレクトリが削除されていることをテスト"""
    print("🧪 古いディレクトリ削除テスト")
    print("=" * 35)
    
    # 削除されるべき古いディレクトリ
    old_dirs = [
        "data/samples",
        "data/templates"
    ]
    
    for dir_path in old_dirs:
        print(f"📁 古いディレクトリ: {dir_path}")
        
        if os.path.exists(dir_path):
            print(f"❌ まだ存在しています: {dir_path}")
        else:
            print(f"✅ 正しく削除されています: {dir_path}")
        
        print()

if __name__ == "__main__":
    test_directory_structure()
    test_old_directory_removed()
    test_shift_csv_paths()
    test_operator_csv_paths()
    
    print("🎉 CSVファイルパステスト完了!") 