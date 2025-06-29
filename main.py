#!/usr/bin/env python3
"""
シフトマッチングシステム - メインエントリーポイント

このファイルは、アプリケーションを起動するためのメインエントリーポイントです。
"""

import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    # Streamlitアプリを起動
    import subprocess
    import streamlit.web.cli as stcli
    
    # src/app/streamlit_shift_matching_demo.pyを起動
    app_path = os.path.join("src", "app", "streamlit_shift_matching_demo.py")
    
    if os.path.exists(app_path):
        print("🚀 シフトマッチングシステムを起動中...")
        print(f"📁 アプリケーションパス: {app_path}")
        print("🌐 ブラウザで http://localhost:8501 にアクセスしてください")
        print("📝 ファイルアップロードでエラーが発生した場合は、手動入力オプションを使用してください")
        
        # Streamlitを起動（設定ファイルを適用）
        sys.argv = [
            "streamlit", "run", app_path, 
            "--server.port=8501",
            "--server.maxUploadSize=200",
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false"
        ]
        sys.exit(stcli.main())
    else:
        print(f"❌ エラー: アプリケーションファイルが見つかりません: {app_path}")
        sys.exit(1) 