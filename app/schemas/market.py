from pydantic import BaseModel, Field

class StockSearchResult(BaseModel):
    """検索結果の株式銘柄を表すモデル"""
    symbol: str = Field(..., description="株式シンボル")
    name: str = Field(..., description="会社名")
    price: str = Field(..., description="現在価格（米国株は$、日本株は¥）")
    change_percent: str = Field(..., description="前日比変化率")
    market: str = Field("US", description="市場（US/Japan）")

class SearchErrorResponse(BaseModel):
    """検索エラーレスポンスのモデル"""
    error_code: str = Field(..., description="エラーコード")
    message: str = Field(..., description="エラーメッセージ") 