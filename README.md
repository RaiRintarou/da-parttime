# シフトマッチングシステム

このプロジェクトは、オペレータのシフト割り当てを最適化するためのStreamlitアプリケーションです。

## 機能

- **CSVアップロード**: デスク別の要員数をCSVファイルで指定
- **オペレータ設定**: 各オペレータの勤務時間、所属デスク、対応可能デスクを設定
- **マッチングアルゴリズム**: 
  - **Multi-slot DAアルゴリズム（推奨）**: 日次スロットベースの柔軟な割り当て
  - DA（Deferred Acceptance）アルゴリズム: 時間単位の安定マッチング
  - 貪欲アルゴリズム: シンプルな逐次割り当て
- **ポイント計算**: 他デスクでの勤務に対するポイント補填
- **CSV出力**: 生成されたシフト表とポイント集計をCSVでダウンロード

## ファイル構成

```
da_parttime/
├── 📁 アプリケーション
│   ├── main.py                              # メインエントリーポイント
│   └── src/
│       ├── __init__.py                      # メインパッケージ
│       ├── 📁 app/
│       │   ├── __init__.py                  # アプリケーションパッケージ
│       │   └── streamlit_shift_matching_demo.py  # メインのStreamlitアプリ
│       ├── 📁 algorithms/
│       │   ├── __init__.py                  # アルゴリズムパッケージ
│       │   ├── da_algorithm.py              # 従来の時間単位DAアルゴリズム
│       │   └── multi_slot_da_algorithm.py   # Multi-slot DAアルゴリズム
│       ├── 📁 models/
│       │   ├── __init__.py                  # モデルパッケージ
│       │   └── multi_slot_models.py         # スロットベースのデータ構造
│       └── 📁 tests/
│           ├── __init__.py                  # テストパッケージ
│           └── test_multi_slot_models.py    # Multi-slotモデルのユニットテスト
│
├── 📁 設定・ドキュメント
│   ├── pyproject.toml                       # Poetry依存関係管理
│   ├── poetry.lock                          # 依存関係ロックファイル
│   ├── Makefile                            # ビルド・デプロイ設定
│   ├── README.md                           # プロジェクト説明書
│   └── docs/
│       └── shift_optimiser_roadmap.md      # 開発ロードマップ
│
├── 📁 サンプルデータ
│   └── data/
│       └── samples/
│           ├── シフト表.csv                 # サンプルシフトデータ
│           ├── シフト表.numbers             # Numbers形式サンプル
│           └── 名称未設定.csv               # サンプルCSV
│
└── 📁 開発環境
    ├── .venv/                              # Poetry仮想環境
    ├── .git/                               # Gitリポジトリ
    ├── .vscode/                            # VS Code設定
    └── __pycache__/                        # Pythonキャッシュ
```

### 主要ファイルの説明

#### アプリケーション層
- **`streamlit_shift_matching_demo.py`**: メインのWebアプリケーション
  - CSVアップロード機能
  - オペレータ設定UI
  - アルゴリズム選択
  - 結果表示・ダウンロード

#### アルゴリズム層
- **`da_algorithm.py`**: 従来の時間単位DAアルゴリズム
  - 9-17時の時間単位でのマッチング
  - 安定マッチング保証
  - 後方互換性維持

- **`multi_slot_models.py`**: Multi-slot日次モデルの基盤
  - `TimeSlot`: 時間スロット定義（朝・午後・夜・夜勤）
  - `OperatorAvailability`: オペレータの利用可能性
  - `DeskRequirement`: デスクの要件定義
  - `Assignment`: 割り当て情報
  - `MultiSlotScheduler`: スケジューラー

- **`multi_slot_da_algorithm.py`**: Multi-slot DAアルゴリズム
  - 日次スロットベースのマッチング
  - 制約検証機能
  - 従来データとの変換機能

