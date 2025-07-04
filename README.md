# Laplace Stock Analysis API

株式銘柄データの検索・分析を行う API サービス

## API 概要

API は安定性と後方互換性を確保するためにバージョニングされています。

- 最新安定版: `/v1/*` - こちらを使用してください
- レガシー互換性: 直接ルート (`/markets/*`など) - 非推奨、将来的に廃止予定

## API 仕様 (v1)

### 銘柄検索

**エンドポイント**: `GET /v1/markets/search`

**クエリパラメータ**:

- `query` (必須): 検索キーワード（例: "トヨタ"、"Apple"）

**レスポンス例**:

```json
{
  "results": [
    {
      "symbol": "7203.T",
      "name": "トヨタ自動車",
      "asset_type": "STOCK",
      "market": "Japan",
      "price": "¥2,120.00",
      "change_percent": "+1.2%",
      "score": 100
    }
  ],
  "total": 1
}
```

### モンテカルロシミュレーション

**エンドポイント**: `POST /v1/simulation`

**リクエストボディ**:

```json
{
  "symbol": "AAPL",
  "initial_investment": 1000000,
  "years": 30,
  "simulations": 1000
}
```

**レスポンス例**:

```json
{
  "symbol": "AAPL",
  "scenarios": {
    "median": [1000000, 1050000, ...],
    "upper_95": [1000000, 1080000, ...],
    "lower_5": [1000000, 920000, ...]
  }
}
```

## クライアント実装例 (Next.js)

```typescript
// lib/api/market.ts

import { API_BASE_URL, APP_VERSION } from "@/config";

// または環境変数から直接取得
// const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
// const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION || "1.0.0";

export interface SearchResult {
  symbol: string;
  name: string;
  asset_type: string;
  market: string;
  price?: string;
  change_percent?: string;
  score: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
}

/**
 * 株式銘柄を検索する
 */
export const searchStocks = async (query: string): Promise<SearchResponse> => {
  if (!query || query.trim().length === 0) {
    throw new Error("検索キーワードを入力してください");
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/v1/markets/search?query=${encodeURIComponent(query)}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "X-App-Version": APP_VERSION,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail?.message || "検索中にエラーが発生しました"
      );
    }

    return await response.json();
  } catch (error) {
    console.error("銘柄検索中にエラーが発生しました:", error);
    throw error;
  }
};
```

## ローカル環境でのセットアップ

### 前提条件

- Python 3.12
- pip（Python パッケージマネージャー）
- Docker（コンテナでの実行やローカルの DynamoDB を使用する場合）

### 1. リポジトリのクローン

```bash
git clone [リポジトリURL]
cd laplace-api
```

### 2. 仮想環境の作成と有効化

```bash
# 仮想環境の作成
python3.12 -m venv venv

# 仮想環境の有効化
# macOSの場合
source venv/bin/activate
# Windowsの場合
.\venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
# pipを最新版にアップグレード
pip install --upgrade pip

# 依存パッケージのインストール
pip install -r requirements.txt
```

### 4. 環境変数の設定

`.env.local`ファイルを作成し、以下の内容を設定します：

```env
# 環境設定
ENVIRONMENT=local

# AWS設定
AWS_ACCESS_KEY_ID=あなたのアクセスキー
AWS_SECRET_ACCESS_KEY=あなたのシークレットキー
AWS_DEFAULT_REGION=ap-northeast-1

# DynamoDB設定
USE_LOCAL_DYNAMODB=true  # ローカルのDynamoDBを使用する場合
```

### 5. ローカル DynamoDB の起動（オプション）

ローカルの DynamoDB を使用する場合：

```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

### 6. アプリケーションの起動

```bash
# 開発モードで起動
source venv/bin/activate

