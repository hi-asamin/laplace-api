from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import date

class QuarterlyEarning(BaseModel):
    """四半期業績データモデル"""
    quarter: str = Field(..., description="四半期")
    value: str = Field(..., description="一株当たり純利益")
    report_date: date = Field(..., description="決算発表日")
    previous_year_value: Optional[str] = Field(None, description="前年同期の一株当たり純利益")
    growth_rate: Optional[str] = Field(None, description="前年同期比成長率")

class IndustryAverages(BaseModel):
    """業界平均指標モデル"""
    industry_name: str = Field(..., description="業界名")
    average_per: Optional[str] = Field(None, description="業界平均PER")
    average_pbr: Optional[str] = Field(None, description="業界平均PBR")
    sample_size: Optional[int] = Field(None, description="サンプル企業数")
    last_updated: Optional[str] = Field(None, description="最終更新日")

class KeyMetrics(BaseModel):
    """主要指標モデル"""
    eps: str = Field(..., description="一株当たり利益（直近12ヶ月）")
    pe_ratio: str = Field(..., description="PER（株価収益率）")
    forward_pe: Optional[str] = Field(None, description="予想PER")
    price_to_sales: Optional[str] = Field(None, description="PSR（株価売上高倍率）")
    price_to_book: Optional[str] = Field(None, description="PBR（株価純資産倍率）")
    roe: Optional[str] = Field(None, description="自己資本利益率")
    roa: Optional[str] = Field(None, description="総資産利益率")
    debt_to_equity: Optional[str] = Field(None, description="負債資本比率")
    current_ratio: Optional[str] = Field(None, description="流動比率")
    operating_margin: Optional[str] = Field(None, description="営業利益率")
    profit_margin: Optional[str] = Field(None, description="純利益率")
    industry_averages: Optional[IndustryAverages] = Field(None, description="業界平均指標")

class DividendData(BaseModel):
    """配当情報モデル"""
    dividend: str = Field(..., description="一株当たり配当金額（年間）")
    dividend_yield: str = Field(..., description="配当利回り")
    payout_ratio: Optional[str] = Field(None, description="配当性向")
    ex_dividend_date: Optional[date] = Field(None, description="権利落ち日")
    next_payment_date: Optional[date] = Field(None, description="次回支払日")

class QuarterlyDividend(BaseModel):
    """四半期配当情報モデル"""
    quarter: str = Field(..., description="四半期（例：第1四半期、第2四半期）")
    amount: Optional[str] = Field(None, description="配当金額")

class DividendHistory(BaseModel):
    """配当履歴モデル"""
    fiscal_year: str = Field(..., description="会計年度（例：2024年3月期）")
    total_dividend: str = Field(..., description="年間配当金額（調整後）")
    is_forecast: bool = Field(False, description="予想値かどうか")
    quarterly_dividends: List[QuarterlyDividend] = Field([], description="四半期別配当金")
    announcement_date: Optional[date] = Field(None, description="配当発表日")

class ValuationGrowth(BaseModel):
    """成長性指標モデル"""
    revenue_growth: Optional[str] = Field(None, description="売上高成長率（前年比）")
    earnings_growth: Optional[str] = Field(None, description="利益成長率（前年比）")
    eps_ttm: str = Field(..., description="過去12ヶ月のEPS")
    eps_growth: Optional[str] = Field(None, description="EPS成長率（前年比）")
    estimated_eps_growth: Optional[str] = Field(None, description="予想EPS成長率（来年）")

class FundamentalData(BaseModel):
    """ファンダメンタル分析データのレスポンスモデル"""
    symbol: str = Field(..., description="銘柄シンボル")
    quarterly_earnings: List[QuarterlyEarning] = Field([], description="四半期業績推移")
    key_metrics: KeyMetrics = Field(..., description="主要指標")
    dividend_data: Optional[DividendData] = Field(None, description="配当情報")
    dividend_history: List[DividendHistory] = Field([], description="配当履歴")
    valuation_growth: Optional[ValuationGrowth] = Field(None, description="成長性指標") 