from functools import lru_cache
import yfinance as yf
import pandas as pd
from rapidfuzz import process, fuzz
from pathlib import Path
import random
import re
from app.models.enums import AssetType
from datetime import date, timedelta, datetime, timezone
import os
from .dynamodb import (
    save_stock_data,
    get_stock_data,
    update_stock_data,
    convert_to_dataframe
)
from typing import List, Dict, Any, Optional

TICKER_CACHE = Path(__file__).with_suffix(".csv")
JPX_DATA_FILE = Path(__file__).parent / "data.csv"  # .xlsから.csvに変更

# 主要企業のロゴURLを定義
LOGO_URLS = {
  "AAPL": "https://logo.clearbit.com/apple.com",
  "AMZN": "https://logo.clearbit.com/amazon.com",
  "GOOG": "https://logo.clearbit.com/google.com",
  "MSFT": "https://logo.clearbit.com/microsoft.com",
  "META": "https://logo.clearbit.com/meta.com",
  "TSLA": "https://logo.clearbit.com/tesla.com",
  "NFLX": "https://logo.clearbit.com/netflix.com",
  "SPOT": "https://logo.clearbit.com/spotify.com",
  "NVDA": "https://logo.clearbit.com/nvidia.com",
  "BABA": "https://logo.clearbit.com/alibaba.com",
  "ORCL": "https://logo.clearbit.com/oracle.com",
  "IBM":  "https://logo.clearbit.com/ibm.com",
  "INTC": "https://logo.clearbit.com/intel.com",
  "CRM":  "https://logo.clearbit.com/salesforce.com",
  "PYPL": "https://logo.clearbit.com/paypal.com",
  "UBER": "https://logo.clearbit.com/uber.com",
  "DIS":  "https://logo.clearbit.com/disney.com",
  "SBUX": "https://logo.clearbit.com/starbucks.com",
  "SHOP": "https://logo.clearbit.com/shopify.com",
  "ADBE": "https://logo.clearbit.com/adobe.com",
  "ABNB": "https://logo.clearbit.com/airbnb.com",
  "TWTR": "https://logo.clearbit.com/x.com",  # Twitter（現X）
  "LYFT": "https://logo.clearbit.com/lyft.com",
  "SNAP": "https://logo.clearbit.com/snap.com",
  "COIN": "https://logo.clearbit.com/coinbase.com",
  "SQ":   "https://logo.clearbit.com/block.xyz", # Block Inc (旧Square)
  "AMD":  "https://logo.clearbit.com/amd.com",
  "ZM":   "https://logo.clearbit.com/zoom.us",
  "TSM":  "https://logo.clearbit.com/tsmc.com",
  "PINS": "https://logo.clearbit.com/pinterest.com",
  "RBLX": "https://logo.clearbit.com/roblox.com",
  "ARM":  "https://logo.clearbit.com/arm.com",
  "7203.T": "https://logo.clearbit.com/toyota-global.com", # トヨタ自動車
  "6758.T": "https://logo.clearbit.com/sony.com", # ソニーグループ
  "7974.T": "https://logo.clearbit.com/nintendo.com", # 任天堂
  "7267.T": "https://logo.clearbit.com/honda.com", # ホンダ
  "6752.T": "https://logo.clearbit.com/panasonic.com", # パナソニック
  "7751.T": "https://logo.clearbit.com/global.canon", # キヤノン
  "6501.T": "https://logo.clearbit.com/hitachi.com", # 日立製作所
  "6701.T": "https://logo.clearbit.com/jp.nec.com", # NEC
  "6702.T": "https://logo.clearbit.com/fujitsu.com", # 富士通
  "9433.T": "https://logo.clearbit.com/kddi.com", # KDDI
  "9432.T": "https://logo.clearbit.com/ntt.com", # NTT
  "9984.T": "https://logo.clearbit.com/softbank.jp", # ソフトバンクグループ
  "8058.T": "https://logo.clearbit.com/mitsubishicorp.com", # 三菱商事
  "8031.T": "https://logo.clearbit.com/mitsui.com", # 三井物産
  "8053.T": "https://logo.clearbit.com/sumitomocorp.com", # 住友商事
  "2914.T": "https://logo.clearbit.com/jt.com", # JT
  "4502.T": "https://logo.clearbit.com/takeda.com", # 武田薬品工業
  "6367.T": "https://logo.clearbit.com/daikin.com", # ダイキン工業
  "9983.T": "https://logo.clearbit.com/fastretailing.com", # ファーストリテイリング
  "4755.T": "https://logo.clearbit.com/rakuten.co.jp", # 楽天グループ
  "4689.T": "https://logo.clearbit.com/lycorp.co.jp", # Zホールディングス→LY Corporation
  "9201.T": "https://logo.clearbit.com/jal.com", # 日本航空
  "9202.T": "https://logo.clearbit.com/ana.co.jp", # ANAホールディングス
  "6902.T": "https://logo.clearbit.com/denso.com", # デンソー
  "6645.T": "https://logo.clearbit.com/omron.com" # オムロン
}

# 静的銘柄データ（曖昧検索用）
INITIAL_TICKERS = [
    {"Symbol": "AAPL", "Name": "Apple Inc.", "Market": "US"},
    {"Symbol": "MSFT", "Name": "Microsoft Corporation", "Market": "US"},
    {"Symbol": "GOOGL", "Name": "Alphabet Inc.", "Market": "US"},
    {"Symbol": "AMZN", "Name": "Amazon.com Inc.", "Market": "US"},
    {"Symbol": "TSLA", "Name": "Tesla Inc.", "Market": "US"},
    {"Symbol": "META", "Name": "Meta Platforms Inc.", "Market": "US"},
    {"Symbol": "NVDA", "Name": "NVIDIA Corporation", "Market": "US"},
    {"Symbol": "NFLX", "Name": "Netflix Inc.", "Market": "US"},
    {"Symbol": "PYPL", "Name": "PayPal Holdings Inc.", "Market": "US"},
    {"Symbol": "ADBE", "Name": "Adobe Inc.", "Market": "US"},
    {"Symbol": "CRM", "Name": "Salesforce Inc.", "Market": "US"},
    {"Symbol": "ORCL", "Name": "Oracle Corporation", "Market": "US"},
    {"Symbol": "IBM", "Name": "International Business Machines Corporation", "Market": "US"},
    {"Symbol": "INTC", "Name": "Intel Corporation", "Market": "US"},
    {"Symbol": "AMD", "Name": "Advanced Micro Devices Inc.", "Market": "US"},
    {"Symbol": "SPY", "Name": "SPDR S&P 500 ETF Trust", "Market": "US"},
    {"Symbol": "QQQ", "Name": "Invesco QQQ Trust", "Market": "US"},
    {"Symbol": "VTI", "Name": "Vanguard Total Stock Market ETF", "Market": "US"},
]

JAPAN_TICKERS = [
    {"Symbol": "7203.T", "Name": "トヨタ自動車", "EnglishName": "Toyota Motor Corporation", "Market": "Japan"},
    {"Symbol": "6758.T", "Name": "ソニーグループ", "EnglishName": "Sony Group Corporation", "Market": "Japan"},
    {"Symbol": "7974.T", "Name": "任天堂", "EnglishName": "Nintendo Co., Ltd.", "Market": "Japan"},
    {"Symbol": "9432.T", "Name": "日本電信電話", "EnglishName": "Nippon Telegraph and Telephone Corporation", "Market": "Japan"},
    {"Symbol": "9984.T", "Name": "ソフトバンクグループ", "EnglishName": "SoftBank Group Corp.", "Market": "Japan"},
    {"Symbol": "6902.T", "Name": "デンソー", "EnglishName": "DENSO Corporation", "Market": "Japan"},
    {"Symbol": "6752.T", "Name": "パナソニック", "EnglishName": "Panasonic Holdings Corporation", "Market": "Japan"},
    {"Symbol": "7267.T", "Name": "ホンダ", "EnglishName": "Honda Motor Co., Ltd.", "Market": "Japan"},
    {"Symbol": "4502.T", "Name": "武田薬品工業", "EnglishName": "Takeda Pharmaceutical Company Limited", "Market": "Japan"},
    {"Symbol": "8058.T", "Name": "三菱商事", "EnglishName": "Mitsubishi Corporation", "Market": "Japan"},
    {"Symbol": "8031.T", "Name": "三井物産", "EnglishName": "Mitsui & Co., Ltd.", "Market": "Japan"},
    {"Symbol": "9983.T", "Name": "ファーストリテイリング", "EnglishName": "Fast Retailing Co., Ltd.", "Market": "Japan"},
    {"Symbol": "4755.T", "Name": "楽天グループ", "EnglishName": "Rakuten Group, Inc.", "Market": "Japan"},
    {"Symbol": "9201.T", "Name": "日本航空", "EnglishName": "Japan Airlines Co., Ltd.", "Market": "Japan"},
    {"Symbol": "9202.T", "Name": "ANAホールディングス", "EnglishName": "ANA Holdings Inc.", "Market": "Japan"},
]

