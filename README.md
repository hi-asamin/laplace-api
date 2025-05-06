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

## インストールと実行

```bash
# 依存関係のインストール
pip install -r requirements.txt

# 開発サーバーの起動
uvicorn app.main:app --reload
```

API ドキュメントは http://localhost:8000/docs で確認できます。
