from app.main import app
from mangum import Mangum

# FastAPIアプリケーションをAWS Lambda用にラップ
handler = Mangum(app) 