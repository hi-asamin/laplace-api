from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks, Request
from typing import List, Optional

from app.api.dependencies import get_market_service
from app.schemas.market import StockSearchResult, SearchErrorResponse
from app.schemas.search import SearchResponse
from app.schemas.details import MarketDetails
from app.schemas.chart import ChartData
from app.schemas.fundamental import FundamentalData
from app.schemas.related import RelatedMarketsResponse

router = APIRouter(
    prefix="/markets",
    tags=["markets"],
    responses={
        404: {"description": "Not found"},
        400: {"model": SearchErrorResponse, "description": "無効なクエリ"},
        503: {"model": SearchErrorResponse, "description": "サービス利用不可"},
        429: {"model": SearchErrorResponse, "description": "レート制限超過"}
    },
)

@router.get("/search", response_model=SearchResponse)
def search_stocks(
    query: str = Query(..., description="検索キーワード"),
    market_service=Depends(get_market_service)
):
    """
    銘柄の検索を行うエンドポイント
    
    - **query**: 検索文字列（例: "トヨタ"、"Amazon"）
    """
    # クエリの検証
    if not query or len(query.strip()) < 1:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_QUERY", "message": "検索文字列は1文字以上入力してください"}
        )
    
    # 検索実行（固定で10件）
    try:
        results = market_service.fuzzy_search(query=query, limit=10)
        
        # 価格情報の追加
        for result in results:
            try:
                symbol = result["symbol"]
                
                # 投資信託かどうかを判定
                if market_service.is_mutual_fund_symbol(symbol):
                    # 投資信託の場合は専用の価格データを使用
                    price_info = market_service.get_mutual_fund_price_data(symbol)
                    currency_symbol = "¥"  # 日本の投資信託は常に円建て
                else:
                    # 株式の場合は従来通りの処理
                    price_info = market_service.get_stock_price(symbol)
                    # 市場に応じて通貨記号を決定
                    is_japan_stock = symbol.endswith(".T")
                    currency_symbol = "¥" if is_japan_stock else "$"
                
                # 数値を適切にフォーマット
                price_value = float(price_info["price"])
                change_percent_value = float(price_info["change_percent"])
                
                result["price"] = f"{currency_symbol}{price_value:,.0f}" if currency_symbol == "¥" else f"{currency_symbol}{price_value:.2f}"
                result["change_percent"] = f"{'+' if change_percent_value > 0 else ''}{change_percent_value:.2f}%"
            except Exception as e:
                print(f"Error getting price for {result['symbol']}: {e}")
                # 価格取得に失敗した場合はデフォルト値を設定
                symbol = result["symbol"]
                if market_service.is_mutual_fund_symbol(symbol):
                    currency_symbol = "¥"
                else:
                    is_japan_stock = symbol.endswith(".T")
                    currency_symbol = "¥" if is_japan_stock else "$"
                result["price"] = f"{currency_symbol}0"
                result["change_percent"] = "0.00%"
        
        return {
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        # エラーハンドリング
        error_message = str(e).lower()
        if "yfinance" in error_message or "yahoo" in error_message or "network" in error_message or "connection" in error_message:
            # 外部サービス接続エラー
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error_code": "SERVICE_UNAVAILABLE",
                    "message": "外部データソースに接続できません"
                }
            )
        else:
            # その他のエラー
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "INTERNAL_ERROR",
                    "message": f"内部エラーが発生しました: {str(e)}"
                }
            )

@router.get("/{symbol}", response_model=MarketDetails)
def get_market_details(
    symbol: str,
    market_service=Depends(get_market_service)
):
    """
    銘柄詳細情報の取得エンドポイント
    
    - **symbol**: 銘柄シンボル（例: AAPL, 9432.T）
    """
    try:
        details = market_service.get_market_details(symbol)
        return details
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "NOT_FOUND",
                "message": f"銘柄が見つかりません: {symbol}"
            }
        )
    except Exception as e:
        # エラーハンドリング
        error_message = str(e).lower()
        if "yfinance" in error_message or "yahoo" in error_message or "network" in error_message or "connection" in error_message:
            # 外部サービス接続エラー
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error_code": "SERVICE_UNAVAILABLE",
                    "message": "外部データソースに接続できません"
                }
            )
        else:
            # その他のエラー
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "INTERNAL_ERROR",
                    "message": f"内部エラーが発生しました: {str(e)}"
                }
            )
