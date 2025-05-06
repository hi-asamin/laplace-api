from functools import lru_cache
from app.services import market as market_service
from app.services import simulation as sim_service

@lru_cache(maxsize=1)
def get_market_service():
    """マーケットサービスのインスタンスを取得"""
    return market_service

# 互換性維持のため、一時的に残す
@lru_cache(maxsize=1)
def get_data_service():
    """マーケットサービスのインスタンスを取得（旧名称、互換性のため維持）"""
    return market_service

@lru_cache(maxsize=1)
def get_simulation_service():
    """シミュレーションサービスのインスタンスを取得"""
    return sim_service 