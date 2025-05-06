from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional

from app.api.dependencies import get_market_service
from app.schemas.related import RelatedMarketsResponse

router = APIRouter(
    prefix="/related",
    tags=["related"],
    responses={
        404: {"description": "Not found"},
        503: {"description": "Service unavailable"},
    },
)

@router.get("/{symbol}", response_model=RelatedMarketsResponse)
def get_related_markets(
    symbol: str,
    limit: int = Query(5, description="返却する結果の最大数"),
    market_service=Depends(get_market_service)
):
    """
    関連銘柄の取得エンドポイント
    
    - **symbol**: 銘柄シンボル（例: AAPL, 9432.T）
    - **limit**: 返却する結果の最大数
    """
    try:
        related_markets = market_service.get_related_markets(symbol, limit)
        return related_markets
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