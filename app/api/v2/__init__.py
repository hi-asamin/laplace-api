from fastapi import APIRouter
# 将来的に作成されるv2エンドポイントをインポート
# from app.api.v2.routes import markets, simulation

# v2 APIルーター
router = APIRouter(prefix="/v2")

# 各エンドポイントをv2ルーターに登録
# 将来的なv2APIが実装されたらコメントアウトを解除
# router.include_router(markets.router)
# router.include_router(simulation.router) 