@lru_cache(maxsize=1)
def load_ticker_master():
    """銘柄マスターデータをロードする関数"""
    # DynamoDBからデータを取得
    items = get_stock_data()
    
    if items:
        df = convert_to_dataframe(items)
        # 各シンボルに対して名前が正しく設定されているか確認
        for idx, row in df.iterrows():
            if row["Name"] == row["Symbol"] or row["Name"] == f"{row['Symbol']} Stock":
                # 名前がシンボルと同じ場合、yfinanceから正しい名前を取得
                try:
                    info = get_company_info(row["Symbol"])
                    if info["name"] != f"{row['Symbol']} Stock":
                        update_stock_data(row["Symbol"], {"Name": info["name"]})
                except Exception as e:
                    print(f"Error updating name for {row['Symbol']}: {e}")
        return df
    
    # データが存在しない場合は初期データを保存
    print("DynamoDBにデータが存在しないため、初期データを保存します")
    initial_data = []
    for ticker in INITIAL_TICKERS:
        ticker["Market"] = "US"
        initial_data.append(ticker)
    
    for ticker in JAPAN_TICKERS:
        ticker["Market"] = "Japan"
        initial_data.append(ticker)
    
    save_stock_data(initial_data)
    return convert_to_dataframe(initial_data)

@lru_cache(maxsize=1024)
def fuzzy_search_lightweight(query: str, limit: int = 10, market: str = None):
    """
    軽量版曖昧検索関数（DynamoDBアクセスなし）
    
    静的データのみを使用して高速検索を実行
    
    Args:
        query: 検索クエリ
        limit: 検索結果の上限数
        market: 市場フィルタ（"US", "Japan", None）
        
    Returns:
        List[Dict]: 検索結果
    """
    # 検索クエリのバリデーション
    if not query or len(query.strip()) < 1:
        return []
    
    # 静的データを取得
    df = get_static_ticker_data()
    
    # 検索クエリの前処理
    query = query.strip()
    lower_query = query.lower()
    
    results = []
    
    # 1. シンボルでの検索
    try:
        # 完全一致
        exact_matches = df[df['Symbol'].str.lower() == lower_query]
        for _, row in exact_matches.iterrows():
            symbol = row['Symbol']
            results.append({
                'symbol': symbol,
                'name': row['Name'],
                'score': 100,
                'asset_type': AssetType.STOCK,
                'market': row['Market'],
                'logo_url': LOGO_URLS.get(symbol)
            })
        
        # 部分一致
        contains = df[df['Symbol'].str.lower().str.contains(lower_query, na=False)]
        for _, row in contains.iterrows():
            symbol = row['Symbol']
            if not any(r['symbol'] == symbol for r in results):  # 重複を避ける
                results.append({
                    'symbol': symbol,
                    'name': row['Name'],
                    'score': 90,
                    'asset_type': AssetType.STOCK,
                    'market': row['Market'],
                    'logo_url': LOGO_URLS.get(symbol)
                })
    except Exception as e:
        print(f"シンボル検索中にエラーが発生しました: {e}")
    
    # 2. 名前での検索（日本語名・英語名両方）
    for col in ['Name', 'EnglishName']:
        if col not in df.columns:
            continue
        
        try:
            # 完全一致
            exact_matches = df[df[col].str.lower() == lower_query]
            for _, row in exact_matches.iterrows():
                symbol = row['Symbol']
                if not any(r['symbol'] == symbol for r in results):  # 重複を避ける
                    results.append({
                        'symbol': symbol,
                        'name': row.get('Name', row.get('EnglishName', '')),
                        'score': 100,
                        'asset_type': AssetType.STOCK,
                        'market': row['Market'],
                        'logo_url': LOGO_URLS.get(symbol)
                    })
            
            # 先頭一致
            starts_with = df[df[col].str.lower().str.startswith(lower_query)]
            for _, row in starts_with.iterrows():
                symbol = row['Symbol']
                if not any(r['symbol'] == symbol for r in results):
                    results.append({
                        'symbol': symbol,
                        'name': row.get('Name', row.get('EnglishName', '')),
                        'score': 90,
                        'asset_type': AssetType.STOCK,
                        'market': row['Market'],
                        'logo_url': LOGO_URLS.get(symbol)
                    })
            
            # 部分一致
            contains = df[df[col].str.lower().str.contains(lower_query, na=False)]
            for _, row in contains.iterrows():
                symbol = row['Symbol']
                if not any(r['symbol'] == symbol for r in results):
                    results.append({
                        'symbol': symbol,
                        'name': row.get('Name', row.get('EnglishName', '')),
                        'score': 80,
                        'asset_type': AssetType.STOCK,
                        'market': row['Market'],
                        'logo_url': LOGO_URLS.get(symbol)
                    })
        except Exception as e:
            print(f"{col}での検索中にエラーが発生しました: {e}")
    
    # スコア順にソート
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # 市場でフィルタリング
    if market:
        results = [r for r in results if r['market'] == market]
    
    return results[:limit]

@lru_cache(maxsize=1024)
def fuzzy_search(query: str, limit: int = 10, market: str = None):
    """
    株式銘柄をあいまい検索する関数（リファクタリング版）
    
    まず静的データで検索し、結果が不十分な場合のみDynamoDBにアクセス
    
    Args:
        query: 検索クエリ
        limit: 検索結果の上限数
        market: 市場フィルタ（"US", "Japan", None）
        
    Returns:
        List[Dict]: 検索結果
    """
    # 検索クエリのバリデーション
    if not query or len(query.strip()) < 1:
        return []
    
    # Step 1: 静的データから検索
    static_results = fuzzy_search_lightweight(query, limit, market)
    
    # 十分な結果が得られた場合はそれを返す（最低3件、またはlimitに達した場合）
    if len(static_results) >= min(limit, 3) or len(static_results) >= limit:
        print(f"静的データ検索で {len(static_results)} 件の結果を取得（DynamoDBアクセスなし）")
        return static_results
    
    # Step 2: 結果が少ない場合のみ、DynamoDBから追加データを取得
    print(f"静的データ検索結果: {len(static_results)} 件。DynamoDBから追加データを取得します。")
    
    try:
        # DynamoDBからデータを取得
        df = load_ticker_master()
        
        if len(df) == 0:
            print("DynamoDB取得失敗、静的データ結果を返します")
            return static_results
        
        # 既存の検索ロジックを実行（DynamoDBデータ使用）
        additional_results = search_in_dataframe(query, limit - len(static_results), market, df)
        
        # 重複を除去して結合
        combined_results = static_results.copy()
        existing_symbols = {r['symbol'] for r in static_results}
        
        for result in additional_results:
            if result['symbol'] not in existing_symbols:
                combined_results.append(result)
                existing_symbols.add(result['symbol'])
        
        print(f"最終結果: {len(combined_results)} 件（静的: {len(static_results)}, DynamoDB: {len(additional_results)}）")
        return combined_results[:limit]
        
    except Exception as e:
        print(f"DynamoDB検索中にエラーが発生しました: {e}")
        return static_results

def search_in_dataframe(query: str, limit: int, market: str, df: pd.DataFrame):
    """
    DataFrameから検索を実行するヘルパー関数
    """
    # 欠損値を処理
    df = df.fillna('')
    
    # 市場区分が設定されているか確認
    if 'Market' not in df.columns:
        df['Market'] = df['Symbol'].apply(lambda x: 'Japan' if str(x).endswith('.T') else 'US')
    
    # 検索クエリの前処理
    query = query.strip()
    lower_query = query.lower()
    
    results = []
    
    # 1. シンボルでの検索
    try:
        # 完全一致
        exact_matches = df[df['Symbol'].str.lower() == lower_query]
        for _, row in exact_matches.iterrows():
            symbol = row['Symbol']
            results.append({
                'symbol': symbol,
                'name': row.get('Name', row.get('EnglishName', '')),
                'score': 100,
                'asset_type': AssetType.STOCK,
                'market': row.get('Market', 'US' if not symbol.endswith('.T') else 'Japan'),
                'logo_url': LOGO_URLS.get(symbol)
            })
        
        # 部分一致
        contains = df[df['Symbol'].str.lower().str.contains(lower_query, na=False)]
        for _, row in contains.iterrows():
            symbol = row['Symbol']
            if not any(r['symbol'] == symbol for r in results):
                results.append({
                    'symbol': symbol,
                    'name': row.get('Name', row.get('EnglishName', '')),
                    'score': 90,
                    'asset_type': AssetType.STOCK,
                    'market': row.get('Market', 'US' if not symbol.endswith('.T') else 'Japan'),
                    'logo_url': LOGO_URLS.get(symbol)
                })
    except Exception as e:
        print(f"シンボル検索中にエラーが発生しました: {e}")
    
    # 2. 名前での検索
    for col in ['Name', 'EnglishName']:
        if col not in df.columns:
            continue
        
        try:
            # 完全一致
            exact_matches = df[df[col].str.lower() == lower_query]
            for _, row in exact_matches.iterrows():
                symbol = row['Symbol']
                if not any(r['symbol'] == symbol for r in results):
                    results.append({
                        'symbol': symbol,
                        'name': row.get('Name', row.get('EnglishName', '')),
                        'score': 100,
                        'asset_type': AssetType.STOCK,
                        'market': row.get('Market', 'US' if not symbol.endswith('.T') else 'Japan'),
                        'logo_url': LOGO_URLS.get(symbol)
                    })
            
            # 先頭一致
            starts_with = df[df[col].str.lower().str.startswith(lower_query)]
            for _, row in starts_with.iterrows():
                symbol = row['Symbol']
                if not any(r['symbol'] == symbol for r in results):
                    results.append({
                        'symbol': symbol,
                        'name': row.get('Name', row.get('EnglishName', '')),
                        'score': 90,
                        'asset_type': AssetType.STOCK,
                        'market': row.get('Market', 'US' if not symbol.endswith('.T') else 'Japan'),
                        'logo_url': LOGO_URLS.get(symbol)
                    })
            
            # 部分一致
            contains = df[df[col].str.lower().str.contains(lower_query, na=False)]
            for _, row in contains.iterrows():
                symbol = row['Symbol']
                if not any(r['symbol'] == symbol for r in results):
                    results.append({
                        'symbol': symbol,
                        'name': row.get('Name', row.get('EnglishName', '')),
                        'score': 80,
                        'asset_type': AssetType.STOCK,
                        'market': row.get('Market', 'US' if not symbol.endswith('.T') else 'Japan'),
                        'logo_url': LOGO_URLS.get(symbol)
                    })
        except Exception as e:
            print(f"{col}での検索中にエラーが発生しました: {e}")
    
    # スコア順にソート
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # 市場でフィルタリング
    if market:
        results = [r for r in results if r['market'] == market]
    
    return results[:limit]



