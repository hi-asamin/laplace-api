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
- Docker（ローカルの DynamoDB を使用する場合）

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
