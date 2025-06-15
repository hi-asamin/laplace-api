from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional
from enum import Enum

from app.api.dependencies import get_market_service
from app.schemas.related import RelatedMarketsResponse

class RelationCriteria(str, Enum):
    """関連付けの基準"""
    INDUSTRY = "industry"
    DIVIDEND_YIELD = "dividend_yield"

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
    criteria: RelationCriteria = Query(RelationCriteria.INDUSTRY, description="関連付けの基準（industry: 業界, dividend_yield: 利回り率）"),
    min_dividend_yield: Optional[float] = Query(None, description="最小利回り率（%）- criteria=dividend_yieldの場合に使用"),
    market_service=Depends(get_market_service)
):
    """
    関連銘柄の取得エンドポイント
    
    - **symbol**: 銘柄シンボル（例: AAPL, 9432.T）
    - **limit**: 返却する結果の最大数
    - **criteria**: 関連付けの基準（industry: 業界, dividend_yield: 利回り率）
    - **min_dividend_yield**: 最小利回り率（%）- criteria=dividend_yieldの場合に使用
    """
    try:
        if criteria == RelationCriteria.DIVIDEND_YIELD and min_dividend_yield is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "MISSING_PARAMETER",
                    "message": "利回り率基準の場合、min_dividend_yieldパラメータが必要です"
                }
            )
        
        related_markets = market_service.get_related_markets(
            symbol=symbol, 
            limit=limit, 
            criteria=criteria.value,
            min_dividend_yield=min_dividend_yield
        )
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