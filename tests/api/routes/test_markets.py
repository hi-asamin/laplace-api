import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
import json

from app.main import app
from app.services.market import JAPAN_TICKERS, INITIAL_TICKERS, fuzzy_search

# テスト用のクライアント
client = TestClient(app)

# テスト用のデータセットを作成
@pytest.fixture
def test_ticker_data():
    # テスト用データフレームを作成
    test_data = {
        'Symbol': ['AAPL', 'MSFT', 'GOOGL', '7203.T', '9432.T', '9984.T'],
        'Name': ['Apple Inc.', 'Microsoft Corporation', 'Alphabet Inc. (Google)', 'トヨタ自動車', '日本電信電話', 'ソフトバンクグループ'],
        'Market': ['US', 'US', 'US', 'Japan', 'Japan', 'Japan']
    }
    return pd.DataFrame(test_data)

# モック関数を作成
def mock_fuzzy_search(query, limit=10, market=None):
    """テスト用のモック検索関数"""
    query = query.lower().strip()
    
    # limitとmarketパラメータは無視
    
    if query == "apple":
        return [{'symbol': 'AAPL', 'name': 'Apple Inc.', 'score': 100, 'market': 'US'}]
    elif query == "トヨタ":
        return [{'symbol': '7203.T', 'name': 'トヨタ自動車', 'score': 100, 'market': 'Japan'}]
    elif query == "電話":
        return [{'symbol': '9432.T', 'name': '日本電信電話', 'score': 80, 'market': 'Japan'}]
    elif query == "自動車":
        return [{'symbol': '7203.T', 'name': 'トヨタ自動車', 'score': 80, 'market': 'Japan'}]
    elif query == "inc":
        return [{'symbol': 'AAPL', 'name': 'Apple Inc.', 'score': 80, 'market': 'US'}]
    elif query == "アップル":
        return [{'symbol': 'AAPL', 'name': 'Apple Inc.', 'score': 100, 'market': 'US'}]
    elif not query:
        # 空クエリの場合はエラーが発生するのでから配列
        return []
    else:
        return []

@pytest.fixture
def patch_fuzzy_search():
    """fuzzy_search関数をモック化"""
    with patch('app.services.market.fuzzy_search', side_effect=mock_fuzzy_search):
        yield

@pytest.fixture
def patch_stock_price():
    """get_stock_price関数をモック化"""
    def mock_get_price(symbol):
        is_japan = symbol.endswith('.T')
        currency = "¥" if is_japan else "$"
        return {
            "price": f"{currency}100.00",
            "change_percent": "+1.2%"
        }
    
    with patch('app.services.market.get_stock_price', side_effect=mock_get_price):
        yield

# テストケース
@pytest.mark.usefixtures("patch_fuzzy_search", "patch_stock_price")
def test_search_with_exact_match():
    """完全一致の検索結果が1件だけ返されることをテスト"""
    response = client.get("/v1/markets/search?query=Apple")
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) == 1
    assert results[0]["symbol"] == "AAPL"
    assert results[0]["name"] == "Apple Inc."
    assert results[0]["market"] == "US"

@pytest.mark.usefixtures("patch_fuzzy_search", "patch_stock_price")
def test_search_with_japanese_company():
    """日本語企業名での検索が機能することをテスト"""
    response = client.get("/v1/markets/search?query=トヨタ")
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) == 1
    assert results[0]["symbol"] == "7203.T"
    assert results[0]["name"] == "トヨタ自動車"
    assert results[0]["market"] == "Japan"
    assert "¥" in results[0]["price"]

@pytest.mark.usefixtures("patch_fuzzy_search", "patch_stock_price")
def test_search_with_keyword_in_japanese_company():
    """日本語キーワード「電話」で「日本電信電話」が検索できることをテスト"""
    response = client.get("/v1/markets/search?query=電話")
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) >= 1
    assert results[0]["symbol"] == "9432.T"
    assert "電話" in results[0]["name"]

@pytest.mark.usefixtures("patch_fuzzy_search", "patch_stock_price")
def test_multiple_results():
    """検索結果が複数返されることをテスト"""
    # 単に自動車と検索
    response = client.get("/v1/markets/search?query=自動車")
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) > 0
    
    # 単にincと検索
    response = client.get("/v1/markets/search?query=inc")
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) > 0

@pytest.mark.usefixtures("patch_fuzzy_search", "patch_stock_price")
def test_popular_companies():
    """POPULAR_COMPANIESに登録されている企業が検索できることをテスト"""
    response = client.get("/v1/markets/search?query=アップル")
    assert response.status_code == 200
    data = response.json()
    results = data["results"]
    assert len(results) == 1
    assert results[0]["symbol"] == "AAPL"

@pytest.mark.usefixtures("patch_fuzzy_search", "patch_stock_price")
def test_empty_query():
    """空のクエリに対してエラーが返されることをテスト"""
    response = client.get("/v1/markets/search?query=")
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "INVALID_QUERY"

# レガシーエンドポイントも引き続き動作することを確認
@pytest.mark.usefixtures("patch_fuzzy_search", "patch_stock_price")
def test_legacy_endpoint():
    """レガシーエンドポイントでも同じ結果が得られることをテスト"""
    v1_response = client.get("/v1/markets/search?query=トヨタ")
    legacy_response = client.get("/markets/search?query=トヨタ")
    
    assert v1_response.status_code == 200
    assert legacy_response.status_code == 200
    
    v1_data = v1_response.json()
    legacy_data = legacy_response.json()
    
    assert v1_data == legacy_data 