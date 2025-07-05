"""
開発用Dockerfile
- ベース: python:3.11-slim
- 必要パッケージ: git, curl, bash-completion, less, build-essential
- Poetry: pipでインストール、仮想環境無効化
- 依存関係: poetry install
- CMD: FastAPI (uvicorn) 起動
"""
FROM python:3.11-slim

# 必要パッケージのインストール
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        bash-completion \
        less \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Poetryインストール（pip経由）
RUN pip install --no-cache-dir poetry

# Poetry仮想環境を無効化
ENV POETRY_VIRTUALENVS_CREATE=false

# 作業ディレクトリ作成
WORKDIR /workspace

# Poetryファイルコピー
COPY pyproject.toml poetry.lock ./

# 依存関係インストール
RUN poetry install --no-root

# アプリケーションコードコピー
COPY . .

# .envファイルの自動ロードはdocker-compose側で対応

# FastAPI起動
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 