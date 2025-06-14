from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class TradingInfo(BaseModel):
    """取引情報モデル"""
    previous_close: str = Field(..., description="前日終値")
    open: str = Field(..., description="始値")
    day_high: str = Field(..., description="日中高値")
    day_low: str = Field(..., description="日中安値")
    volume: str = Field(..., description="出来高")
    avg_volume: str = Field(..., description="平均出来高")
    market_cap: str = Field(..., description="時価総額")
    pe_ratio: Optional[str] = Field(None, description="PER（株価収益率）")
    primary_exchange: str = Field(..., description="主要取引所")

class CompanyProfile(BaseModel):
    """企業プロフィール情報モデル"""
    company_name: str = Field(..., description="企業名")
    logo_url: Optional[str] = Field(None, description="企業ロゴ画像のURL")
    website: Optional[str] = Field(None, description="公式サイトのURL")
    market_cap_formatted: Optional[str] = Field(None, description="兆・億単位に整形済みの時価総額")
    business_summary: Optional[str] = Field(None, description="事業内容のサマリー")
    industry_tags: List[str] = Field([], description="業種を示すタグのリスト")
    full_time_employees: Optional[int] = Field(None, description="従業員数")
    foundation_year: Optional[int] = Field(None, description="設立年")
    headquarters: Optional[str] = Field(None, description="本社所在地")

class MarketDetails(BaseModel):
    """銘柄詳細情報のレスポンスモデル"""
    symbol: str = Field(..., description="銘柄シンボル")
    name: str = Field(..., description="企業名")
    market: str = Field(..., description="取引市場（US/Japan）")
    market_name: Optional[str] = Field(None, description="取引市場の正式名称")
    price: str = Field(..., description="現在の株価")
    change: str = Field(..., description="前日比の変化額")
    change_percent: str = Field(..., description="前日比の変化率")
    is_positive: bool = Field(..., description="株価変動が正かどうか")
    currency: str = Field(..., description="通貨単位")
    logo_url: Optional[str] = Field(None, description="企業ロゴのURL")
    sector: Optional[str] = Field(None, description="セクター")
    industry: Optional[str] = Field(None, description="業種")
    description: Optional[str] = Field(None, description="企業概要")
    website: Optional[str] = Field(None, description="企業のウェブサイト")
    trading_info: TradingInfo = Field(..., description="取引情報")
    dividend_yield: Optional[str] = Field(None, description="配当利回り（%）")
    company_profile: CompanyProfile = Field(..., description="企業プロフィール情報")
    last_updated: str = Field(..., description="情報取得日時（ISO 8601形式）") 