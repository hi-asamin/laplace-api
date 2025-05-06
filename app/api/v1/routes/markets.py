from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
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
                price_info = market_service.get_stock_price(result["symbol"])
                result["price"] = price_info["price"]
                result["change_percent"] = price_info["change_percent"]
            except Exception:
                # 価格取得に失敗した場合はスキップ
                pass
        
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

# 管理者用エンドポイントを追加
@router.post("/admin/update-jpx", status_code=status.HTTP_200_OK)
def update_jpx_data(
    background_tasks: BackgroundTasks,
    market_service=Depends(get_market_service)
):
    """
    JPXデータを使用して銘柄マスタを更新するエンドポイント（管理者用）
    
    このエンドポイントは以下の処理を行います：
    1. JPXデータから日本株の日本語名称を読み込む
    2. 銘柄マスタの日本株名称を日本語に更新する
    
    Note: このエンドポイントは管理者専用です
    """
    try:
        # バックグラウンドタスクとして銘柄マスタの更新を実行
        background_tasks.add_task(market_service.enhance_ticker_master_with_jpx)
        
        return {
            "status": "success",
            "message": "銘柄マスタの更新をバックグラウンドで開始しました"
        }
    except Exception as e:
        # エラーハンドリング
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "errorCode": "INTERNAL_ERROR",
                "message": f"内部エラーが発生しました: {str(e)}"
            }
        )

# JPX銘柄辞書を直接更新するエンドポイントも追加
@router.post("/admin/reload-jpx-map", status_code=status.HTTP_200_OK)
def reload_jpx_map(
    market_service=Depends(get_market_service)
):
    """
    JPX銘柄辞書を再読み込みするエンドポイント（管理者用）
    
    このエンドポイントは以下の処理を行います：
    1. JPXデータを再読み込みし、銘柄辞書を更新する
    
    Note: このエンドポイントは管理者専用です
    """
    try:
        # JPX銘柄辞書を更新
        result = market_service.update_jpx_symbols_map()
        
        if result:
            return {
                "status": "success",
                "message": "JPX銘柄辞書を更新しました"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "errorCode": "UPDATE_FAILED",
                    "message": "JPX銘柄辞書の更新に失敗しました"
                }
            )
    except Exception as e:
        # エラーハンドリング
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "errorCode": "INTERNAL_ERROR",
                "message": f"内部エラーが発生しました: {str(e)}"
            }
        ) 