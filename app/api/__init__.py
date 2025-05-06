from fastapi import APIRouter

# APIルーター
api_router = APIRouter()

# v1 APIルーターをインポート
from app.api.v1 import router as v1_router

# 各バージョンのルーターを登録
api_router.include_router(v1_router) 