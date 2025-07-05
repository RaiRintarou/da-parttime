"""
ログ管理モジュール

このモジュールは、アプリケーション全体で使用されるログ機能を提供します。
設定ファイルと連携し、適切なログレベルとフォーマットを設定します。

主な機能:
- ログレベルの設定
- ログファイルへの出力
- ログローテーション
- 構造化ログ出力
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from .config import get_config


class ColoredFormatter(logging.Formatter):
    """カラー付きログフォーマッター"""
    
    # ANSIカラーコード
    COLORS = {
        'DEBUG': '\033[36m',    # シアン
        'INFO': '\033[32m',     # 緑
        'WARNING': '\033[33m',  # 黄
        'ERROR': '\033[31m',    # 赤
        'CRITICAL': '\033[35m', # マゼンタ
        'RESET': '\033[0m'      # リセット
    }
    
    def format(self, record):
        """ログレコードをフォーマット"""
        # カラーコードを追加
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター"""
    
    def format(self, record):
        """構造化されたログメッセージをフォーマット"""
        # 基本情報
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage()
        }
        
        # 例外情報があれば追加
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return str(log_entry)


class LoggerManager:
    """ログマネージャークラス"""
    
    def __init__(self):
        """ログマネージャーを初期化"""
        self._initialized = False
        self._config = get_config()
    
    def setup_logging(self, log_level: Optional[str] = None) -> None:
        """ログ設定を初期化"""
        if self._initialized:
            return
        
        # 設定からログレベルを取得
        if log_level is None:
            log_level = self._config.log_level
        
        # ログレベルを設定
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # ルートロガーを設定
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # 既存のハンドラーをクリア
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # コンソールハンドラーを追加
        self._setup_console_handler(root_logger, numeric_level)
        
        # ファイルハンドラーを追加
        self._setup_file_handler(root_logger, numeric_level)
        
        # 特定のライブラリのログレベルを調整
        self._adjust_library_log_levels()
        
        self._initialized = True
        
        # 初期化完了をログ出力
        logging.info("ログシステムを初期化しました")
    
    def _setup_console_handler(self, logger: logging.Logger, level: int) -> None:
        """コンソールハンドラーを設定"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # デバッグモードの場合はカラー付きフォーマッターを使用
        if self._config.debug:
            formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    def _setup_file_handler(self, logger: logging.Logger, level: int) -> None:
        """ファイルハンドラーを設定"""
        # ログディレクトリを作成
        log_file = self._config.log_file
        log_dir = log_file.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # ローテーティングファイルハンドラーを作成
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=self._parse_size(self._config.log_max_size),
            backupCount=self._config.log_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        # 構造化フォーマッターを使用
        formatter = StructuredFormatter()
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
    
    def _parse_size(self, size_str: str) -> int:
        """サイズ文字列をバイト数に変換"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def _adjust_library_log_levels(self) -> None:
        """特定のライブラリのログレベルを調整"""
        # 外部ライブラリのログレベルを調整
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('streamlit').setLevel(logging.INFO)
        
        # デバッグモードでない場合は、詳細なログを抑制
        if not self._config.debug:
            logging.getLogger('matplotlib').setLevel(logging.WARNING)
            logging.getLogger('PIL').setLevel(logging.WARNING)


# グローバルログマネージャーインスタンス
logger_manager = LoggerManager()


def setup_logging(log_level: Optional[str] = None) -> None:
    """ログ設定を初期化"""
    logger_manager.setup_logging(log_level)


def get_logger(name: str) -> logging.Logger:
    """指定された名前のロガーを取得"""
    return logging.getLogger(name)


def log_extra_fields(logger: logging.Logger, level: int, message: str, **kwargs) -> None:
    """追加フィールド付きでログを出力"""
    # 構造化ログメッセージを作成
    structured_message = f"{message} | {kwargs}"
    logger.log(level, structured_message)


# 使用例
if __name__ == "__main__":
    # ログ設定を初期化
    setup_logging()
    
    # ロガーを取得
    logger = get_logger(__name__)
    
    # 通常のログ出力
    logger.info("アプリケーションが起動しました")
    logger.warning("設定ファイルが見つかりません")
    logger.error("データベース接続に失敗しました")
    
    # 追加フィールド付きのログ出力
    log_extra_fields(
        logger, 
        logging.INFO, 
        "ユーザーアクション", 
        user_id="12345", 
        action="login", 
        ip_address="192.168.1.1"
    ) 