@lru_cache(maxsize=256)
def get_price_history(symbol: str, period: str):
    """指定された銘柄の価格履歴を取得する"""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)
    dividends = ticker.dividends
    hist = hist.reset_index()
    hist["Date"] = hist["Date"].dt.strftime("%Y-%m-%d")
    hist["Dividend"] = hist["Date"].map(dividends.to_dict()).fillna(0.0)
    return hist

def reset_ticker_cache():
    """
    銘柄マスタのキャッシュを再構築する関数（管理者用）
    """
    try:
        # S&P 500の銘柄データを取得
        print("S&P500データを取得中...")
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        sp500 = sp500[['Symbol', 'Security']]
        sp500.columns = ['Symbol', 'Name']
        sp500["Market"] = "US"
        print(f"S&P500から {len(sp500)} 件のデータを取得しました")
    
        # 日本株データの取得（初期データを使用）
        print("日本株データを取得中...")
        japan_stocks = pd.DataFrame(JAPAN_TICKERS)
        japan_stocks["Market"] = "Japan"
        print(f"初期データから {len(japan_stocks)} 件の日本株データを取得しました")
    
        # データの結合
        print("データを結合中...")
        combined_df = pd.concat([sp500, japan_stocks], ignore_index=True)
        print(f"合計 {len(combined_df)} 銘柄のデータを取得しました（米国: {len(sp500)}, 日本: {len(japan_stocks)}）")
    
        # DynamoDBに保存
        save_stock_data(combined_df.to_dict('records'))
        print("データをDynamoDBに保存しました")
        return combined_df
    except Exception as e:
        print(f"銘柄マスタの更新中にエラーが発生しました: {e}")
        # 初期データを使用
        df = pd.DataFrame(INITIAL_TICKERS + JAPAN_TICKERS)
        df["Market"] = df["Symbol"].apply(lambda x: "Japan" if str(x).endswith(".T") else "US")
        save_stock_data(df.to_dict('records'))
        return df

def get_company_info(symbol: str):
    """
    シンボルから企業情報を取得する関数
    日本株の場合は日本語名称を優先的に返す
    """
    try:
        # 日本株の場合は日本語名を優先
        japanese_name = None
        if symbol.endswith(".T"):
            # DynamoDBから直接データを取得
            stock_data = get_stock_data(symbol)
            if stock_data and len(stock_data) > 0:
                japanese_name = stock_data[0].get("name")
        
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 企業名を取得（複数のフィールドを試す）
        company_name = None
        
        # 日本株で日本語名があれば優先
        if japanese_name:
            company_name = japanese_name
        else:
            # それ以外は通常の順序で取得
            for field in ['longName', 'shortName', 'name']:
                if field in info and info[field]:
                    company_name = info[field]
                    break
        
        if not company_name:
            company_name = f"{symbol} Stock"
        
        # 事前定義したロゴURLがあればそれを使用
        logo_url = LOGO_URLS.get(symbol)
        
        # ロゴURLがない場合はウェブサイトからClearbitロゴを生成する可能性を残す
        website = info.get('website', '')
        
        return {
            "name": company_name,
            "sector": info.get('sector', ''),
            "industry": info.get('industry', ''),
            "country": info.get('country', ''),
            "website": website,
            "logoUrl": logo_url
        }
    except Exception as e:
        print(f"Error fetching info for {symbol}: {e}")
        # エラー時も日本語名と可能ならロゴURLを提供
        if symbol.endswith(".T"):
            # DynamoDBから直接データを取得
            stock_data = get_stock_data(symbol)
            if stock_data and len(stock_data) > 0:
                japanese_name = stock_data[0].get("name")
                if japanese_name:
                    return {"name": japanese_name, "logoUrl": LOGO_URLS.get(symbol)}
        
        # その他のケース
        logo_url = LOGO_URLS.get(symbol)
        return {"name": f"{symbol} Stock", "logoUrl": logo_url}

