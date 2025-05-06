from fastapi import APIRouter
from app.api.v1.routes import markets, simulation, charts, fundamentals, related

# v1 APIルーター
router = APIRouter(prefix="/v1")

# 各エンドポイントをv1ルーターに登録
router.include_router(markets.router)
router.include_router(simulation.router)
router.include_router(charts.router)
router.include_router(fundamentals.router)
router.include_router(related.router) 