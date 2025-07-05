#!/usr/bin/env python3
"""
Shift Optimiser PoC - メインエントリーポイント

このモジュールは、シフト最適化システムのメインエントリーポイントです。
設定の初期化、ログシステムのセットアップ、アプリケーションの起動を行います。

主な機能:
- 環境設定の読み込み
- ログシステムの初期化
- Streamlitアプリケーションの起動
- エラーハンドリング
"""

import sys
import traceback
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.config import get_config
from src.utils.logger import setup_logging, get_logger


def main():
    """メイン関数"""
    try:
        # 設定を読み込み
        config = get_config()
        
        # ログシステムを初期化
        setup_logging()
        logger = get_logger(__name__)
        
        logger.info("Shift Optimiser PoC を起動しています...")
        logger.info(f"アプリケーション名: {config.app_name}")
        logger.info(f"バージョン: {config.app_version}")
        logger.info(f"デバッグモード: {config.debug}")
        
        # Streamlitアプリケーションを起動
        import streamlit as st
        from src.app.streamlit_shift_matching_demo import main as streamlit_main
        
        logger.info("Streamlitアプリケーションを起動しています...")
        streamlit_main()
        
    except Exception as e:
        # エラーログを出力
        error_logger = get_logger("error")
        error_logger.error(f"アプリケーション起動エラー: {str(e)}")
        error_logger.error(f"詳細: {traceback.format_exc()}")
        
        # コンソールにもエラーを出力
        print(f"エラーが発生しました: {str(e)}")
        print("詳細はログファイルを確認してください。")
        
        sys.exit(1)


if __name__ == "__main__":
    main() 