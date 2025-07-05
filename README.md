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

# Shift Optimiser PoC

シフト最適化システムのプロトタイプ実装です。D-Waveの量子アニーリング技術を使用して、効率的なシフトスケジュールを生成します。

## 🚀 クイックスタート

### 前提条件

- Python 3.11以上
- Poetry
- Docker（オプション）

### 開発環境セットアップ

1. **リポジトリをクローン**
```bash
git clone <repository-url>
cd da_parttime
```

2. **環境設定ファイルを作成**
```bash
make setup-env
```

3. **依存関係をインストール**
```bash
make install
```

4. **アプリケーションを起動**
```bash
make run
```

### direnvを使用した環境管理（推奨）

1. **direnvをインストール**
```bash
# macOS
brew install direnv

# Ubuntu/Debian
sudo apt-get install direnv
```

2. **direnvをシェルに追加**
```bash
# ~/.bashrc または ~/.zshrc に追加
eval "$(direnv hook bash)"  # または zsh
```

3. **.envrcファイルを作成**
```bash
echo "dotenv" > .envrc
direnv allow
```

これで、プロジェクトディレクトリに入ると自動的に`.env`ファイルが読み込まれます。

## 📁 プロジェクト構造

```
da_parttime/
├── src/                    # ソースコード
│   ├── algorithms/         # アルゴリズム実装
│   ├── app/               # アプリケーション
│   ├── models/            # データモデル
│   └── utils/             # ユーティリティ
├── tests/                 # テストコード
├── data/                  # データファイル
├── docs/                  # ドキュメント
├── .github/               # GitHub Actions
├── env.example            # 環境変数テンプレート
├── .env                   # 環境変数（自動作成）
├── pyproject.toml         # Poetry設定
├── Dockerfile             # Docker設定
└── docker-compose.yml     # Docker Compose設定
```

## ⚙️ 設定

### 環境変数

`env.example`ファイルをコピーして`.env`ファイルを作成し、必要に応じて値を編集してください：

```bash
# アプリケーション設定
APP_NAME=Shift Optimiser PoC
APP_VERSION=0.1.0
DEBUG=true
LOG_LEVEL=INFO

# データベース設定
DATABASE_URL=sqlite:///./data/shift_optimiser.db

# セキュリティ設定
SECRET_KEY=your-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Streamlit設定
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# アルゴリズム設定
DA_ALGORITHM_MAX_ITERATIONS=1000
DA_ALGORITHM_TEMPERATURE=1.0
DA_ALGORITHM_COOLING_RATE=0.95

# 制約設定
DEFAULT_MIN_REST_HOURS=8
DEFAULT_MAX_CONSECUTIVE_DAYS=6
DEFAULT_MAX_WEEKLY_HOURS=40
DEFAULT_MAX_NIGHT_SHIFTS_PER_WEEK=3
```

## 🛠️ 開発コマンド

### 基本的なコマンド

```bash
make help              # 利用可能なコマンドを表示
make install           # 依存関係をインストール
make test              # テストを実行
make test-cov          # カバレッジ付きテストを実行
make lint              # コード品質チェック
make format            # コードフォーマット
make clean             # 一時ファイルを削除
```

### アプリケーション実行

```bash
make run               # Streamlitアプリを実行
make run-dev           # 開発モードでアプリを実行
```

### Docker関連

```bash
make docker-build      # Dockerイメージをビルド
make docker-run        # Dockerコンテナを実行
```

### 環境管理

```bash
make setup-env         # 環境設定ファイルを作成
make dev-setup         # 開発環境をセットアップ
make prod-setup        # 本番環境をセットアップ
make health-check      # システムヘルスチェック
```

## 🧪 テスト

### テスト実行

```bash
# 全テスト実行
make test

# カバレッジ付きテスト実行
make test-cov

# 特定のテストファイル実行
poetry run pytest tests/test_specific.py

# 特定のテスト関数実行
poetry run pytest tests/test_specific.py::test_function_name
```

### テストカバレッジ

