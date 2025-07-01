from enum import Enum, auto
from typing import Dict

class Period(str, Enum):
    """株価データの取得期間を表す列挙型"""
    one_day = "1d"
    five_days = "5d"
    one_month = "1mo"
    three_months = "3mo"
    six_months = "6mo"
    one_year = "1y"
    two_years = "2y"
    five_years = "5y"
    ten_years = "10y"
    ytd = "ytd"  # Year to date
    max = "max"

class AssetType(str, Enum):
    """資産タイプの列挙型"""
    STOCK = "STOCK"  # 株式
    ETF = "ETF"  # 上場投資信託
    INDEX = "INDEX"  # 指数
    CRYPTO = "CRYPTO"  # 暗号資産
    COMMODITY = "COMMODITY"  # 商品
    MUTUAL_FUND = "MUTUAL_FUND"  # 投資信託

# yfinanceのperiodパラメータにマッピング
PERIOD_MAP: Dict[Period, str] = {
    Period.one_day: "1d",
    Period.five_days: "5d",
    Period.one_month: "1mo",
    Period.three_months: "3mo",
    Period.six_months: "6mo",
    Period.one_year: "1y",
    Period.two_years: "2y",
    Period.five_years: "5y",
    Period.ten_years: "10y",
    Period.ytd: "ytd",
    Period.max: "max",
} 