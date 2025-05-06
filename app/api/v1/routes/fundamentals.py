from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional

from app.api.dependencies import get_market_service
from app.schemas.fundamental import FundamentalData

router = APIRouter(
    prefix="/fundamentals",
    tags=["fundamentals"],
    responses={
        404: {"description": "Not found"},
        503: {"description": "Service unavailable"},
    },
)

@router.get("/{symbol}", response_model=FundamentalData)
def get_fundamental_data(
    symbol: str,
    market_service=Depends(get_market_service)
):
    """
    ファンダメンタル分析データの取得エンドポイント
    
    - **symbol**: 銘柄シンボル（例: AAPL, 9432.T）
    """
    try:
        fundamental_data = market_service.get_fundamental_data(symbol)
        return fundamental_data
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