from typing import List, Optional, Union
from pydantic import BaseModel, Field

class RelatedMarket(BaseModel):
    """関連銘柄のモデル（最適化版）"""
    symbol: str = Field(..., description="銘柄シンボル")
    name: str = Field(..., description="銘柄名")
    price: Union[float, int] = Field(..., description="現在の株価")
    change_percent: Union[float, int] = Field(..., description="変化率（%）")
    logo_url: Optional[str] = Field(None, description="ロゴURL")
    dividend_yield: Optional[str] = Field(None, description="配当利回り")

class RelatedMarketsResponse(BaseModel):
    """関連銘柄のレスポンスモデル"""
    items: List[RelatedMarket] = Field(..., description="関連銘柄リスト") 