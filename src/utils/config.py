"""
設定管理モジュール

このモジュールは、アプリケーション全体で使用される設定値を管理します。
環境変数から値を読み込み、適切なデフォルト値を提供します。
direnvとの連携を考慮し、開発環境での設定管理を簡素化します。

主な機能:
- 環境変数からの設定値読み込み
- デフォルト値の提供
- 設定値の型変換
- 設定値の検証
"""

import os
import logging
from typing import Optional, Union
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    """アプリケーション設定クラス"""
    
    # アプリケーション基本設定
    app_name: str
    app_version: str
    debug: bool
    log_level: str
    
    # データベース設定
    database_url: str
    
    # セキュリティ設定
    secret_key: str
    allowed_hosts: list[str]
    
    # Streamlit設定
    streamlit_server_port: int
    streamlit_server_address: str
    
    # アルゴリズム設定
    da_algorithm_max_iterations: int
    da_algorithm_temperature: float
    da_algorithm_cooling_rate: float
    
    # 制約設定
    default_min_rest_hours: int
    default_max_consecutive_days: int
    default_max_weekly_hours: int
    default_max_night_shifts_per_week: int
    
    # ファイルパス設定
    data_dir: Path
    operators_file: Path
    shifts_file: Path
    
    # ログ設定
    log_file: Path
    log_max_size: str
    log_backup_count: int
    
    # 開発用設定
    enable_hot_reload: bool
    enable_debug_toolbar: bool