python -m uvicorn app.main:app --reload
```

アプリケーションは http://localhost:8000 で起動します。

### 7. API ドキュメントの確認

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 開発環境（ホットリロード対応）

コードの変更を即座に反映させながら開発したい場合は、docker-composeを使用してください。

### 1. リポジトリのクローン

```bash
git clone [リポジトリURL]
cd laplace-api
```

### 2. ホットリロード環境の起動

```bash
# ホットリロード対応のDockerコンテナを起動
docker-compose up --build
```

### 3. アプリケーションへのアクセス

アプリケーションは http://localhost:8000 で起動します。

### 4. 開発のポイント

- **ホットリロード**: `app/`ディレクトリ内のPythonファイルを変更すると、自動的にサーバーが再起動されます
- **即座に反映**: ファイル保存後、数秒で変更が反映されます
- **API ドキュメント**: http://localhost:8000/docs で確認できます

### 5. 開発環境の停止

```bash
# コンテナを停止
docker-compose down
```

## Dockerを使った起動方法

### 1. リポジトリのクローン

```bash
git clone [リポジトリURL]
cd laplace-api
```

### 2. 環境変数の設定

`.env`ファイルを作成し、必要な環境変数を設定します：

```env
# 環境設定
ENVIRONMENT=development

# AWS設定（必要に応じて）
AWS_ACCESS_KEY_ID=あなたのアクセスキー
AWS_SECRET_ACCESS_KEY=あなたのシークレットキー
AWS_DEFAULT_REGION=ap-northeast-1
```

### 3. Dockerイメージのビルド

```bash
# Dockerイメージをビルド
docker build -t laplace-api .
```

### 4. Dockerコンテナの起動

```bash
# コンテナを起動（ポート8000でアクセス可能）
docker run -p 8000:80 laplace-api

# バックグラウンドで起動する場合
docker run -d -p 8000:80 --name laplace-api-container laplace-api
```

### 5. アプリケーションへのアクセス

アプリケーションは http://localhost:8000 で起動します。

### 6. API ドキュメントの確認

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 7. コンテナの管理

```bash
# コンテナの停止
docker stop laplace-api-container

# コンテナの削除
docker rm laplace-api-container

# イメージの削除
docker rmi laplace-api

# ログの確認
docker logs laplace-api-container

# コンテナ内に入る（デバッグ用）
docker exec -it laplace-api-container /bin/bash
```

### Docker + ローカルDynamoDBの組み合わせ

ローカルDynamoDBと組み合わせて使用する場合：

```bash
# 1. ローカルDynamoDBを起動
docker run -d -p 8000:8000 --name dynamodb-local amazon/dynamodb-local

# 2. アプリケーションコンテナを起動（DynamoDBコンテナにリンク）
docker run -d -p 8001:80 \
  --link dynamodb-local:dynamodb \
  --env-file .env \
  -e USE_LOCAL_DYNAMODB=true \
  -e DYNAMODB_ENDPOINT_URL=http://dynamodb:8000 \
  --name laplace-api-container \
  laplace-api
```

この場合、アプリケーションは http://localhost:8001 でアクセスできます。

## トラブルシューティング

### 一般的な問題

1. モジュールが見つからないエラー

```bash
pip install -r requirements.txt
```

2. ポートが既に使用されている場合

```bash
python -m uvicorn app.main:app --reload --port 8001
```

3. DynamoDB 接続エラー

- ローカル DynamoDB が起動していることを確認
- `.env.local`の設定を確認

4. Docker関連の問題

```bash
# コンテナが起動しない場合
docker logs laplace-api-container

# ポートが使用されている場合
docker run -p 8001:80 --env-file .env laplace-api

# イメージのビルドエラー
docker build --no-cache -t laplace-api .

# コンテナの強制削除
docker rm -f laplace-api-container
```

### 開発時の注意点

- コードの変更は自動的にリロードされます（--reload オプション使用時）
- ログはコンソールに出力されます
- 環境変数の変更時はアプリケーションの再起動が必要です

## テスト

```bash
# テストの実行
pytest

# 特定のテストファイルの実行
pytest tests/test_特定のファイル.py
```

## デプロイ

本番環境へのデプロイ手順は別途ドキュメントを参照してください。
