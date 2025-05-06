from typing import List, Optional
from pydantic import BaseModel, Field

class RelatedMarket(BaseModel):
    """関連銘柄のモデル"""
    symbol: str = Field(..., description="銘柄シンボル")
    name: str = Field(..., description="企業名")
    price: Optional[str] = Field(None, description="現在の株価")
    change: Optional[str] = Field(None, description="前日比の変化額")
    change_percent: Optional[str] = Field(None, description="前日比の変化率")
    is_positive: Optional[bool] = Field(None, description="株価変動が正かどうか")
    logo_url: Optional[str] = Field(None, description="企業ロゴのURL")
    relation_type: Optional[str] = Field(None, description="関連性の種類")
    sector: Optional[str] = Field(None, description="セクター")

class RelatedMarketsResponse(BaseModel):
    """関連銘柄のレスポンスモデル"""
    items: List[RelatedMarket] = Field(..., description="関連銘柄リスト") 