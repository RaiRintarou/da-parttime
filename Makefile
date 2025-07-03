# シフトマッチングシステム - Makefile

.PHONY: help install test run clean lint format

# デフォルトターゲット
help:
	@echo "利用可能なコマンド:"
	@echo "  install  - 依存関係をインストール"
	@echo "  test     - テストを実行"
	@echo "  run      - アプリケーションを起動"
	@echo "  clean    - キャッシュファイルを削除"
	@echo "  lint     - コードの品質チェック"
	@echo "  format   - コードをフォーマット"

# 依存関係のインストール
install:
	@echo "📦 依存関係をインストール中..."
	poetry install --with dev

# テストの実行
test:
	@echo "🧪 テストを実行中..."
	poetry run pytest

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

# コードの品質チェック
lint:
	@echo "🔍 コードの品質チェック中..."
	poetry run flake8 src/ --max-line-length=88 --ignore=E203,W503

# コードのフォーマット
format:
	@echo "🎨 コードをフォーマット中..."
	poetry run black src/ --line-length=88
	poetry run isort src/ --profile=black

performance-test:
	poetry run python performance_test.py