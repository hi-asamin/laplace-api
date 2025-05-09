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

# 管理者用APIエンドポイント（銘柄マスター更新）
@router.post("/admin/update-jpx-data", response_model=dict)
def update_jpx_data(
    request: Request,
    market_service=Depends(get_market_service)
):
    """
    JPXデータを使用して日本株の銘柄マスタを更新する管理者用エンドポイント
    
    特定のIPアドレスからのみアクセス可能（簡易認証）
    """
    # クライアントのIPアドレスを取得
    client_ip = request.client.host
    
    # ローカル環境からのみアクセス可能（本番環境では適切な認証を実装すべき）
    allowed_ips = ["127.0.0.1", "localhost", "::1"]
    if client_ip not in allowed_ips:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "ACCESS_DENIED",
                "message": "管理者機能へのアクセスが拒否されました"
            }
        )
    
    try:
        # JPX銘柄辞書を更新
        update_result = market_service.update_jpx_symbols_map()
        
        if update_result:
            # 銘柄マスタをJPXデータで拡充
            enhance_result = market_service.enhance_ticker_master_with_jpx()
            return {
                "success": True,
                "message": "JPXデータを使用して銘柄マスタを更新しました",
                "details": {
                    "jpx_map_updated": update_result,
                    "ticker_master_enhanced": enhance_result
                }
            }
        else:
            return {
                "success": False,
                "message": "JPXデータの更新に失敗しました"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "UPDATE_FAILED",
                "message": f"銘柄マスタの更新中にエラーが発生しました: {str(e)}"
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