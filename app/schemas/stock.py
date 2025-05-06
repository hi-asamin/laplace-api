from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.enums import Period

class PricePoint(BaseModel):
    """価格時系列の1ポイントを表すモデル"""
    date: str = Field(..., description="日付")
    close: float = Field(..., description="終値")
    dividend: float = Field(0.0, description="配当金")

class StockDetailResponse(BaseModel):
    """株式詳細情報のレスポンスモデル"""
    symbol: str = Field(..., description="株式シンボル")
    name: str = Field(..., description="会社名")
    currency: str = Field("USD", description="通貨")
    period: Period = Field(..., description="期間")
    prices: List[PricePoint] = Field(..., description="価格履歴")
    dividend_yield: Optional[float] = Field(None, description="配当利回り（%）") 