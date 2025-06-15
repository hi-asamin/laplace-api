from typing import List, Optional
from pydantic import BaseModel, Field

class RelatedMarket(BaseModel):
    """関連銘柄のモデル（最適化版）"""
    symbol: str = Field(..., description="銘柄シンボル")
    name: str = Field(..., description="銘柄名")
    price: str = Field(..., description="現在の株価")
    change_percent: str = Field(..., description="変化率")
    logo_url: Optional[str] = Field(None, description="ロゴURL")

class RelatedMarketsResponse(BaseModel):
    """関連銘柄のレスポンスモデル"""
    items: List[RelatedMarket] = Field(..., description="関連銘柄リスト") 