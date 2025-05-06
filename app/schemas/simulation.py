from typing import List
from pydantic import BaseModel, Field

class SimulationRequest(BaseModel):
    """シミュレーションリクエストのモデル"""
    symbol: str = Field(..., description="シミュレーション対象の株式シンボル")
    years: int = Field(5, description="シミュレーション期間（年）", ge=1, le=30)
    simulations: int = Field(100, description="シミュレーション回数", ge=10, le=1000)

class SimulationResponse(BaseModel):
    """シミュレーション結果のレスポンスモデル"""
    symbol: str = Field(..., description="株式シンボル")
    scenarios: List[List[float]] = Field(..., description="シミュレーション結果") 