from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.enums import AssetType

class SearchResult(BaseModel):
    """検索結果の1アイテムを表すモデル"""
    symbol: str = Field(..., description="銘柄コード")
    name: str = Field(..., description="銘柄名")
    asset_type: AssetType = Field(AssetType.STOCK, description="資産タイプ")
    market: str = Field(..., description="市場")
    price: Optional[str] = Field(None, description="現在価格")
    change_percent: Optional[str] = Field(None, description="前日比")
    logo_url: Optional[str] = Field(None, description="企業ロゴのURL")

class SearchResponse(BaseModel):
    """検索結果のレスポンスモデル"""
    results: List[SearchResult] = Field(..., description="検索結果リスト")
    total: int = Field(..., description="検索結果の総数") 