#### テスト層
- **`test_multi_slot_models.py`**: 包括的なユニットテスト
  - 各クラスの動作検証
  - アルゴリズムの正確性確認
  - エッジケースのテスト

## Multi-slot日次モデルについて

### 従来モデルとの違い

| 項目 | 従来モデル | Multi-slotモデル |
|------|------------|------------------|
| 時間単位 | 1時間単位 | スロット単位（朝3h、午後5h等） |
| 柔軟性 | 固定時間 | カスタマイズ可能スロット |
| 制約 | 時間制約のみ | 労働時間・休息時間制約 |
| 拡張性 | 限定的 | 高（新しいスロットタイプ追加可能） |

### スロット定義

- **朝シフト (morning)**: 9:00-12:00 (3時間)
- **午後シフト (afternoon)**: 12:00-17:00 (5時間)
- **夜シフト (evening)**: 17:00-21:00 (4時間)
- **夜勤シフト (night)**: 21:00-9:00 (12時間)

## DAアルゴリズムについて

DA（Deferred Acceptance）アルゴリズムは、安定マッチングを保証するアルゴリズムです。

### 特徴

1. **安定性**: どのオペレータも、現在の割り当てよりも好ましいデスクに移動できない
2. **公平性**: 所属デスクのオペレータを優先的に割り当て
3. **効率性**: 各時間帯で最適な割り当てを実現

### アルゴリズムの流れ

1. 各時間帯で独立してマッチングを実行
2. オペレータは自分の優先順位に従ってデスクに提案
3. デスクは受け入れ可能なオペレータを優先順位に従って選択
4. 競合が発生した場合、優先度の低いオペレータを除外
5. 全てのオペレータが割り当てられるまで繰り返し

## 使用方法

### 1. 環境構築
```bash
# Poetryで依存関係をインストール
poetry install

# 開発用依存関係も含めてインストール
poetry install --with dev
```

### 2. アプリケーション起動
```bash
# 方法1: メインエントリーポイントを使用（推奨）
poetry run python main.py

# 方法2: 直接Streamlitを起動
poetry run streamlit run src/app/streamlit_shift_matching_demo.py

# 方法3: Makefileを使用
make run
```

### 3. テスト実行
```bash
# 全テストを実行
poetry run pytest src/tests/ -v

# 特定のテストファイルを実行
poetry run pytest src/tests/test_multi_slot_models.py -v

# Makefileを使用
make test

# カバレッジ付きでテスト実行
poetry run pytest --cov=src/models --cov=src/algorithms
```

### 4. アプリケーション使用手順

1. デスク要員数のCSVファイルをアップロード（またはテンプレートを使用）

2. オペレータ情報を設定:
   - 名前
   - 勤務時間（開始・終了）
   - 所属デスク
   - 対応可能デスク

3. マッチングアルゴリズムを選択:
   - **Multi-slot DAアルゴリズム（推奨）**: 最新の日次スロットベース
   - **DAアルゴリズム**: 従来の時間単位
   - **貪欲アルゴリズム**: シンプルな逐次割り当て

4. 「Match & Generate Schedule」ボタンをクリック

5. 生成されたシフト表とポイント集計を確認・ダウンロード

## 開発環境

### 必要なライブラリ
- **streamlit**: Webアプリケーションフレームワーク
- **pandas**: データ処理
- **pytest**: テストフレームワーク（開発用）

### インストール
```bash
# Poetryを使用したインストール（推奨）
poetry install

# または従来のpipを使用
pip install streamlit pandas pytest
```

## 開発ロードマップ

詳細な開発計画は `shift_optimiser_roadmap.md` を参照してください。

### 現在の実装状況
- ✅ **Phase 0.1**: Multi-slot日次モデルの実装
- ✅ **Phase 0.1**: ユニットテストの実装
- 🔄 **Phase 0.2**: CI/CDパイプラインの構築
- ⏳ **Phase 1**: MVP for Single-Site Pilot

## ライセンス

MIT License 