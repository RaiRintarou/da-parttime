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
- **制約設定UI**: 最小休息・最大連勤・最大週労働・夜勤回数・夜勤後休日などをGUIで調整
- **シフト期間設定**: 1日/5日連続/カスタム日数でシフト生成
- **ポイント計算**: 他デスク勤務に対するポイント補填
- **シフト表・ポイント集計CSV出力**: 期間統合・個別日ごとにダウンロード可
- **サンプル/テンプレートCSVのDL**: デスク・オペレーター両方に対応

## ファイル構成（2024/06/29時点）

```
da_parttime/
├── main.py
├── Makefile
├── pyproject.toml
├── poetry.lock
├── README.md
│
├── src/
│   ├── __init__.py
│   ├── app/
│   │   ├── __init__.py
│   │   └── streamlit_shift_matching_demo.py
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── da_algorithm.py
│   │   ├── multi_slot_da_algorithm.py
│   │   └── constrained_multi_slot_da_algorithm.py
│   └── models/
│       ├── __init__.py
│       ├── multi_slot_models.py
│       └── constraints.py
│
├── tests/
│   ├── __init__.py
│   ├── test_multi_slot_models.py
│   ├── test_constraints.py
│   ├── test_5day_shift.py
│   ├── test_operator_csv.py
│   ├── test_constraint_ui.py
│   ├── test_constrained_algorithm.py
│   └── test_multi_slot_debug.py
│
├── data/
│   ├── samples/
│   │   ├── シフト表.csv
│   │   ├── シフト表.numbers
│   │   ├── 名称未設定.csv
│   │   └── operators_default.csv
│   └── templates/
│       └── operators_template.csv
│
└── docs/
    └── shift_optimiser_roadmap.md
```

## 主要ファイル・ディレクトリの説明

### ルート直下
- **main.py**: アプリケーションのエントリーポイント
- **Makefile**: ビルド・実行・テスト・フォーマット等のコマンド集
- **pyproject.toml / poetry.lock**: Poetryによる依存管理
- **README.md**: 本ファイル

### src/
- **app/**
  - `streamlit_shift_matching_demo.py`: Web UI本体。デスク・オペレーターCSV入出力、制約設定、アルゴリズム選択、シフト生成・DLまで一括管理。
- **algorithms/**
  - `da_algorithm.py`: 時間単位DAアルゴリズム（後方互換）
  - `multi_slot_da_algorithm.py`: スロット単位DAアルゴリズム
  - `constrained_multi_slot_da_algorithm.py`: 制約付きスロットDAアルゴリズム
- **models/**
  - `multi_slot_models.py`: スロット・オペレーター・割当等のデータ構造
  - `constraints.py`: 制約DSL・バリデーション・各種制約クラス

### tests/
- `test_multi_slot_models.py`: モデル・アルゴリズムのユニットテスト
- `test_constraints.py`: 制約ロジックのテスト
- `test_5day_shift.py`: 5日分シフト生成の動作確認
- `test_operator_csv.py`: オペレーターCSV読み込みの動作確認
- `test_constraint_ui.py`: 制約UIテスト
- `test_constrained_algorithm.py`: 制約付きアルゴリズムテスト
- `test_multi_slot_debug.py`: デバッグ用テスト

### data/
- **samples/**
  - `シフト表.csv`: デスク要員数サンプル
  - `operators_default.csv`: オペレーターサンプル
- **templates/**
  - `operators_template.csv`: オペレーターCSVテンプレート

### docs/
- `shift_optimiser_roadmap.md`: 開発ロードマップ

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
make test
# または
poetry run pytest tests/ -v
```

### 4. Webアプリの操作手順
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

---

ご質問・不具合はGitHub Issueまたは開発者までご連絡ください。 