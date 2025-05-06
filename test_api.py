import requests
import json
from time import time
import asyncio
import sys

# テスト対象のURLをセット
BASE_URL = "http://localhost:8000/v1"  # 開発環境

# テスト用のシンボル
TEST_SYMBOLS = ["AAPL", "MSFT", "GOOG", "7203.T", "9984.T"]

def print_response(description, response, show_full=False):
    """
    APIレスポンスを整形して表示する関数
    """
    try:
        elapsed = response.elapsed.total_seconds() * 1000  # ms単位
        status = response.status_code
        
        print(f"\n===== {description} =====")
        print(f"Status: {status}, Time: {elapsed:.2f}ms")
        
        if response.status_code >= 400:
            print(f"Error: {response.text}")
            return
        
        data = response.json()
        
        if show_full:
            # 完全なレスポンスを表示
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            # 要約を表示
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 2:
                        print(f"{key}: [{len(value)} items]")
                        print(f"  First item: {json.dumps(value[0], ensure_ascii=False)}")
                        print(f"  Last item: {json.dumps(value[-1], ensure_ascii=False)}")
                    elif isinstance(value, dict) and len(value) > 5:
                        print(f"{key}: {{{len(value)} keys}}")
                        sample_keys = list(value.keys())[:3]
                        for k in sample_keys:
                            print(f"  {k}: {value[k]}")
                    else:
                        print(f"{key}: {value}")
            else:
                print(data)
    except Exception as e:
        print(f"Error processing response: {e}")
        print(f"Raw response: {response.text[:200]}...")

def test_search_api():
    """検索APIをテストする関数"""
    url = f"{BASE_URL}/markets/search"
    queries = ["apple", "トヨタ", "ソフトバンク", "NVIDIA", "IBM"]
    
    for query in queries:
        params = {"query": query}
        
        start_time = time()
        response = requests.get(url, params=params)
        end_time = time()
        
        print_response(f"Search API ({query})", response)

def test_market_details_api():
    """銘柄詳細情報APIをテストする関数"""
    for symbol in TEST_SYMBOLS:
        url = f"{BASE_URL}/markets/{symbol}"
        
        start_time = time()
        response = requests.get(url)
        end_time = time()
        
        print_response(f"Market Details API ({symbol})", response)

def test_chart_api():
    """チャートデータAPIをテストする関数"""
    periods = ["1D", "1M", "3M", "1Y"]
    intervals = ["1D", "1W"]
    
    # テスト対象を制限
    symbol = TEST_SYMBOLS[0]  # AAPLのみでテスト
    
    for period in periods:
        for interval in intervals:
            url = f"{BASE_URL}/charts/{symbol}"
            params = {"period": period, "interval": interval}
            
            start_time = time()
            response = requests.get(url, params=params)
            end_time = time()
            
            print_response(f"Chart API ({symbol}, {period}, {interval})", response)
            
            # 最初の組み合わせのみ詳細表示
            if period == periods[0] and interval == intervals[0]:
                print_response(f"Chart API Detail ({symbol}, {period}, {interval})", response, show_full=True)
            
            # 全組み合わせをテストすると時間がかかるので、1つの期間につき1つの間隔のみテスト
            break

def test_fundamental_api():
    """ファンダメンタル分析データAPIをテストする関数"""
    for symbol in TEST_SYMBOLS[:2]:  # 最初の2つのシンボルでテスト
        url = f"{BASE_URL}/fundamentals/{symbol}"
        
        start_time = time()
        response = requests.get(url)
        end_time = time()
        
        print_response(f"Fundamental API ({symbol})", response)

def test_related_api():
    """関連銘柄APIをテストする関数"""
    for symbol in TEST_SYMBOLS[:2]:  # 最初の2つのシンボルでテスト
        url = f"{BASE_URL}/related/{symbol}"
        params = {"limit": 3}
        
        start_time = time()
        response = requests.get(url, params=params)
        end_time = time()
        
        print_response(f"Related Markets API ({symbol})", response)

def main():
    """メイン関数"""
    print("=== Laplace Markets API Test ===")
    
    if len(sys.argv) > 1:
        # コマンドライン引数による特定のテスト実行
        test_name = sys.argv[1].lower()
        
        if test_name == "search":
            test_search_api()
        elif test_name == "details":
            test_market_details_api()
        elif test_name == "chart":
            test_chart_api()
        elif test_name == "fundamental":
            test_fundamental_api()
        elif test_name == "related":
            test_related_api()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: search, details, chart, fundamental, related")
    else:
        # すべてのテストを実行
        print("\nRunning all tests...")
        test_search_api()
        test_market_details_api()
        test_chart_api()
        test_fundamental_api()
        test_related_api()
        
    print("\n=== Test completed ===")

if __name__ == "__main__":
    main() 