テストカバレッジは60%以上を維持しています。カバレッジレポートは以下の場所で確認できます：

- コンソール出力: `make test-cov`
- HTMLレポート: `htmlcov/index.html`
- XMLレポート: `coverage.xml`

## 🔒 セキュリティ

### セキュリティチェック

```bash
make security          # セキュリティチェックを実行
```

以下のツールを使用してセキュリティチェックを実行します：

- **Bandit**: Pythonコードのセキュリティ脆弱性チェック
- **Safety**: 依存関係のセキュリティ脆弱性チェック

### セキュリティベストプラクティス

1. **環境変数の管理**
   - 機密情報は`.env`ファイルに保存
   - `.env`ファイルはGitにコミットしない
   - 本番環境では適切なシークレット管理を使用

2. **依存関係の管理**
   - 定期的に`safety check`を実行
   - 脆弱性のある依存関係は即座に更新

3. **コード品質**
   - `bandit`によるセキュリティチェックをCI/CDに組み込み
   - 定期的なコードレビューを実施

## 🚀 CI/CD

### GitHub Actions

プロジェクトには以下のCI/CDパイプラインが設定されています：

1. **テスト**: Python 3.11/3.12でのテスト実行
2. **リント**: コード品質チェック
3. **セキュリティ**: セキュリティ脆弱性チェック

### ローカルCI実行

```bash
# 全CIチェックを実行
make lint
make test-cov
make security
```

## 📊 ログ管理

### ログ設定

アプリケーションは以下のログ機能を提供します：

- **コンソール出力**: 開発時のデバッグ用
- **ファイル出力**: 構造化ログ（JSON形式）
- **ログローテーション**: 自動的なログファイル管理

### ログレベル

- `DEBUG`: 詳細なデバッグ情報
- `INFO`: 一般的な情報
- `WARNING`: 警告
- `ERROR`: エラー
- `CRITICAL`: 致命的なエラー

### ログファイル

ログファイルは`logs/app.log`に保存され、以下の設定で管理されます：

- 最大サイズ: 10MB
- バックアップ数: 5ファイル
- エンコーディング: UTF-8

## 🐳 Docker

### Docker実行

```bash
# イメージビルド
make docker-build

# コンテナ実行
make docker-run
```

### Docker Compose

`docker-compose.yml`を使用して、アプリケーションとその依存関係を簡単に起動できます：

```yaml
version: "3.9"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./:/workspace
```

## 📈 パフォーマンス

### ベンチマーク

```bash
# パフォーマンステスト実行
poetry run python performance_test.py
```

### 最適化のヒント

1. **アルゴリズムパラメータの調整**
   - `DA_ALGORITHM_MAX_ITERATIONS`
   - `DA_ALGORITHM_TEMPERATURE`
   - `DA_ALGORITHM_COOLING_RATE`

2. **制約の最適化**
   - 必要最小限の制約のみを設定
   - 制約の優先度を適切に設定

## 🤝 コントリビューション

### 開発フロー

1. 機能ブランチを作成
2. 変更を実装
3. テストを追加・実行
4. コードレビューを実施
5. マージリクエストを作成

### コーディング規約

- Python: PEP 8準拠
- 型ヒント: 必須
- ドキュメント: 日本語コメント
- テスト: 新機能には必ずテストを追加

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🆘 トラブルシューティング

### よくある問題

1. **依存関係のインストールエラー**
   ```bash
   poetry install --no-dev  # 開発依存関係をスキップ
   ```

2. **環境変数の読み込みエラー**
   ```bash
   make setup-env  # 環境設定ファイルを再作成
   ```

3. **Docker実行エラー**
   ```bash
   docker system prune  # Dockerキャッシュをクリア
   make docker-build    # イメージを再ビルド
   ```

### サポート

問題が解決しない場合は、以下を確認してください：

1. ログファイル: `logs/app.log`
2. システム要件: Python 3.11以上
3. 依存関係: `poetry show`
4. 環境変数: `.env`ファイルの設定 