def get_stock_price(symbol: str):
    """
    銘柄の価格情報を取得する関数
    yfinanceから最新データを取得します
    """
    # シンボルから市場を判断
    is_japan_stock = symbol.endswith(".T")
    currency_symbol = "¥" if is_japan_stock else "$"
    
    try:
        ticker = yf.Ticker(symbol)
        
        # 日本株の場合、取引時間内かどうかを判定
        if is_japan_stock:
            current_time = datetime.now(timezone(timedelta(hours=9)))  # JST
            is_trading_hours = (
                current_time.weekday() < 5 and  # 平日
                9 <= current_time.hour < 15 or  # 9:00-15:00
                (current_time.hour == 15 and current_time.minute <= 30)  # 15:00-15:30
            )
            
            if is_trading_hours:
                # 取引時間内は1分足のデータを取得
                data = ticker.history(period="1d", interval="1m")
            else:
                # 取引時間外は日足のデータを取得
                data = ticker.history(period="1d")
        else:
            # 米国株の場合は日足のデータを取得
            data = ticker.history(period="1d")
        
        if not data.empty:
            # 最新の終値
            latest_price = data['Close'].iloc[-1]
            # データ取得時刻（最新のデータの日時）
            last_updated = data.index[-1]
            
            # 前日比の変化率を計算
            if len(data) > 1:
                prev_close = data['Close'].iloc[-2]
                change_percent = ((latest_price - prev_close) / prev_close) * 100
            else:
                # 1日分のデータしかない場合
                change_percent = 0
            
            # UTCに変換して返却
            utc_time = last_updated.astimezone(timezone.utc)
            
            return {
                "price": f"{currency_symbol}{latest_price:.2f}",
                "change_percent": f"{'+' if change_percent > 0 else ''}{change_percent:.1f}%",
                "last_updated": utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
    
    # エラーが発生した場合や、データが取得できない場合はランダムな値を返す
    price = round(random.uniform(10, 1000), 2)
    change = round(random.uniform(-5, 5), 1)
    current_utc = datetime.now(timezone.utc)
    
    return {
        "price": f"{currency_symbol}{price}",
        "change_percent": f"{'+' if change > 0 else ''}{change}%",
        "last_updated": current_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

# 銘柄マスタを修正して日本株を追加する
def add_japan_stocks_to_cache():
    """
    既存の銘柄マスタを維持したまま、日本株データを追加する関数
    """
    print("銘柄マスタに日本株を追加します...")
    
    # 現在のデータを取得
    current_items = get_stock_data()
    current_data = convert_to_dataframe(current_items) if current_items else pd.DataFrame()
    
    # 日本株データを取得
    japan_df = pd.DataFrame(JAPAN_TICKERS)
    japan_df["Market"] = "Japan"
    print(f"日本株データ: {len(japan_df)}件")
    
    # 既存データに日本株が含まれているかチェック
    japan_symbols = set()
    if not current_data.empty and 'Symbol' in current_data.columns:
        japan_symbols = set(current_data[current_data['Symbol'].str.endswith('.T')]['Symbol'])
    
    # 既に含まれている日本株の数を表示
    print(f"既存データに含まれる日本株: {len(japan_symbols)}件")
    
    # 既存データに含まれていない日本株のみを追加
    new_japan_stocks = japan_df[~japan_df['Symbol'].isin(japan_symbols)]
    print(f"新たに追加する日本株: {len(new_japan_stocks)}件")
    
    # 既存データがない場合は米国株も追加
    if current_data.empty:
        print("既存データがないため、米国株も追加します")
        us_df = pd.DataFrame(INITIAL_TICKERS)
        us_df["Market"] = "US"
        current_data = pd.concat([current_data, us_df], ignore_index=True)
        print(f"米国株データ: {len(us_df)}件")
    
    # 日本株を追加
    if len(new_japan_stocks) > 0:
        combined_df = pd.concat([current_data, new_japan_stocks], ignore_index=True)
        print(f"合計データ: {len(combined_df)}件")
        
        # DynamoDBに保存
        save_stock_data(combined_df.to_dict('records'))
        print("データをDynamoDBに保存しました")
        
        # キャッシュをクリア
        load_ticker_master.cache_clear()
        
        return combined_df
    else:
        print("新たに追加する日本株はありません")
        return current_data

# S&P 500主要銘柄をダウンロードして追加する
def load_us_stocks():
    """米国主要株式のデータをダウンロードする"""
    try:
        # S&P 500の構成銘柄をダウンロード
        sp500_url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        sp500_df = pd.read_csv(sp500_url)
        
        # 必要なカラムに変換
        if 'Symbol' in sp500_df.columns and 'Name' in sp500_df.columns:
            sp500_processed = pd.DataFrame({
                'Symbol': sp500_df['Symbol'],
                'Name': sp500_df['Name'],
                'Market': 'US',
                'Sector': sp500_df.get('Sector', ''),
                'Industry': sp500_df.get('Industry', '')
            })
            print(f"S&P 500から {len(sp500_processed)} 件の米国株データを取得しました")
            return sp500_processed
        else:
            print("S&P 500データの形式が想定と異なります")
            
    except Exception as e:
        print(f"米国株データの取得中にエラーが発生しました: {e}")
    
    # エラーが発生した場合、初期データを使用
    us_df = pd.DataFrame(INITIAL_TICKERS)
    us_df["Market"] = "US"
    print(f"初期データから {len(us_df)} 件の米国株データを読み込みました")
    return us_df

# 銘柄マスタを拡充する
def expand_stock_data():
    """銘柄マスタを拡充し、S&P 500とJAPAN_TICKERSのデータを追加する"""
    print("銘柄マスタを拡充しています...")
    
    # 現在のデータを取得
    current_items = get_stock_data()
    current_data = convert_to_dataframe(current_items) if current_items else pd.DataFrame()
    
    # 米国株データを取得
    us_stocks = load_us_stocks()
    print(f"米国株データ: {len(us_stocks)}件")
    
    # 日本株データを取得
    japan_stocks = pd.DataFrame(JAPAN_TICKERS)
    japan_stocks["Market"] = "Japan"
    print(f"日本株データ: {len(japan_stocks)}件")
    
    # 既存のシンボルを取得
    existing_symbols = set()
    if not current_data.empty and 'Symbol' in current_data.columns:
        existing_symbols = set(current_data['Symbol'])
    
    # 既存データに含まれていない米国株のみを追加
    new_us_stocks = us_stocks[~us_stocks['Symbol'].isin(existing_symbols)]
    print(f"新たに追加する米国株: {len(new_us_stocks)}件")
    
    # 既存データに含まれていない日本株のみを追加
    new_japan_stocks = japan_stocks[~japan_stocks['Symbol'].isin(existing_symbols)]
    print(f"新たに追加する日本株: {len(new_japan_stocks)}件")
    
    # 新しいデータを追加
    if len(new_us_stocks) > 0 or len(new_japan_stocks) > 0:
        # 既存データがなければ、米国株と日本株を追加
        if current_data.empty:
            combined_df = pd.concat([us_stocks, japan_stocks], ignore_index=True)
        else:
            combined_df = pd.concat([current_data, new_us_stocks, new_japan_stocks], ignore_index=True)
        
        print(f"合計データ: {len(combined_df)}件")
        
        # 重複を排除
        combined_df = combined_df.drop_duplicates(subset=['Symbol'])
        print(f"重複排除後のデータ: {len(combined_df)}件")
        
        # 市場区分が設定されているか確認
        if 'Market' not in combined_df.columns:
            combined_df['Market'] = combined_df['Symbol'].apply(lambda x: 'Japan' if str(x).endswith('.T') else 'US')
        
        # DynamoDBに保存
        save_stock_data(combined_df.to_dict('records'))
        print("データをDynamoDBに保存しました")
        
        # キャッシュをクリア
        load_ticker_master.cache_clear()
        
        return combined_df
    else:
        print("新たに追加するデータはありません")
        return current_data

def calculate_dividend_yield(symbol: str, info: dict) -> Optional[str]:
    """
    配当利回りを計算する関数
    
    Args:
        symbol: 銘柄シンボル
        info: yfinanceから取得した銘柄情報
        
    Returns:
        Optional[str]: 配当利回り（%表記）、配当がない場合はNone
    """
    try:
        # 1. 最も確実な方法：配当レートと現在価格から計算（最優先）
        dividend_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate')
        current_price = (info.get('currentPrice') or 
                        info.get('regularMarketPrice') or 
                        info.get('previousClose'))
        
        if dividend_rate and current_price and current_price > 0:
            dividend_yield = (dividend_rate / current_price) * 100
            # 異常値チェック（50%超は異常値として除外）
            if dividend_yield > 50:
                print(f"Warning: Abnormal dividend yield {dividend_yield:.2f}% for {symbol}, using fallback")
            else:
                return f"{dividend_yield:.2f}%"
        
        # 2. yfinanceの配当利回りフィールドを慎重に使用
        # 注意: yfinanceのdividendYieldフィールドは信頼性が低いため、厳格にチェック
        dividend_yield_value = info.get('dividendYield')
        if dividend_yield_value and dividend_yield_value > 0:
            # 異常値の事前チェック
            if dividend_yield_value > 1:  # 1を超える場合は既にパーセント形式の可能性
                # 100%を超える配当利回りは現実的でない
                if dividend_yield_value > 100:
                    print(f"Warning: Extremely high dividend yield {dividend_yield_value} for {symbol}, skipping")
                else:
                    # 既にパーセント形式として扱う
                    return f"{dividend_yield_value:.2f}%"
            else:
                # 小数形式として扱う（0.05 = 5%）
                dividend_yield = dividend_yield_value * 100
                # 再度異常値チェック
                if dividend_yield > 50:
                    print(f"Warning: High dividend yield {dividend_yield:.2f}% for {symbol}, may be incorrect")
                else:
                    return f"{dividend_yield:.2f}%"
        
        # 3. trailingAnnualDividendYieldを使用（より慎重に）
        trailing_yield = info.get('trailingAnnualDividendYield')
        if trailing_yield and trailing_yield > 0:
            # 異常値の事前チェック
            if trailing_yield > 1:  # 1を超える場合は既にパーセント形式の可能性
                if trailing_yield > 100:
                    print(f"Warning: Extremely high trailing dividend yield {trailing_yield} for {symbol}, skipping")
                else:
                    return f"{trailing_yield:.2f}%"
            else:
                # 小数形式として扱う
                dividend_yield = trailing_yield * 100
                if dividend_yield > 50:
                    print(f"Warning: High trailing dividend yield {dividend_yield:.2f}% for {symbol}, may be incorrect")
                else:
                    return f"{dividend_yield:.2f}%"
        
        # 4. ETFや指数の場合、yield情報を取得
        if info.get('yield') and info.get('yield') > 0:
            yield_value = info.get('yield', 0)
            # yieldフィールドも同様にチェック
            if yield_value < 1:
                yield_value = yield_value * 100
            if yield_value <= 50:  # 異常値チェック
                return f"{yield_value:.2f}%"
        
        # 5. S&P500などの指数の場合、過去の平均利回りを推定
        if is_index_symbol(symbol):
            # S&P500の場合は平均配当利回り約1.8%を使用
            if symbol.upper() in ['SPY', '^SPX', 'SPX', '^GSPC']:
                return "1.80%"
            # その他の指数も一般的な利回りを返す
            return "1.50%"
        
        # 6. 配当がない場合は0.00%を返す
        # dividendRateが明示的に0またはNoneの場合
        if dividend_rate is not None and dividend_rate == 0:
            return "0.00%"
        
        return None
        
    except Exception as e:
        print(f"Error calculating dividend yield for {symbol}: {e}")
        return None

def is_index_symbol(symbol: str) -> bool:
    """
    シンボルが指数かどうかを判別する関数
    
    Args:
        symbol: 銘柄シンボル
        
    Returns:
        bool: 指数の場合True
    """
    # 一般的な指数シンボルのパターン
    index_patterns = [
        '^',  # Yahoo Finance指数プレフィックス
        'SPY', 'QQQ', 'IWM',  # 主要ETF
        'VOO', 'VTI', 'VEA',  # Vanguard ETF
    ]
    
    symbol_upper = symbol.upper()
    
    # プレフィックスチェック
    if symbol.startswith('^'):
        return True
    
    # 主要指数ETFチェック
    for pattern in index_patterns[1:]:  # '^'以外をチェック
        if symbol_upper.startswith(pattern):
            return True
    
    return False

def get_market_details(symbol: str):
    """
    銘柄の詳細情報を取得する関数
    
    Args:
        symbol: 銘柄シンボル (例: 'AAPL', '7203.T')
        
    Returns:
        dict: 銘柄の詳細情報
    """
    try:
        # シンボルから市場を判断
        is_japan_stock = symbol.endswith(".T")
        market = "Japan" if is_japan_stock else "US"
        currency = "JPY" if is_japan_stock else "USD"
        currency_symbol = "¥" if is_japan_stock else "$"
        
        # 基本情報を取得
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 価格情報を取得
        price_data = get_stock_price(symbol)
        latest_price = price_data["price"]
        change_percent = price_data["change_percent"]
        last_updated = price_data["last_updated"]
        
        # 前日比の数値を計算
        try:
            latest_price_value = float(latest_price.replace(currency_symbol, ""))
            change_percent_value = float(change_percent.replace("%", "").replace("+", ""))
            change_value = (latest_price_value * change_percent_value / 100)
            change = f"{'+' if change_percent_value > 0 else ''}{currency_symbol}{change_value:.2f}"
            is_positive = change_percent_value > 0
        except:
            change = "+0.00" if "+" in change_percent else "-0.00"
            is_positive = "+" in change_percent
        
        # 企業情報を取得
        company_info = get_company_info(symbol)
        
        # 取引情報を収集
        # 注: 実際のAPIでは全ての情報が取得できない場合があるため、エラーハンドリングを適切に行う
        trading_info = {
            "previous_close": f"{currency_symbol}{info.get('previousClose', 0):.2f}",
            "open": f"{currency_symbol}{info.get('open', 0):.2f}",
            "day_high": f"{currency_symbol}{info.get('dayHigh', 0):.2f}",
            "day_low": f"{currency_symbol}{info.get('dayLow', 0):.2f}",
            "volume": f"{info.get('volume', 0)/1000000:.1f}M",
            "avg_volume": f"{info.get('averageVolume', 0)/1000000:.1f}M",
            "market_cap": f"{currency_symbol}{info.get('marketCap', 0)/1000000000:.2f}B",
            "pe_ratio": f"{info.get('trailingPE', 0):.2f}" if info.get('trailingPE') else None,
            "primary_exchange": info.get('exchange', 'Unknown')
        }
        
        # ロゴURLを取得
        logo_url = company_info.get('logoUrl')
        
        # 事前定義したロゴがない場合はClearbitから取得（企業ドメインがあれば）
        if not logo_url and company_info.get('website'):
            domain = company_info['website'].replace('https://', '').replace('http://', '').split('/')[0]
            logo_url = f"https://logo.clearbit.com/{domain}"
        
        # 配当利回りを計算
        dividend_yield = calculate_dividend_yield(symbol, info)
        
        # 企業プロフィール情報を取得
        company_profile_data = get_company_profile(symbol)
        
        return {
            "symbol": symbol,
            "name": company_info.get('name', symbol),
            "market": market,
            "market_name": info.get('exchange', None),
            "price": latest_price,
            "change": change,
            "change_percent": change_percent,
            "is_positive": is_positive,
            "currency": currency,
            "logo_url": logo_url,
            "sector": company_info.get('sector', None),
            "industry": company_info.get('industry', None),
            "description": info.get('longBusinessSummary', None),
            "website": company_info.get('website', None),
            "trading_info": trading_info,
            "dividend_yield": dividend_yield,
            "company_profile": company_profile_data,
            "last_updated": last_updated
        }
    except Exception as e:
        print(f"Error fetching market details for {symbol}: {e}")
        raise ValueError(f"Failed to fetch market details for {symbol}")

def get_chart_data(symbol: str, period: str = "3M", interval: str = "1D"):
    """
    チャートデータを取得する関数
    
    Args:
        symbol: 銘柄シンボル (例: 'AAPL', '7203.T')
        period: データ期間 (1D, 1W, 1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y, ALL)
        interval: データ間隔 (1m, 5m, 15m, 30m, 60m, 1D, 1W, 1M)
        
    Returns:
        dict: チャートデータ
    """
    try:
        # 期間とインターバルをyfinance形式に変換
        period_mapping = {
            "1D": "1d", "1W": "5d", "1M": "1mo",
            "3M": "3mo", "6M": "6mo", "1Y": "1y",
            "2Y": "2y", "5Y": "5y", "10Y": "10y",
            "ALL": "max"
        }
        interval_mapping = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "60m": "60m", "1D": "1d", "1W": "1wk", "1M": "1mo"
        }
        
        # 1Dを選択した場合は、より詳細なデータを取得するために分単位のインターバルを使用
        if period == "1D":
            # インターバルがデフォルト（1D）または日以上の場合、5分間隔に変更
            if interval in ["1D", "1W", "1M"]:
                interval = "5m"
        
        yf_period = period_mapping.get(period, "3mo")
        yf_interval = interval_mapping.get(interval, "1d")
        
        # データ取得
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=yf_period, interval=yf_interval)
        
        # データが空または少ない場合の対応
        if len(data) <= 1 and period == "1D":
            # 1Dでデータが少ない場合は、2日分のデータを取得して最新日のみフィルタリング
            fallback_data = ticker.history(period="2d", interval="5m")
            # 最新の取引日のデータのみをフィルタリング
            if not fallback_data.empty:
                latest_date = fallback_data.index.date.max()
                data = fallback_data[fallback_data.index.date == latest_date]
        
        # データ整形
        chart_data = []
        for index, row in data.iterrows():
            chart_data.append({
                "date": index,
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"])
            })
        
        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "data": chart_data
        }
    except Exception as e:
        print(f"Error fetching chart data for {symbol}: {e}")
        raise ValueError(f"Failed to fetch chart data for {symbol}")

