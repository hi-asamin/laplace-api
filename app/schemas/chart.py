from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class ChartPoint(BaseModel):
    """チャートの1データポイントを表すモデル"""
    date: datetime = Field(..., description="データポイントの日時")
    open: float = Field(..., description="始値")
    high: float = Field(..., description="高値")
    low: float = Field(..., description="安値")
    close: float = Field(..., description="終値")
    volume: int = Field(..., description="出来高")

class ChartData(BaseModel):
    """チャートデータのレスポンスモデル"""
    symbol: str = Field(..., description="銘柄シンボル")
    period: str = Field(..., description="データ期間")
    interval: str = Field(..., description="データ間隔") 
    data: List[ChartPoint] = Field(..., description="チャートデータポイント") 