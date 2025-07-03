# シフトマッチングシステム

このプロジェクトは、オペレーターのシフト割り当てを最適化するためのStreamlitアプリケーションです。

## 主な機能

- **デスク要員数CSVアップロード**: デスクごとの時間帯要員数をCSVで指定
- **オペレーター設定**: 手動入力またはCSVアップロードで勤務時間・所属・対応デスクを一括設定
- **マッチングアルゴリズム選択**:
  - 制約付きMulti-slot DAアルゴリズム（推奨）
  - Multi-slot DAアルゴリズム
  - DA（Deferred Acceptance）アルゴリズム
  - 貪欲アルゴリズム
- **制約設定UI**: 最小休息・最大連勤・最大週労働・夜勤回数・夜勤後休日・連続スロット後の必須休憩などをGUIで調整
- **自動休憩割り当て**: 5スロット連続勤務後のオペレータを「休憩」デスクに自動アサイン
- **高性能シフト生成**: キャッシュ機能と最適化により高速なシフト生成（100オペレータ・10デスクで0.03秒）
- **シフト期間設定**: 1日/5日連続/カスタム日数でシフト生成
- **ポイント計算**: 他デスク勤務に対するポイント補填
- **シフト表・ポイント集計CSV出力**: 期間統合・個別日ごとにダウンロード可
- **サンプル/テンプレートCSVのDL**: デスク・オペレーター両方に対応

## ファイル構成（2024/06/XX時点・現状）

```
da_parttime/
  ├── data/
  │   ├── operators/
  │   │   └── operators_default.csv
  │   └── shifts/
  │       ├── シフト表.csv
  │       └── シフト表.numbers
  ├── demo_consecutive_break.py
  ├── docs/
  │   └── shift_optimiser_roadmap.md
  ├── main.py
  ├── Makefile
  ├── performance_test.py
  ├── poetry.lock
  ├── pyproject.toml
  ├── README.md
  ├── src/
  │   ├── __init__.py
  │   ├── algorithms/
  │   │   ├── __init__.py
  │   │   ├── constrained_multi_slot_da_algorithm.py
  │   │   ├── da_algorithm.py
  │   │   └── multi_slot_da_algorithm.py
  │   ├── app/
  │   │   ├── __init__.py
  │   │   └── streamlit_shift_matching_demo.py
  │   ├── models/
  │   │   ├── __init__.py
  │   │   ├── constraints.py
  │   │   └── multi_slot_models.py
  │   └── utils/
  │       ├── __init__.py
  │       ├── algorithm_executor.py
  │       ├── constants.py
  │       ├── constraint_manager.py
  │       ├── csv_utils.py
  │       ├── data_converter.py
  │       ├── point_calculator.py
  │       ├── schedule_converter.py
  │       └── ui_components.py
  ├── test_break_display.py
  ├── tests/
  │   ├── __init__.py
  │   └── test_integrated.py
```

## 主要ファイル・ディレクトリの説明

### ルート直下
- **main.py**: アプリケーションのエントリーポイント。
- **Makefile**: ビルド・実行・テスト・フォーマット等のコマンド集。
- **pyproject.toml / poetry.lock**: Poetryによる依存管理ファイル。
- **README.md**: 本ファイル。
- **performance_test.py**: シフト生成パフォーマンスの測定・分析用スクリプト。
- **test_break_display.py**: 休憩表示に関するテストスクリプト。

### data/
- **operators/operators_default.csv**: オペレーターサンプルデータ。
- **shifts/シフト表.csv, シフト表.numbers**: デスク要員数サンプル。

### docs/
- **shift_optimiser_roadmap.md**: 開発ロードマップ。

### src/
- **algorithms/**
  - `da_algorithm.py`: 時間単位DAアルゴリズム（後方互換）。
  - `multi_slot_da_algorithm.py`: スロット単位DAアルゴリズム。
  - `constrained_multi_slot_da_algorithm.py`: 制約付きスロットDAアルゴリズム。
- **app/**
  - `streamlit_shift_matching_demo.py`: Web UI本体。デスク・オペレーターCSV入出力、制約設定、アルゴリズム選択、シフト生成・DLまで一括管理。
- **models/**
  - `multi_slot_models.py`: スロット・オペレーター・割当等のデータ構造。
  - `constraints.py`: 制約DSL・バリデーション・各種制約クラス。
- **utils/**
  - `algorithm_executor.py`: アルゴリズム実行補助。
  - `constants.py`: 定数定義。
  - `constraint_manager.py`: 制約管理ロジック。
  - `csv_utils.py`: CSV入出力ユーティリティ。
  - `data_converter.py`: データ変換ユーティリティ。
  - `point_calculator.py`: ポイント計算ロジック。
  - `schedule_converter.py`: スケジュールデータ変換。
  - `ui_components.py`: UI部品。

### tests/
- `test_integrated.py`: 統合テスト。

## 使い方

### 1. 環境構築
```bash
poetry install --with dev
```

### 2. アプリケーション起動
```bash
make run
# または
poetry run python main.py
```

### 3. テスト実行
```bash
poetry run pytest
```

### 4. パフォーマンステスト実行
```bash
make performance-test
# または
poetry run python performance_test.py
```

### 5. Webアプリの操作手順
1. **デスク要員数CSV**をアップロード（テンプレDL可）
2. **オペレーター情報**を手動入力 or CSVアップロード（テンプレDL可）
3. **シフト期間**（1日/5日/カスタム）・**開始日**を選択
4. **制約**（必要に応じて）を設定
5. **アルゴリズム**を選択
6. **「Match & Generate Schedule」ボタン**でシフト生成
7. **シフト表・ポイント集計CSV**をDL（5日分の場合は個別日DLも可）

## サンプルCSV

### デスク要員数テンプレート
```
desk,h09,h10,h11,h12,h13,h14,h15,h16,h17
Desk A,1,1,1,0,0,0,0,0,0
Desk B,1,1,1,0,0,0,0,0,0
```

### オペレーターCSVテンプレート
```
name,start,end,home,desks
Op1,9,12,Desk A,"Desk A,Desk B"
Op2,9,12,Desk B,"Desk A,Desk B"
```

## 必要なライブラリ
- Python 3.11
- streamlit
- pandas
- pytest（開発用）

## よくある質問

- **Q. オペレーターCSVの「desks」列はどう書く？**
  - カンマ区切りで複数デスク指定可。例: `"Desk A,Desk B"`
- **Q. 5日分シフトを出したい場合は？**
  - サイドバー「シフト期間設定」で「5日連続」または「カスタム」を選択
- **Q. 制約はどこで設定？**
  - 「制約付きMulti-slot DAアルゴリズム」選択時、サイドバー下部で各種制約をGUI設定
- **Q. 休憩時間はどうやって設定する？**
  - 制約設定で「連続スロット後の必須休憩制約」を有効にすると、指定したスロット数以上連続で働いたオペレータが自動的に「休憩」デスクに割り当てられます
- **Q. 休憩デスクの名前は変更できる？**
  - 制約設定の「休憩デスク名」で任意の名前を設定可能（デフォルト: 「休憩」）
- **Q. シフト生成に時間がかかる場合は？**
  - パフォーマンス最適化済み（100オペレータ・10デスクで0.03秒）
  - 制約数を減らすか、オペレータ数を調整してください
  - 詳細なパフォーマンス測定は `python performance_test.py` で実行可能

---

ご質問・不具合はGitHub Issueまたは開発者までご連絡ください。 