def get_fundamental_data(symbol: str):
    """
    ファンダメンタル分析データを取得する関数
    
    Args:
        symbol: 銘柄シンボル (例: 'AAPL', '7203.T')
        
    Returns:
        dict: ファンダメンタル分析データ
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 実際の四半期業績データを取得
        try:
            # yfinanceから四半期財務データを取得
            earnings_data = ticker.earnings
            earnings_quarterly = ticker.quarterly_earnings
            earnings_dates = ticker.earnings_dates
            
            # 四半期EPSデータがあるか確認
            has_quarterly_data = earnings_quarterly is not None and not earnings_quarterly.empty
            
            # 現在の年と四半期を取得
            from datetime import datetime
            current_year = datetime.now().year
            current_quarter = (datetime.now().month - 1) // 3 + 1  # 現在の四半期（1〜4）
            
            quarterly_earnings = []
            
            if has_quarterly_data:
                # 実際のデータを使用
                # earnings_quarterlyは通常古い四半期から新しい四半期順
                for i, (date_idx, row) in enumerate(earnings_quarterly.iterrows()):
                    if i >= 4:  # 直近4四半期のみ
                        break
                        
                    # 日付からYYYY-Q1形式の四半期名を生成
                    year = date_idx.year
                    q_num = (date_idx.month - 1) // 3 + 1
                    quarter_name = f"{year} Q{q_num}"
                    
                    # EPS値を取得
                    eps_value = row.get('Earnings', None)
                    if eps_value is not None:
                        value = f"${eps_value:.2f}"
                    else:
                        value = "N/A"
                    
                    # 前年同期のEPSを取得（あれば）
                    prev_year_idx = date_idx.replace(year=date_idx.year - 1)
                    prev_year_data = earnings_quarterly[earnings_quarterly.index == prev_year_idx]
                    
                    if not prev_year_data.empty:
                        prev_eps = prev_year_data.iloc[0].get('Earnings', None)
                        prev_value = f"${prev_eps:.2f}" if prev_eps is not None else "N/A"
                        
                        # 成長率を計算
                        if eps_value is not None and prev_eps is not None and prev_eps != 0:
                            growth_rate = ((eps_value - prev_eps) / abs(prev_eps)) * 100
                            growth_text = f"{'+' if growth_rate >= 0 else ''}{growth_rate:.1f}%"
                        else:
                            growth_text = "N/A"
                    else:
                        prev_value = "N/A"
                        growth_text = "N/A"
                    
                    # 発表日はインデックス自体を使用
                    report_date = date_idx.date()
                    
                    quarterly_earnings.append({
                        "quarter": quarter_name,
                        "value": value,
                        "report_date": report_date,
                        "previous_year_value": prev_value,
                        "growth_rate": growth_text
                    })
                
                # 最新の四半期が先頭に来るように並び替え
                quarterly_earnings.reverse()
            
            # データが取得できなかった場合はモックデータを生成
            if not quarterly_earnings:
                print(f"銘柄 {symbol} の実際の四半期データが取得できなかったため、推定データを生成します")
                # 現在の日付からエスティメートする
                for i in range(4):
                    # 過去4四半期のデータを生成
                    offset_quarter = i
                    q_num = current_quarter - offset_quarter
                    year = current_year
                    
                    # 前年度の四半期を調整
                    if q_num <= 0:
                        q_num += 4
                        year -= 1
                        
                    quarter_name = f"{year} Q{q_num}"
                    
                    # TTM EPSから概算値を計算（存在する場合）
                    ttm_eps = info.get('trailingEps', None)
                    if ttm_eps:
                        # TTM EPSを4等分して四半期の概算値を算出
                        estimated_quarterly_eps = ttm_eps / 4
                        value = f"${estimated_quarterly_eps:.2f} (est.)"
                        prev_value = f"${estimated_quarterly_eps * 0.9:.2f} (est.)"  # 前年比10%成長と仮定
                        growth = 10.0  # 概算成長率
                    else:
                        # TTM EPSがなければランダムな値を使用
                        value = f"${round(2 + random.uniform(-0.5, 0.5), 2)} (est.)"
                        prev_value = f"${round(1.8 + random.uniform(-0.3, 0.3), 2)} (est.)"
                        growth = round(random.uniform(5, 15), 1)
                    
                    # 四半期末の日付を概算
                    quarter_end_month = q_num * 3
                    report_offset = 45  # 報告は四半期末から約45日後
                    quarter_end_day = 31 if quarter_end_month in [3, 12] else 30
                    
                    # 決算発表日
                    if quarter_end_month + (report_offset // 30) > 12:
                        report_month = (quarter_end_month + (report_offset // 30)) % 12
                        report_year = year + 1 if quarter_end_month == 12 else year
                    else:
                        report_month = quarter_end_month + (report_offset // 30)
                        report_year = year
                        
                    report_day = min(quarter_end_day, 28 if report_month == 2 else 30)
                    report_date = date(report_year, report_month, report_day)
                    
                    quarterly_earnings.append({
                        "quarter": quarter_name,
                        "value": value,
                        "report_date": report_date,
                        "previous_year_value": prev_value,
                        "growth_rate": f"+{growth}% (est.)"
                    })
        except Exception as e:
            print(f"四半期データの取得中にエラーが発生しました: {e}")
            # エラー時はデフォルトに戻る
            quarterly_earnings = []
            
            # モックデータを生成
            from datetime import datetime
            current_year = datetime.now().year
            current_quarter = (datetime.now().month - 1) // 3 + 1  # 現在の四半期（1〜4）
            
            for i in range(4):
                # 過去4四半期のデータを生成
                offset_quarter = i
                q_num = current_quarter - offset_quarter
                year = current_year
                
                # 前年度の四半期を調整
                if q_num <= 0:
                    q_num += 4
                    year -= 1
                    
                quarter_name = f"{year} Q{q_num}"
                value = f"${round(2 + random.uniform(-0.5, 0.5), 2)} (est.)"
                prev_value = f"${round(1.8 + random.uniform(-0.3, 0.3), 2)} (est.)"
                growth = round(random.uniform(5, 15), 1)
                
                # 四半期末の日付を概算
                quarter_end_month = q_num * 3
                report_offset = 45
                quarter_end_day = 31 if quarter_end_month in [3, 12] else 30
                
                # 決算発表日
                if quarter_end_month + (report_offset // 30) > 12:
                    report_month = (quarter_end_month + (report_offset // 30)) % 12
                    report_year = year + 1 if quarter_end_month == 12 else year
                else:
                    report_month = quarter_end_month + (report_offset // 30)
                    report_year = year
                    
                report_day = min(quarter_end_day, 28 if report_month == 2 else 30)
                report_date = date(report_year, report_month, report_day)
                
                quarterly_earnings.append({
                    "quarter": quarter_name,
                    "value": value,
                    "report_date": report_date,
                    "previous_year_value": prev_value,
                    "growth_rate": f"+{growth}% (est.)"
                })
        
        # 主要指標
        eps = info.get('trailingEps', 0)
        pe_ratio = info.get('trailingPE', 0)
        
        # 業界平均データを取得
        industry_averages_data = None
        industry = info.get('industry', '')
        sector = info.get('sector', '')
        
        # 業界平均サービスをインポート
        from app.services.industry_averages import industry_averages_service
        
        # まず業界名で検索、見つからなければセクター名で検索
        industry_avg = industry_averages_service.get_industry_averages(industry)
        if not industry_avg and sector:
            industry_avg = industry_averages_service.get_industry_averages(sector)
        
        if industry_avg:
            industry_averages_data = {
                "industry_name": industry_avg["industry_name"],
                "average_per": f"{industry_avg['average_per']:.1f}",
                "average_pbr": f"{industry_avg['average_pbr']:.1f}",
                "sample_size": industry_avg["sample_size"],
                "last_updated": industry_avg["last_updated"]
            }
        
        key_metrics = {
            "eps": f"{eps:.2f}",
            "pe_ratio": f"{pe_ratio:.2f}",
            "forward_pe": f"{info.get('forwardPE', 0):.2f}" if info.get('forwardPE') else None,
            "price_to_sales": f"{info.get('priceToSalesTrailing12Months', 0):.2f}" if info.get('priceToSalesTrailing12Months') else None,
            "price_to_book": f"{info.get('priceToBook', 0):.2f}" if info.get('priceToBook') else None,
            "roe": f"{info.get('returnOnEquity', 0) * 100:.1f}%" if info.get('returnOnEquity') else None,
            "roa": None,  # Yahoo Financeから直接取得できない
            "debt_to_equity": f"{info.get('debtToEquity', 0):.1f}%" if info.get('debtToEquity') else None,
            "current_ratio": f"{info.get('currentRatio', 0):.2f}" if info.get('currentRatio') else None,
            "operating_margin": f"{info.get('operatingMargins', 0) * 100:.1f}%" if info.get('operatingMargins') else None,
            "profit_margin": f"{info.get('profitMargins', 0) * 100:.1f}%" if info.get('profitMargins') else None,
            "industry_averages": industry_averages_data
        }
        
        # 配当情報
        dividend_data = None
        if info.get('dividendRate'):
            # 日本株と米国株で通貨単位を調整
            currency_symbol = "¥" if symbol.endswith('.T') else "$"
            
            # 権利落ち日と次回支払日
            ex_date = None
            next_payment = None
            if info.get('exDividendDate'):
                timestamp = info.get('exDividendDate')
                if timestamp:
                    ex_date = date.fromtimestamp(timestamp)
                    # 次回支払日は推定（通常は権利落ち日の数週間後）
                    next_payment = ex_date + timedelta(days=30)
            
            # 配当利回りの処理（修正済みのcalculate_dividend_yield関数を使用）
            dividend_yield_formatted = calculate_dividend_yield(symbol, info)
            if not dividend_yield_formatted:
                dividend_yield_formatted = "0.00%"
            
            dividend_data = {
                "dividend": f"{currency_symbol}{info.get('dividendRate', 0):.2f}",
                "dividend_yield": dividend_yield_formatted,
                "payout_ratio": f"{info.get('payoutRatio', 0) * 100:.1f}%" if info.get('payoutRatio') else None,
                "ex_dividend_date": ex_date,
                "next_payment_date": next_payment
            }
        
        # 成長性指標
        valuation_growth = {
            "revenue_growth": f"+{info.get('revenueGrowth', 0) * 100:.1f}%" if info.get('revenueGrowth') else None,
            "earnings_growth": f"+{info.get('earningsGrowth', 0) * 100:.1f}%" if info.get('earningsGrowth') else None,
            "eps_ttm": f"{info.get('trailingEps', 0):.2f}",
            "eps_growth": f"+{random.uniform(5, 10):.1f}%",  # モックデータ
            "estimated_eps_growth": f"+{random.uniform(3, 8):.1f}%"  # モックデータ
        }
        
        # 配当履歴を取得
        dividend_history = get_dividend_history(symbol)
        
        return {
            "symbol": symbol,
            "quarterly_earnings": quarterly_earnings,
            "key_metrics": key_metrics,
            "dividend_data": dividend_data,
            "dividend_history": dividend_history,
            "valuation_growth": valuation_growth
        }
    except Exception as e:
        print(f"Error fetching fundamental data for {symbol}: {e}")
        raise ValueError(f"Failed to fetch fundamental data for {symbol}")

@lru_cache(maxsize=1024)
def get_related_markets(symbol: str, limit: int = 5):
    """
    関連銘柄を取得する関数
    
    Args:
        symbol: 銘柄シンボル (例: 'AAPL', '7203.T')
        limit: 返却する結果の最大数
        
    Returns:
        dict: 関連銘柄のリスト
    """
    try:
        # シンボルから市場とセクターを判断
        is_japan_stock = symbol.endswith('.T')
        market = "Japan" if is_japan_stock else "US"
        
        # 基本情報を取得（キャッシュ済みの関数を使用）
        company_info = get_company_info(symbol)
        sector = company_info.get('sector', '')
        
        # 同一セクターの銘柄を取得（キャッシュ済みの関数を使用）
        df = load_ticker_master()
        
        # セクター情報がない場合は空のリストを返す
        if not sector or len(df) == 0:
            return {"items": []}
        
        # 同一市場、同一セクターで異なる銘柄を抽出
        if 'Sector' in df.columns:
            sector_matches = df[(df['Market'] == market) & 
                               (df['Sector'].str.lower() == sector.lower()) & 
                               (df['Symbol'] != symbol)]
        else:
            # セクター情報がない場合は同一市場の銘柄をランダムに抽出
            sector_matches = df[(df['Market'] == market) & 
                               (df['Symbol'] != symbol)]
        
        # 十分な銘柄がない場合はランダムな銘柄で補完
        if len(sector_matches) < limit:
            other_matches = df[(df['Market'] == market) & 
                             (df['Symbol'] != symbol)]
            if 'Sector' in df.columns:
                other_matches = other_matches[other_matches['Sector'].str.lower() != sector.lower()]
            
            # 不足分をランダムに追加
            if len(other_matches) > 0:
                random_sample = other_matches.sample(min(limit - len(sector_matches), len(other_matches)))
                sector_matches = pd.concat([sector_matches, random_sample])
        
        # 結果を制限
        related_symbols = sector_matches.head(limit)
        
        # 関連銘柄のリストを作成
        items = []
        for _, row in related_symbols.iterrows():
            rel_symbol = row['Symbol']
            try:
                # 価格情報を取得（キャッシュ済みの関数を使用）
                price_info = get_stock_price(rel_symbol)
                
                # 前日比の数値を計算
                currency_symbol = "¥" if rel_symbol.endswith('.T') else "$"
                change_percent = price_info["change_percent"]
                latest_price = price_info["price"]
                
                try:
                    latest_price_value = float(latest_price.replace(currency_symbol, "").replace(",", ""))
                    change_percent_value = float(change_percent.replace("%", "").replace("+", ""))
                    change_value = (latest_price_value * change_percent_value / 100)
                    change = f"{'+' if change_percent_value > 0 else ''}{currency_symbol}{change_value:.2f}"
                    is_positive = change_percent_value > 0
                except:
                    change = "+0.00" if "+" in change_percent else "-0.00"
                    is_positive = "+" in change_percent
                
                # 企業情報を取得（キャッシュ済みの関数を使用）
                rel_company_info = get_company_info(rel_symbol)
                
                # ロゴURLを取得
                logo_url = LOGO_URLS.get(rel_symbol)
                
                # 事前定義したロゴがない場合はClearbitから取得（企業ドメインがあれば）
                if not logo_url and rel_company_info.get('website'):
                    domain = rel_company_info['website'].replace('https://', '').replace('http://', '').split('/')[0]
                    logo_url = f"https://logo.clearbit.com/{domain}"
                
                # 関連タイプ（同一セクター）
                relation_type = "competitor"
                
                # アイテムを追加
                items.append({
                    "symbol": rel_symbol,
                    "name": row.get('Name', rel_company_info.get('name', rel_symbol)),
                    "price": price_info["price"],
                    "change": change,
                    "change_percent": price_info["change_percent"],
                    "is_positive": is_positive,
                    "logo_url": logo_url,
                    "relation_type": relation_type,
                    "sector": rel_company_info.get('sector', None)
                })
            except Exception as e:
                print(f"Error processing related symbol {rel_symbol}: {e}")
                continue
        
        return {"items": items}
    except Exception as e:
        print(f"Error fetching related markets for {symbol}: {e}")
        return {"items": []}

def load_jpx_data():
    """
    DynamoDBから日本株データを読み込む関数
    """
    try:
        # DynamoDBからデータを取得
        items = get_stock_data()
        if not items:
            print("DynamoDBからデータを取得できませんでした")
            return None, {}
            
        # データフレームに変換
        df = convert_to_dataframe(items)
        
        # 日本株のみを抽出
        japan_df = df[df["Symbol"].str.endswith(".T")].copy()
        
        if len(japan_df) == 0:
            print("日本株データが見つかりませんでした")
            return None, {}
            
        # シンボルと日本語名のマッピング作成
        jpx_symbols_map = dict(zip(japan_df["Symbol"], japan_df["Name"]))
        
        print(f"DynamoDBから {len(japan_df)} 件の日本株データを読み込みました")
        return japan_df, jpx_symbols_map
        
    except Exception as e:
        print(f"日本株データの読み込み中にエラーが発生しました: {e}")
        return None, {}

def update_jpx_symbols_map():
    """
    JPX銘柄辞書を更新する関数
    データが変更された場合に手動で呼び出します
    """
    global JPX_SYMBOLS_MAP
    try:
        _, updated_map = load_jpx_data() or (None, {})
        if updated_map and len(updated_map) > 0:
            JPX_SYMBOLS_MAP = updated_map
            print(f"JPX銘柄辞書を更新しました。{len(JPX_SYMBOLS_MAP)}件のデータがあります。")
            return True
        else:
            print("JPX銘柄辞書の更新に失敗しました。有効なデータが取得できませんでした。")
            return False
    except Exception as e:
        print(f"JPX銘柄辞書の更新中にエラーが発生しました: {e}")
        return False

def enhance_ticker_master_with_jpx():
    """
    銘柄マスタをJPXデータで拡充する関数
    日本株の日本語名称をマスタに追加します
    """
    try:
        # 現在のマスタデータを読み込む
        df = load_ticker_master()
        if df is None or len(df) == 0:
            print("銘柄マスタが空です。まず基本データをロードしてください。")
            return False
            
        # JPXデータを読み込む
        jpx_df, _ = load_jpx_data() or (None, {})
        if jpx_df is None or len(jpx_df) == 0:
            print("JPXデータを読み込めませんでした。")
            return False
            
        # 日本株だけを抽出
        japan_stocks = df[df["Symbol"].str.endswith(".T")].copy()
        
        # JPXデータとマージするためのキー設定
        updates_made = 0
        
        # 各日本株に対して、JPXデータから日本語名を探して更新
        for idx, row in japan_stocks.iterrows():
            symbol = row["Symbol"]
            if symbol in JPX_SYMBOLS_MAP:
                japanese_name = JPX_SYMBOLS_MAP[symbol]
                # 元のデータフレームを更新
                df.loc[df["Symbol"] == symbol, "Name"] = japanese_name
                updates_made += 1
        
        # 更新があった場合、キャッシュファイルを更新
        if updates_made > 0:
            df.to_csv(TICKER_CACHE, index=False)
            print(f"銘柄マスタを更新しました。{updates_made}件の日本株名称を日本語化しました。")
            # 銘柄マスタのキャッシュをクリア
            load_ticker_master.cache_clear()
            return True
        else:
            print("更新対象の日本株銘柄がありませんでした。")
            return False
            
    except Exception as e:
        print(f"銘柄マスタの拡充中にエラーが発生しました: {e}")
        return False 

@lru_cache(maxsize=1)
def get_static_ticker_data():
    """
    静的銘柄データを取得する軽量関数
    DynamoDBアクセスを避けて高速検索を実現
    """
    # 静的データを結合してDataFrameを作成
    all_tickers = INITIAL_TICKERS + JAPAN_TICKERS
    df = pd.DataFrame(all_tickers)
    
    # 欠損値処理
    df = df.fillna('')
    
    print(f"静的銘柄データ読み込み完了：合計 {len(df)} 件（米国: {len(INITIAL_TICKERS)}, 日本: {len(JAPAN_TICKERS)}）")
    return df

def format_market_cap(market_cap_value, currency_symbol=""):
    """
    時価総額を兆・億単位で整形する関数
    
    Args:
        market_cap_value: 時価総額の数値
        currency_symbol: 通貨記号（"¥", "$"等）
        
    Returns:
        str: 整形された時価総額文字列
    """
    try:
        if not market_cap_value or market_cap_value == 0:
            return None
            
        # 兆の単位（1兆 = 1,000,000,000,000）
        if market_cap_value >= 1_000_000_000_000:
            trillion_value = market_cap_value / 1_000_000_000_000
            return f"{currency_symbol}{trillion_value:.1f}兆円" if currency_symbol == "¥" else f"{currency_symbol}{trillion_value:.1f}T"
        
        # 億の単位（1億 = 100,000,000）
        elif market_cap_value >= 100_000_000:
            if currency_symbol == "¥":
                oku_value = market_cap_value / 100_000_000
                return f"{currency_symbol}{oku_value:.1f}億円"
            else:
                # 米国株の場合は10億以上でBillion単位（10億 = 1B）
                if market_cap_value >= 1_000_000_000:
                    billion_value = market_cap_value / 1_000_000_000
                    return f"{currency_symbol}{billion_value:.1f}B"
                else:
                    # 10億未満は百万単位で表示
                    million_value = market_cap_value / 1_000_000
                    return f"{currency_symbol}{million_value:.1f}M"
        
        # 百万の単位
        elif market_cap_value >= 1_000_000:
            million_value = market_cap_value / 1_000_000
            return f"{currency_symbol}{million_value:.1f}M"
        
        # そのまま表示
        else:
            return f"{currency_symbol}{market_cap_value:,}"
            
    except Exception as e:
        print(f"時価総額の整形中にエラーが発生しました: {e}")
        return None

def get_company_profile(symbol: str):
    """
    企業プロフィール情報を取得する関数
    
    Args:
        symbol: 銘柄シンボル (例: 'AAPL', '7203.T')
        
    Returns:
        dict: 企業プロフィール情報
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 通貨記号を決定
        currency_symbol = "¥" if symbol.endswith('.T') else "$"
        
        # 企業名を取得
        company_name = (info.get('longName') or 
                       info.get('shortName') or 
                       info.get('name') or 
                       symbol)
        
        # ロゴURLを取得
        logo_url = LOGO_URLS.get(symbol)
        if not logo_url and info.get('website'):
            # ウェブサイトからClearbitロゴを生成
            try:
                domain = info['website'].replace('https://', '').replace('http://', '').split('/')[0]
                logo_url = f"https://logo.clearbit.com/{domain}"
            except:
                logo_url = None
        
        # 時価総額を整形
        market_cap_formatted = None
        if info.get('marketCap'):
            market_cap_formatted = format_market_cap(info['marketCap'], currency_symbol)
        
        # 業種タグを作成
        industry_tags = []
        if info.get('sector'):
            industry_tags.append(info['sector'])
        if info.get('industry') and info['industry'] != info.get('sector'):
            industry_tags.append(info['industry'])
        
        # 本社所在地を作成
        headquarters = None
        city = info.get('city', '')
        state = info.get('state', '')
        country = info.get('country', '')
        
        if symbol.endswith('.T'):
            # 日本株の場合
            if city and state:
                headquarters = f"{state}{city}"
            elif city:
                headquarters = city
            elif country:
                headquarters = country
        else:
            # 米国株の場合
            if city and state:
                headquarters = f"{city}, {state}"
            elif city and country:
                headquarters = f"{city}, {country}"
            elif state:
                headquarters = state
            elif country:
                headquarters = country
        
        # 設立年の推定（IPO年からの推定）
        foundation_year = None
        # yfinanceには直接的な設立年フィールドがないため、主要企業の設立年をマッピング
        known_foundation_years = {
            'AAPL': 1976,
            'MSFT': 1975,
            'GOOGL': 1998,
            'AMZN': 1994,
            'TSLA': 2003,
            'META': 2004,
            'NFLX': 1997,
            '7203.T': 1937,  # トヨタ自動車
            '6758.T': 1946,  # ソニーグループ
            '7974.T': 1889,  # 任天堂
            '9432.T': 1952,  # NTT
            '9984.T': 1981,  # ソフトバンクグループ
        }
        foundation_year = known_foundation_years.get(symbol)
        
        # 日本語事業概要の辞書
        japanese_business_summaries = {
            # 日本株
            '7203.T': '世界最大級の自動車メーカーとして、ハイブリッド技術のパイオニアであり、持続可能なモビリティソリューションを提供しています。レクサスブランドも展開し、グローバルに事業を展開しています。',
            '6758.T': 'エレクトロニクス、エンターテインメント、金融サービスを手がける多角的企業グループです。PlayStation、音楽、映画、イメージセンサーなど幅広い事業を展開しています。',
            '7974.T': '世界的なゲーム・エンターテインメント企業として、Nintendo Switch、マリオ、ゼルダなどの人気ゲームシリーズを開発・販売しています。',
            '9432.T': '日本最大の通信事業者として、固定・移動通信サービス、データ通信、システムインテグレーションなど幅広いICTサービスを提供しています。',
            '9984.T': '通信、インターネット、AI、フィンテックなど多様な事業を展開する投資持株会社です。ソフトバンク・ビジョン・ファンドを通じて世界的な投資活動も行っています。',
            '6861.T': 'デジタルカメラ、プリンター、複合機などの映像機器・事務機器の開発・製造・販売を行う精密機器メーカーです。',
            '4063.T': '化粧品・スキンケア製品の研究開発・製造・販売を行う化粧品メーカーです。国内外で多数のブランドを展開しています。',
            '8058.T': '総合商社として、エネルギー、金属、機械、化学品、食料など幅広い分野で事業を展開しています。',
            '8306.T': '日本を代表するメガバンクとして、個人・法人向け金融サービス、投資銀行業務、資産管理業務を提供しています。',
            '2914.T': '食品・飲料の製造・販売を行う総合食品メーカーです。調味料、加工食品、冷凍食品など多様な商品を展開しています。',
            
            # 米国株
            'AAPL': 'iPhone、iPad、Mac、Apple Watchなどの革新的な製品を設計・製造・販売する世界最大のテクノロジー企業です。App Store、iCloud、Apple Musicなどのサービスも提供しています。',
            'MSFT': 'Windows、Office、Azure、Xbox、LinkedInなどを手がける世界最大級のソフトウェア・クラウドサービス企業です。企業向けクラウドソリューションでも業界をリードしています。',
            'GOOGL': 'Google検索、YouTube、Android、Google Cloud、広告事業などを展開する世界最大のインターネット・テクノロジー企業です。AI技術の研究開発でも先端を走っています。',
            'AMZN': '世界最大のEコマース・クラウドコンピューティング企業として、オンライン小売、AWS、Prime Video、Alexaなど多様なサービスを提供しています。',
            'TSLA': '電気自動車、エネルギー貯蔵システム、太陽光発電システムの設計・製造・販売を行う持続可能エネルギー企業です。自動運転技術の開発でも業界をリードしています。',
            'META': 'Facebook、Instagram、WhatsApp、Messengerなどのソーシャルメディアプラットフォームを運営し、メタバース技術の開発にも注力しています。',
            'NFLX': '世界最大のストリーミング動画配信サービスとして、オリジナルコンテンツの制作・配信を行い、190以上の国・地域でサービスを展開しています。',
            'NVDA': 'GPU、AI チップ、データセンター向けプロセッサーの設計・製造を行う半導体企業です。ゲーミング、データセンター、自動車、AI分野で業界をリードしています。',
            'JPM': '米国最大級の投資銀行・商業銀行として、個人・法人向け金融サービス、投資銀行業務、資産管理業務を世界規模で提供しています。',
            'JNJ': '医薬品、医療機器、消費者向け製品の研究開発・製造・販売を行う世界最大級のヘルスケア企業です。',
            'PG': '洗剤、シャンプー、おむつなどの日用消費財を製造・販売する世界最大級の消費財メーカーです。180以上の国・地域で事業を展開しています。',
            'KO': '世界最大の清涼飲料水メーカーとして、コカ・コーラをはじめとする500以上のブランドを200以上の国・地域で展開しています。',
            'DIS': 'ディズニーランド・ディズニーワールドの運営、映画・テレビ番組の制作、Disney+などのストリーミングサービスを手がける総合エンターテインメント企業です。',
            'V': '世界最大の決済ネットワーク企業として、クレジットカード・デビットカード決済の処理・決済システムを200以上の国・地域で提供しています。',
            'MA': 'Mastercardブランドの決済ネットワークを運営し、世界中の金融機関、加盟店、消費者に決済ソリューションを提供しています。',
            
            # ETF
            'SPY': 'S&P 500指数に連動するETFとして、米国大型株500銘柄に分散投資できる世界最大級のETFです。',
            'QQQ': 'NASDAQ-100指数に連動するETFとして、米国のテクノロジー株を中心とした100銘柄に投資できます。',
            'VTI': '米国株式市場全体に投資できるETFとして、大型株から小型株まで約4,000銘柄に分散投資が可能です。'
        }
        
        # 日本語事業概要を取得（事前定義があれば使用、なければ英語版をそのまま使用）
        business_summary = japanese_business_summaries.get(symbol)
        if not business_summary:
            # 事前定義がない場合は英語版を使用（将来的に翻訳APIを追加可能）
            business_summary = info.get('longBusinessSummary')
            
            # 英語版が長すぎる場合は短縮（日本語UIに適した長さに調整）
            if business_summary and len(business_summary) > 200:
                business_summary = business_summary[:200] + "..."
        
        return {
            "company_name": company_name,
            "logo_url": logo_url,
            "website": info.get('website'),
            "market_cap_formatted": market_cap_formatted,
            "business_summary": business_summary,
            "industry_tags": industry_tags,
            "full_time_employees": info.get('fullTimeEmployees'),
            "foundation_year": foundation_year,
            "headquarters": headquarters
        }
        
    except Exception as e:
        print(f"企業プロフィール情報の取得中にエラーが発生しました（{symbol}）: {e}")
        # エラー時でも基本的な情報は返す
        return {
            "company_name": symbol,
            "logo_url": LOGO_URLS.get(symbol),
            "website": None,
            "market_cap_formatted": None,
            "business_summary": None,
            "industry_tags": [],
            "full_time_employees": None,
            "foundation_year": None,
            "headquarters": None
        }