class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self):
        """設定マネージャーを初期化"""
        self._config: Optional[AppConfig] = None
        self._logger = logging.getLogger(__name__)
    
    def load_config(self) -> AppConfig:
        """環境変数から設定を読み込み、AppConfigオブジェクトを返す"""
        if self._config is None:
            self._config = self._create_config()
        return self._config
    
    def _create_config(self) -> AppConfig:
        """環境変数から設定オブジェクトを作成"""
        
        # アプリケーション基本設定
        app_name = os.getenv('APP_NAME', 'Shift Optimiser PoC')
        app_version = os.getenv('APP_VERSION', '0.1.0')
        debug = self._parse_bool(os.getenv('DEBUG', 'true'))
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # データベース設定
        database_url = os.getenv('DATABASE_URL', 'sqlite:///./data/shift_optimiser.db')
        
        # セキュリティ設定
        secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
        allowed_hosts_str = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
        allowed_hosts = [host.strip() for host in allowed_hosts_str.split(',')]
        
        # Streamlit設定
        streamlit_server_port = int(os.getenv('STREAMLIT_SERVER_PORT', '8501'))
        streamlit_server_address = os.getenv('STREAMLIT_SERVER_ADDRESS', '0.0.0.0')
        
        # アルゴリズム設定
        da_algorithm_max_iterations = int(os.getenv('DA_ALGORITHM_MAX_ITERATIONS', '1000'))
        da_algorithm_temperature = float(os.getenv('DA_ALGORITHM_TEMPERATURE', '1.0'))
        da_algorithm_cooling_rate = float(os.getenv('DA_ALGORITHM_COOLING_RATE', '0.95'))
        
        # 制約設定
        default_min_rest_hours = int(os.getenv('DEFAULT_MIN_REST_HOURS', '8'))
        default_max_consecutive_days = int(os.getenv('DEFAULT_MAX_CONSECUTIVE_DAYS', '6'))
        default_max_weekly_hours = int(os.getenv('DEFAULT_MAX_WEEKLY_HOURS', '40'))
        default_max_night_shifts_per_week = int(os.getenv('DEFAULT_MAX_NIGHT_SHIFTS_PER_WEEK', '3'))
        
        # ファイルパス設定
        data_dir = Path(os.getenv('DATA_DIR', './data'))
        operators_file = Path(os.getenv('OPERATORS_FILE', './data/operators/operators_default.csv'))
        shifts_file = Path(os.getenv('SHIFTS_FILE', './data/shifts/シフト表.csv'))
        
        # ログ設定
        log_file = Path(os.getenv('LOG_FILE', './logs/app.log'))
        log_max_size = os.getenv('LOG_MAX_SIZE', '10MB')
        log_backup_count = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        
        # 開発用設定
        enable_hot_reload = self._parse_bool(os.getenv('ENABLE_HOT_RELOAD', 'true'))
        enable_debug_toolbar = self._parse_bool(os.getenv('ENABLE_DEBUG_TOOLBAR', 'false'))
        
        # 設定オブジェクトを作成
        config = AppConfig(
            app_name=app_name,
            app_version=app_version,
            debug=debug,
            log_level=log_level,
            database_url=database_url,
            secret_key=secret_key,
            allowed_hosts=allowed_hosts,
            streamlit_server_port=streamlit_server_port,
            streamlit_server_address=streamlit_server_address,
            da_algorithm_max_iterations=da_algorithm_max_iterations,
            da_algorithm_temperature=da_algorithm_temperature,
            da_algorithm_cooling_rate=da_algorithm_cooling_rate,
            default_min_rest_hours=default_min_rest_hours,
            default_max_consecutive_days=default_max_consecutive_days,
            default_max_weekly_hours=default_max_weekly_hours,
            default_max_night_shifts_per_week=default_max_night_shifts_per_week,
            data_dir=data_dir,
            operators_file=operators_file,
            shifts_file=shifts_file,
            log_file=log_file,
            log_max_size=log_max_size,
            log_backup_count=log_backup_count,
            enable_hot_reload=enable_hot_reload,
            enable_debug_toolbar=enable_debug_toolbar
        )
        
        # 設定の検証
        self._validate_config(config)
        
        # ログ出力
        self._log_config_summary(config)
        
        return config
    
    def _parse_bool(self, value: str) -> bool:
        """文字列をブール値に変換"""
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def _validate_config(self, config: AppConfig) -> None:
        """設定値の検証"""
        errors = []
        
        # 必須ディレクトリの存在確認
        if not config.data_dir.exists():
            self._logger.warning(f"データディレクトリが存在しません: {config.data_dir}")
        
        # ログディレクトリの作成
        log_dir = config.log_file.parent
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            self._logger.info(f"ログディレクトリを作成しました: {log_dir}")
        
        # アルゴリズム設定の検証
        if config.da_algorithm_temperature <= 0:
            errors.append("DA_ALGORITHM_TEMPERATUREは正の値である必要があります")
        
        if not (0 < config.da_algorithm_cooling_rate < 1):
            errors.append("DA_ALGORITHM_COOLING_RATEは0と1の間の値である必要があります")
        
        if config.da_algorithm_max_iterations <= 0:
            errors.append("DA_ALGORITHM_MAX_ITERATIONSは正の値である必要があります")
        
        # 制約設定の検証
        if config.default_min_rest_hours < 0:
            errors.append("DEFAULT_MIN_REST_HOURSは0以上の値である必要があります")
        
        if config.default_max_consecutive_days < 1:
            errors.append("DEFAULT_MAX_CONSECUTIVE_DAYSは1以上の値である必要があります")
        
        if config.default_max_weekly_hours < 1:
            errors.append("DEFAULT_MAX_WEEKLY_HOURSは1以上の値である必要があります")
        
        if config.default_max_night_shifts_per_week < 0:
            errors.append("DEFAULT_MAX_NIGHT_SHIFTS_PER_WEEKは0以上の値である必要があります")
        
        # エラーがあれば例外を発生
        if errors:
            error_msg = "設定エラー:\n" + "\n".join(f"- {error}" for error in errors)
            raise ValueError(error_msg)
    
    def _log_config_summary(self, config: AppConfig) -> None:
        """設定の要約をログに出力"""
        self._logger.info(f"アプリケーション設定を読み込みました:")
        self._logger.info(f"  アプリ名: {config.app_name} v{config.app_version}")
        self._logger.info(f"  デバッグモード: {config.debug}")
        self._logger.info(f"  ログレベル: {config.log_level}")
        self._logger.info(f"  データベース: {config.database_url}")
        self._logger.info(f"  Streamlit: {config.streamlit_server_address}:{config.streamlit_server_port}")
        self._logger.info(f"  データディレクトリ: {config.data_dir}")
        self._logger.info(f"  ログファイル: {config.log_file}")


# グローバル設定インスタンス
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """設定オブジェクトを取得"""
    return config_manager.load_config()


def reload_config() -> AppConfig:
    """設定を再読み込み"""
    config_manager._config = None
    return config_manager.load_config() 