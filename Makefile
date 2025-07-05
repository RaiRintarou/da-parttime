# シフトマッチングシステム - Makefile

.PHONY: help install test run clean lint format setup-env docker-build docker-run

# デフォルトターゲット
help:
	@echo "利用可能なコマンド:"
	@echo "  install      - 依存関係をインストール"
	@echo "  test         - テストを実行"
	@echo "  test-cov     - カバレッジ付きテストを実行"
	@echo "  lint         - コード品質チェック"
	@echo "  format       - コードフォーマット"
	@echo "  clean        - 一時ファイルを削除"
	@echo "  setup-env    - 環境設定ファイルを作成"
	@echo "  docker-build - Dockerイメージをビルド"
	@echo "  docker-run   - Dockerコンテナを実行"
	@echo "  run          - Streamlitアプリを実行"
	@echo "  run-dev      - 開発モードでアプリを実行"

# 依存関係のインストール
install:
	@echo "📦 依存関係をインストール中..."
	poetry install --with dev

# テストの実行
test:
	@echo "🧪 テストを実行中..."
	poetry run pytest

# カバレッジ付きテスト実行
test-cov:
	poetry run pytest --cov=src --cov-report=term-missing --cov-report=html

# アプリケーションの起動
run:
	@echo "🚀 アプリケーションを起動中..."
	@echo "📝 ファイルアップロードの問題が発生した場合は、手動入力オプションを使用してください"
	poetry run python main.py

# キャッシュファイルの削除
clean:
	@echo "🧹 キャッシュファイルを削除中..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name "bandit-report.json" -delete
	find . -type f -name "safety-report.json" -delete
	find . -type f -name "*.log" -delete

# コードの品質チェック
lint:
	@echo "🔍 コードの品質チェック中..."
	poetry run flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
	poetry run flake8 src/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	poetry run bandit -r src/ -f json -o bandit-report.json || true
	poetry run safety check --json --output safety-report.json || true

# コードのフォーマット
format:
	@echo "🎨 コードをフォーマット中..."
	poetry run black src/ tests/
	poetry run isort src/ tests/

# 環境設定ファイル作成
setup-env:
	@if [ ! -f .env ]; then \
		echo "環境設定ファイルを作成しています..."; \
		cp env.example .env; \
		echo ".envファイルを作成しました。必要に応じて値を編集してください。"; \
	else \
		echo ".envファイルは既に存在します。"; \
	fi

# Dockerイメージビルド
docker-build:
	docker build -t shift-optimiser-poc .

# Dockerコンテナ実行
docker-run:
	docker-compose up --build

# Streamlitアプリ実行
run:
	poetry run streamlit run src/app/streamlit_shift_matching_demo.py

# 開発モードでアプリ実行
run-dev:
	DEBUG=true poetry run streamlit run src/app/streamlit_shift_matching_demo.py

# 依存関係更新
update:
	poetry update

# セキュリティチェック
security:
	poetry run bandit -r src/ -f json -o bandit-report.json
	poetry run safety check --json --output safety-report.json

# 開発環境セットアップ（初回用）
dev-setup: setup-env install
	@echo "開発環境のセットアップが完了しました。"
	@echo "次のコマンドでアプリを起動できます:"
	@echo "  make run"
	@echo "  make run-dev  # デバッグモード"

# 本番環境用セットアップ
prod-setup: install
	@echo "本番環境用のセットアップが完了しました。"
	@echo "環境変数を適切に設定してからアプリを起動してください。"

# ヘルスチェック
health-check:
	@echo "システムヘルスチェックを実行中..."
	@python -c "import sys; print(f'Python version: {sys.version}')"
	@poetry --version
	@poetry run python -c "import streamlit; print(f'Streamlit version: {streamlit.__version__}')"
	@echo "ヘルスチェック完了"