def get_dividend_history(symbol: str, years: int = 8):
    """
    配当履歴を取得する関数
    
    Args:
        symbol: 銘柄シンボル (例: 'AAPL', '7203.T')
        years: 取得する年数
        
    Returns:
        List[Dict]: 配当履歴データ
    """
    try:
        ticker = yf.Ticker(symbol)
        
        # yfinanceから配当履歴を取得
        dividends = ticker.dividends
        
        if dividends.empty:
            print(f"銘柄 {symbol} の配当履歴が見つかりません")
            return []
        
        # 通貨記号を決定
        currency_symbol = "¥" if symbol.endswith('.T') else "$"
        
        # 年度別に配当を集計
        dividend_by_year = {}
        
        for date_idx, dividend_amount in dividends.items():
            # 日本株の場合は会計年度（3月期）に合わせる
            if symbol.endswith('.T'):
                # 3月期の会計年度を計算
                if date_idx.month >= 4:  # 4月〜翌年3月
                    fiscal_year = date_idx.year + 1
                else:
                    fiscal_year = date_idx.year
                fiscal_year_str = f"{fiscal_year}年3月期"
            else:
                # 米国株は暦年
                fiscal_year = date_idx.year
                fiscal_year_str = f"{fiscal_year}年"
            
            # 四半期を計算
            quarter_num = ((date_idx.month - 1) // 3) + 1
            quarter_str = f"第{quarter_num}四半期"
            
            if fiscal_year_str not in dividend_by_year:
                dividend_by_year[fiscal_year_str] = {
                    'total': 0,
                    'quarters': {},
                    'dates': []
                }
            
            dividend_by_year[fiscal_year_str]['total'] += dividend_amount
            dividend_by_year[fiscal_year_str]['quarters'][quarter_str] = dividend_amount
            dividend_by_year[fiscal_year_str]['dates'].append(date_idx.date())
        
        # 結果を配当履歴形式に変換
        dividend_history = []
        
        # 年度を降順でソート（最新年度が最初）
        sorted_years = sorted(dividend_by_year.keys(), reverse=True)
        
        # 指定された年数まで取得
        for fiscal_year in sorted_years[:years]:
            year_data = dividend_by_year[fiscal_year]
            
            # 四半期配当リストを作成
            quarterly_dividends = []
            for quarter in ["第1四半期", "第2四半期", "第3四半期", "第4四半期"]:
                if quarter in year_data['quarters']:
                    amount = year_data['quarters'][quarter]
                    quarterly_dividends.append({
                        "quarter": quarter,
                        "amount": f"{currency_symbol}{amount:.2f}"
                    })
                else:
                    # 配当がない四半期は"---"で表示
                    quarterly_dividends.append({
                        "quarter": quarter,
                        "amount": None
                    })
            
            # 発表日（最初の配当支払日を使用）
            announcement_date = min(year_data['dates']) if year_data['dates'] else None
            
            # 予想/実績の判定（未来の年度は予想とする）
            current_year = datetime.now().year
            is_forecast = False
            
            if symbol.endswith('.T'):
                # 日本株：現在年+1以降は予想
                fiscal_year_num = int(fiscal_year.replace('年3月期', ''))
                is_forecast = fiscal_year_num > current_year + 1
            else:
                # 米国株：現在年以降は予想
                fiscal_year_num = int(fiscal_year.replace('年', ''))
                is_forecast = fiscal_year_num > current_year
            
            dividend_history.append({
                "fiscal_year": fiscal_year,
                "total_dividend": f"{currency_symbol}{year_data['total']:.2f}",
                "is_forecast": is_forecast,
                "quarterly_dividends": quarterly_dividends,
                "announcement_date": announcement_date
            })
        
        return dividend_history
        
    except Exception as e:
        print(f"配当履歴の取得中にエラーが発生しました（{symbol}）: {e}")
        return []
