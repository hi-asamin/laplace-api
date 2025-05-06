from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional

from app.api.dependencies import get_market_service
from app.schemas.chart import ChartData

router = APIRouter(
    prefix="/charts",
    tags=["charts"],
    responses={
        404: {"description": "Not found"},
        503: {"description": "Service unavailable"},
    },
)

@router.get("/{symbol}", response_model=ChartData)
def get_chart_data(
    symbol: str,
    period: str = Query("3M", description="期間（1D, 1W, 1M, 3M, 6M, 1Y, ALL）"),
    interval: str = Query("1D", description="データポイントの間隔（1m, 5m, 15m, 30m, 60m, 1D, 1W, 1M）"),
    market_service=Depends(get_market_service)
):
    """
    チャートデータの取得エンドポイント
    
    - **symbol**: 銘柄シンボル（例: AAPL, 9432.T）
    - **period**: データ期間（1D, 1W, 1M, 3M, 6M, 1Y, ALL）
    - **interval**: データポイントの間隔（1m, 5m, 15m, 30m, 60m, 1D, 1W, 1M）
    """
    try:
        chart_data = market_service.get_chart_data(symbol, period, interval)
        return chart_data
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