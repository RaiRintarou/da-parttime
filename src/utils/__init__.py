"""
ユーティリティパッケージ

このパッケージは、アプリケーション全体で使用される共通機能を提供します。
設定管理、ログ機能、データ変換、CSV操作などのユーティリティが含まれています。
"""

# 設定管理とログ機能
from .config import get_config, reload_config, AppConfig
from .logger import setup_logging, get_logger, log_extra_fields

from .schedule_converter import (
    convert_to_operator_schedule,
    convert_multi_slot_to_operator_schedule,
    convert_multi_day_to_operator_schedule,
    convert_assignments_to_operator_schedule,
    convert_multi_day_assignments_to_operator_schedule
)

from .data_converter import convert_ops_data_to_operator_availability
from .point_calculator import calc_points
from .csv_utils import (
    create_desk_requirements_template,
    create_operators_template,
    validate_csv_upload,
    validate_operators_csv
)
from .constants import (
    HOURS,
    COLS,
    DEFAULT_DESKS,
    ALGORITHM_CHOICES,
    SHIFT_PERIOD_CHOICES,
    OPERATOR_SCHEDULE_METHODS,
    DEFAULT_CONSTRAINTS
)
from .ui_components import (
    create_manual_desk_input_form,
    create_manual_operator_input_form,
    display_operator_preview,
    display_assignment_results,
    display_constraint_details,
    create_download_button,
    generate_filename,
    display_shift_info,
    display_individual_day_downloads
)
from .algorithm_executor import AlgorithmExecutor
from .constraint_manager import ConstraintManager

__all__ = [
    # 設定管理とログ機能
    'get_config',
    'reload_config',
    'AppConfig',
    'setup_logging',
    'get_logger',
    'log_extra_fields',
    
    # スケジュール変換機能
    'convert_to_operator_schedule',
    'convert_multi_slot_to_operator_schedule', 
    'convert_multi_day_to_operator_schedule',
    'convert_assignments_to_operator_schedule',
    'convert_multi_day_assignments_to_operator_schedule',
    
    # データ変換機能
    'convert_ops_data_to_operator_availability',
    
    # ポイント計算機能
    'calc_points',
    
    # CSV処理機能
    'create_desk_requirements_template',
    'create_operators_template',
    'validate_csv_upload',
    'validate_operators_csv',
    
    # 定数
    'HOURS',
    'COLS',
    'DEFAULT_DESKS',
    'ALGORITHM_CHOICES',
    'SHIFT_PERIOD_CHOICES',
    'OPERATOR_SCHEDULE_METHODS',
    'DEFAULT_CONSTRAINTS',
    
    # UIコンポーネント
    'create_manual_desk_input_form',
    'create_manual_operator_input_form',
    'display_operator_preview',
    'display_assignment_results',
    'display_constraint_details',
    'create_download_button',
    'generate_filename',
    'display_shift_info',
    'display_individual_day_downloads',
    
    # アルゴリズム実行
    'AlgorithmExecutor',
    
    # 制約管理
    'ConstraintManager'
] 