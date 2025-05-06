from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from app.api import api_router
import humps

# ===================================================
# バージョン情報
# ===================================================
API_VERSION = "1.0.0"
MIN_APP_VERSION = "1.0.0"  # アプリの最小互換バージョン

# カスタムJSONレスポンスクラス（キャメルケース変換）
class CamelCaseJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        # dictまたはlistの場合はキャメルケースに変換
        if isinstance(content, (dict, list)):
            camelized_content = humps.camelize(content)
            return super().render(camelized_content)
        return super().render(content)

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="Laplace Stock Analysis API",
    description="""
    株式分析のためのAPI（米国株・日本株対応）
    
    ## バージョニング
    
    - `/v1/*` - 安定版APIエンドポイント（推奨）
    - 直接ルート（`/markets/*`など）- レガシー互換性用（非推奨）
    
    ## 認証
    
    現在は認証が必要ありませんが、将来的にはAPIキーが必要になる可能性があります。
    """,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    default_response_class=CamelCaseJSONResponse,  # デフォルトのレスポンスクラスを設定
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では具体的なオリジンのリストに変更すべき
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# アプリバージョンチェックミドルウェア
@app.middleware("http")
async def check_app_version(request: Request, call_next):
    """
    クライアントアプリのバージョンをチェックするミドルウェア
    X-App-Versionヘッダーが提供されている場合にチェックする
    """
    app_version = request.headers.get("X-App-Version")
    
    # ドキュメントページはチェック対象外
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # 現在はヘッダーを要求しない（将来的に強制する可能性あり）
    if app_version is None:
        return await call_next(request)
    
    # バージョン比較（シンプルな文字列比較、将来的には semver 比較を実装）
    if app_version < MIN_APP_VERSION:
        return CamelCaseJSONResponse(
            status_code=status.HTTP_426_UPGRADE_REQUIRED,
            content={
                "error": {
                    "code": "MIN_VERSION_UNSUPPORTED",
                    "message": f"お使いのアプリバージョン({app_version})はサポートされていません。{MIN_APP_VERSION}以上にアップデートしてください。",
                    "updateUrl": "https://example.com/app/update"
                }
            }
        )
    
    return await call_next(request)

# ルーターの登録
app.include_router(api_router)

# 起動時処理
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    # データの自動ロードは不要（必要時に遅延ロードされる）
    pass

# 終了時処理
@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    # リソースのクリーンアップなどを行う場合はここに記述
    pass
