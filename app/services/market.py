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
import requests
from bs4 import BeautifulSoup
import time
import logging

TICKER_CACHE = Path(__file__).with_suffix(".csv")
JPX_DATA_FILE = Path(__file__).parent / "data.csv"  # .xlsから.csvに変更

# 人気度データ（取引量、時価総額、知名度などを考慮したスコア）
POPULARITY_SCORES = {
    # 米国株（人気順）
    "AAPL": 100, "MSFT": 95, "GOOGL": 90, "AMZN": 88, "TSLA": 85,
    "META": 82, "NVDA": 80, "NFLX": 75, "PYPL": 70, "ADBE": 68,
    "CRM": 65, "ORCL": 62, "IBM": 60, "INTC": 58, "AMD": 55,
    "DIS": 52, "SBUX": 50, "SHOP": 48, "ABNB": 45, "UBER": 42,
    "LYFT": 40, "SNAP": 38, "COIN": 35, "SQ": 32, "ZM": 30,
    "TSM": 28, "PINS": 25, "RBLX": 22, "ARM": 20,
    
    # 米国ETF（人気順）
    "SPY": 100, "QQQ": 95, "VTI": 90, "VOO": 85, "IWM": 80,
    "VEA": 75, "VWO": 70, "GLD": 65, "TLT": 60, "EFA": 55,
    "IEFA": 50, "VTV": 45, "VUG": 40, "VXUS": 35, "BND": 30,
    
    # 米国指数（人気順）
    "^GSPC": 100, "^IXIC": 95, "^DJI": 90, "^RUT": 85, "^VIX": 80,
    "^NDX": 75, "^FTSE": 70, "^GDAXI": 65, "^FCHI": 60,
    
    # 日本株（人気順）
    "7203.T": 100, "6758.T": 95, "7974.T": 90, "7267.T": 85, "6752.T": 80,
    "7751.T": 75, "6501.T": 70, "6701.T": 65, "6702.T": 60, "9433.T": 55,
    "9432.T": 50, "9984.T": 45, "8058.T": 40, "8031.T": 35, "8053.T": 30,
    "2914.T": 28, "4502.T": 25, "6367.T": 22, "9983.T": 20, "4755.T": 18,
    "4689.T": 15, "9201.T": 12, "9202.T": 10, "6902.T": 8, "6645.T": 5,
    
    # 日本指数（人気順）
    "^N225": 100, "^TOPX": 90,
}

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
    # 米国株
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
    
    # 米国ETF
    {"Symbol": "SPY", "Name": "SPDR S&P 500 ETF Trust", "Market": "US"},
    {"Symbol": "QQQ", "Name": "Invesco QQQ Trust", "Market": "US"},
    {"Symbol": "VTI", "Name": "Vanguard Total Stock Market ETF", "Market": "US"},
    {"Symbol": "VOO", "Name": "Vanguard S&P 500 ETF", "Market": "US"},
    {"Symbol": "IWM", "Name": "iShares Russell 2000 ETF", "Market": "US"},
    {"Symbol": "VEA", "Name": "Vanguard FTSE Developed Markets ETF", "Market": "US"},
    {"Symbol": "VWO", "Name": "Vanguard FTSE Emerging Markets ETF", "Market": "US"},
    {"Symbol": "GLD", "Name": "SPDR Gold Shares", "Market": "US"},
    {"Symbol": "TLT", "Name": "iShares 20+ Year Treasury Bond ETF", "Market": "US"},
    {"Symbol": "EFA", "Name": "iShares MSCI EAFE ETF", "Market": "US"},
    
    # 米国指数
    {"Symbol": "^GSPC", "Name": "S&P 500", "Market": "US"},
    {"Symbol": "^IXIC", "Name": "NASDAQ Composite", "Market": "US"},
    {"Symbol": "^DJI", "Name": "Dow Jones Industrial Average", "Market": "US"},
    {"Symbol": "^RUT", "Name": "Russell 2000", "Market": "US"},
    {"Symbol": "^VIX", "Name": "CBOE Volatility Index", "Market": "US"},
    {"Symbol": "^NDX", "Name": "NASDAQ-100", "Market": "US"},
    
    # 日本指数
    {"Symbol": "^N225", "Name": "日経平均株価", "Market": "Japan"},
    {"Symbol": "^TOPX", "Name": "東証株価指数", "Market": "Japan"},
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

# 日本の主要投資信託データ（実際のファンドコードを使用）
JAPAN_MUTUAL_FUNDS = [
    # eMAXIS Slimシリーズ（実際のファンドコード）
    {"Symbol": "03311179", "Name": "eMAXIS Slim 米国株式 (S&P500)", "EnglishName": "eMAXIS Slim US Equity (S&P500)", "Market": "Japan", "Category": "海外株式", "Company": "三菱UFJ国際投信", "YahooCode": "03311179", "nav": 32850, "change": 188, "change_percent": 0.58},
    {"Symbol": "0331418A", "Name": "eMAXIS Slim 全世界株式 (オール・カントリー)", "EnglishName": "eMAXIS Slim All World Equity (All Country)", "Market": "Japan", "Category": "海外株式", "Company": "三菱UFJ国際投信", "YahooCode": "0331418A", "nav": 27500, "change": 188, "change_percent": 0.69},
    {"Symbol": "03312174", "Name": "eMAXIS Slim 先進国株式インデックス", "EnglishName": "eMAXIS Slim Developed Markets Equity Index", "Market": "Japan", "Category": "海外株式", "Company": "三菱UFJ国際投信", "YahooCode": "03312174", "nav": 26890, "change": 145, "change_percent": 0.54},
    {"Symbol": "03312175", "Name": "eMAXIS Slim 新興国株式インデックス", "EnglishName": "eMAXIS Slim Emerging Markets Equity Index", "Market": "Japan", "Category": "海外株式", "Company": "三菱UFJ国際投信", "YahooCode": "03312175", "nav": 21450, "change": 123, "change_percent": 0.58},
    {"Symbol": "03312177", "Name": "eMAXIS Slim 国内株式（TOPIX）", "EnglishName": "eMAXIS Slim Japan Equity (TOPIX)", "Market": "Japan", "Category": "国内株式", "Company": "三菱UFJ国際投信", "YahooCode": "03312177", "nav": 17890, "change": 98, "change_percent": 0.55},
    {"Symbol": "03312176", "Name": "eMAXIS Slim 国内株式（日経平均）", "EnglishName": "eMAXIS Slim Japan Equity (Nikkei 225)", "Market": "Japan", "Category": "国内株式", "Company": "三菱UFJ国際投信", "YahooCode": "03312176", "nav": 19340, "change": 112, "change_percent": 0.58},
    
    # SBI・Vシリーズ（実際のファンドコード）
    {"Symbol": "2020012A", "Name": "SBI・V・S&P500インデックス・ファンド", "EnglishName": "SBI V S&P500 Index Fund", "Market": "Japan", "Category": "海外株式", "Company": "SBIアセットマネジメント", "YahooCode": "2020012A", "nav": 22340, "change": 127, "change_percent": 0.57},
    {"Symbol": "2020011A", "Name": "SBI・V・全米株式インデックス・ファンド", "EnglishName": "SBI V US Total Stock Market Index Fund", "Market": "Japan", "Category": "海外株式", "Company": "SBIアセットマネジメント", "YahooCode": "2020011A", "nav": 18920, "change": 108, "change_percent": 0.57},
    {"Symbol": "2020013A", "Name": "SBI・V・全世界株式インデックス・ファンド", "EnglishName": "SBI V Total World Stock Index Fund", "Market": "Japan", "Category": "海外株式", "Company": "SBIアセットマネジメント", "YahooCode": "2020013A", "nav": 19680, "change": 112, "change_percent": 0.57},
    
    # 楽天シリーズ（実際のファンドコード）
    {"Symbol": "01311187", "Name": "楽天・全米株式インデックス・ファンド", "EnglishName": "Rakuten All America Stock Index Fund", "Market": "Japan", "Category": "海外株式", "Company": "楽天投信投資顧問", "YahooCode": "01311187", "nav": 27890, "change": 159, "change_percent": 0.57},
    {"Symbol": "01311188", "Name": "楽天・全世界株式インデックス・ファンド", "EnglishName": "Rakuten All World Stock Index Fund", "Market": "Japan", "Category": "海外株式", "Company": "楽天投信投資顧問", "YahooCode": "01311188", "nav": 20250, "change": 115, "change_percent": 0.57},
    
    # ニッセイシリーズ（実際のファンドコード）
    {"Symbol": "03131113", "Name": "ニッセイ外国株式インデックスファンド", "EnglishName": "Nissei Foreign Stock Index Fund", "Market": "Japan", "Category": "海外株式", "Company": "ニッセイアセットマネジメント", "YahooCode": "03131113", "nav": 31240, "change": 168, "change_percent": 0.54},
    {"Symbol": "03131114", "Name": "ニッセイTOPIXインデックスファンド", "EnglishName": "Nissei TOPIX Index Fund", "Market": "Japan", "Category": "国内株式", "Company": "ニッセイアセットマネジメント", "YahooCode": "03131114", "nav": 16780, "change": 89, "change_percent": 0.53},
    
    # その他人気ファンド（実際のファンドコード）
    {"Symbol": "09311173", "Name": "セゾン・バンガード・グローバルバランスファンド", "EnglishName": "Saison Vanguard Global Balanced Fund", "Market": "Japan", "Category": "バランス型", "Company": "セゾン投信", "YahooCode": "09311173", "nav": 18450, "change": 78, "change_percent": 0.42},
    {"Symbol": "04311140", "Name": "iFree S&P500インデックス", "EnglishName": "iFree S&P500 Index", "Market": "Japan", "Category": "海外株式", "Company": "大和アセットマネジメント", "YahooCode": "04311140", "nav": 24680, "change": 141, "change_percent": 0.57},
    {"Symbol": "03312181", "Name": "つみたて日本株式（日経平均）", "EnglishName": "Tsumitate Japan Stock (Nikkei 225)", "Market": "Japan", "Category": "国内株式", "Company": "三菱UFJ国際投信", "YahooCode": "03312181", "nav": 17990, "change": 103, "change_percent": 0.58},
]

# セクター別銘柄分類（最適化版用）
SECTOR_STOCKS = {
    # 米国株
    "Technology": [
        {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology'},
        {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'sector': 'Technology'},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Technology'},
        {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Technology'},
        {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'sector': 'Technology'},
        {'symbol': 'ORCL', 'name': 'Oracle Corporation', 'sector': 'Technology'},
        {'symbol': 'IBM', 'name': 'International Business Machines Corporation', 'sector': 'Technology'},
        {'symbol': 'INTC', 'name': 'Intel Corporation', 'sector': 'Technology'},
        {'symbol': 'AMD', 'name': 'Advanced Micro Devices Inc.', 'sector': 'Technology'},
        {'symbol': 'CRM', 'name': 'Salesforce Inc.', 'sector': 'Technology'},
    ],
    "Consumer Cyclical": [
        {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Consumer Cyclical'},
        {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Cyclical'},
        {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'sector': 'Consumer Cyclical'},
        {'symbol': 'DIS', 'name': 'The Walt Disney Company', 'sector': 'Consumer Cyclical'},
        {'symbol': 'SBUX', 'name': 'Starbucks Corporation', 'sector': 'Consumer Cyclical'},
        {'symbol': 'ABNB', 'name': 'Airbnb Inc.', 'sector': 'Consumer Cyclical'},
    ],
    "Financial Services": [
        {'symbol': 'PYPL', 'name': 'PayPal Holdings Inc.', 'sector': 'Financial Services'},
        {'symbol': 'COIN', 'name': 'Coinbase Global Inc.', 'sector': 'Financial Services'},
        {'symbol': 'SQ', 'name': 'Block Inc.', 'sector': 'Financial Services'},
    ],
    
    # 日本株
    "自動車": [
        {'symbol': '7203.T', 'name': 'トヨタ自動車', 'sector': '自動車'},
        {'symbol': '7267.T', 'name': 'ホンダ', 'sector': '自動車'},
        {'symbol': '6902.T', 'name': 'デンソー', 'sector': '自動車'},
    ],
    "電気機器": [
        {'symbol': '6758.T', 'name': 'ソニーグループ', 'sector': '電気機器'},
        {'symbol': '6752.T', 'name': 'パナソニック', 'sector': '電気機器'},
        {'symbol': '7974.T', 'name': '任天堂', 'sector': '電気機器'},
    ],
    "情報・通信業": [
        {'symbol': '9432.T', 'name': '日本電信電話', 'sector': '情報・通信業'},
        {'symbol': '9984.T', 'name': 'ソフトバンクグループ', 'sector': '情報・通信業'},
        {'symbol': '4755.T', 'name': '楽天グループ', 'sector': '情報・通信業'},
    ],
    "商社": [
        {'symbol': '8058.T', 'name': '三菱商事', 'sector': '商社'},
        {'symbol': '8031.T', 'name': '三井物産', 'sector': '商社'},
    ],
    "医薬品": [
        {'symbol': '4502.T', 'name': '武田薬品工業', 'sector': '医薬品'},
    ],
    "小売業": [
        {'symbol': '9983.T', 'name': 'ファーストリテイリング', 'sector': '小売業'},
    ],
    "運輸業": [
        {'symbol': '9201.T', 'name': '日本航空', 'sector': '運輸業'},
        {'symbol': '9202.T', 'name': 'ANAホールディングス', 'sector': '運輸業'},
    ],
}

# キャッシュされた価格データ（最適化版用）
CACHED_PRICES = {
    # 米国株（USD）
    "AAPL": {"price": 227.52, "change_percent": 1.8},
    "MSFT": {"price": 415.26, "change_percent": 0.9},
    "GOOGL": {"price": 178.89, "change_percent": -0.5},
    "AMZN": {"price": 207.09, "change_percent": 2.1},
    "TSLA": {"price": 248.5, "change_percent": -1.2},
    "META": {"price": 555.31, "change_percent": 1.5},
    "NVDA": {"price": 145.89, "change_percent": 3.2},
    "NFLX": {"price": 891.38, "change_percent": -0.4},
    "PYPL": {"price": 86.12, "change_percent": 0.3},
    "ADBE": {"price": 512.78, "change_percent": -0.7},
    "CRM": {"price": 329.45, "change_percent": 1.0},
    "ORCL": {"price": 189.67, "change_percent": 0.5},
    "IBM": {"price": 225.34, "change_percent": -0.2},
    "INTC": {"price": 21.89, "change_percent": 2.3},
    "AMD": {"price": 125.67, "change_percent": 1.8},
    "DIS": {"price": 113.58, "change_percent": -0.6},
    "SBUX": {"price": 97.45, "change_percent": 0.8},
    "ABNB": {"price": 125.78, "change_percent": 1.2},
    "COIN": {"price": 278.9, "change_percent": 4.5},
    "SQ": {"price": 78.23, "change_percent": 2.1},
    
    # 日本株（円）
    "7203.T": {"price": 2891, "change_percent": 0.7},
    "6758.T": {"price": 2855, "change_percent": -0.3},
    "7267.T": {"price": 1489, "change_percent": 1.1},
    "9432.T": {"price": 143.8, "change_percent": 0.2},
    "6752.T": {"price": 1233, "change_percent": -0.8},
    "7974.T": {"price": 6890, "change_percent": 1.5},
    "9984.T": {"price": 9876, "change_percent": -2.1},
    "6902.T": {"price": 8760, "change_percent": 0.9},
    "4502.T": {"price": 4123, "change_percent": -0.5},
    "8058.T": {"price": 3245, "change_percent": 1.3},
    "8031.T": {"price": 4567, "change_percent": 0.6},
    "9983.T": {"price": 32100, "change_percent": 2.8},
    "4755.T": {"price": 1234, "change_percent": -1.5},
    "9201.T": {"price": 2567, "change_percent": 0.4},
    "9202.T": {"price": 3456, "change_percent": -0.7},
    
    # ETF
    "SPY": {"price": 601.45, "change_percent": 0.6},
    "QQQ": {"price": 519.23, "change_percent": 1.1},
    "VTI": {"price": 295.67, "change_percent": 0.4},
    "VOO": {"price": 551.23, "change_percent": 0.5},
    "IWM": {"price": 234.78, "change_percent": 0.9},
    "VEA": {"price": 52.34, "change_percent": 0.3},
    "VWO": {"price": 43.67, "change_percent": 0.8},
    "GLD": {"price": 245.89, "change_percent": -0.2},
    "TLT": {"price": 87.45, "change_percent": -0.6},
    "EFA": {"price": 78.23, "change_percent": 0.1},
}

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
                'asset_type': get_asset_type(symbol),
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
                    'asset_type': get_asset_type(symbol),
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
        
        # タイムアウト回避のため、DynamoDBデータを事前にフィルタリング
        # 日本語クエリの場合、日本株のみに絞り込んで処理時間を短縮
        if any('\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FAF' for char in query):
            # 日本語文字が含まれている場合、日本株のみに絞り込み
            df = df[df['Symbol'].str.endswith('.T')]
            print(f"日本語クエリ検出: 日本株 {len(df)} 件に絞り込み")
        
        # 既存の検索ロジックを実行（フィルタリング済みデータ使用）
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
    DataFrameから検索を実行するヘルパー関数（最適化版）
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
    max_results = limit * 3  # 早期終了のための上限設定
    
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
                    
                    # 早期終了: 十分な結果が得られた場合は処理を停止
                    if len(results) >= max_results:
                        print(f"早期終了: {len(results)}件の結果を取得")
                        break
        except Exception as e:
            print(f"{col}での検索中にエラーが発生しました: {e}")
        
        # 早期終了チェック
        if len(results) >= max_results:
            break
    
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
                "price": round(latest_price, 2),
                "change_percent": round(change_percent, 1),
                "last_updated": utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
    
    # エラーが発生した場合や、データが取得できない場合はランダムな値を返す
    price = round(random.uniform(10, 1000), 2)
    change = round(random.uniform(-5, 5), 1)
    current_utc = datetime.now(timezone.utc)
    
    return {
        "price": price,
        "change_percent": change,
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

def convert_index_symbol(symbol: str) -> str:
    """
    指数シンボルをyfinance形式に変換する関数
    
    Args:
        symbol: ユーザー入力の指数シンボル
        
    Returns:
        str: yfinance形式の指数シンボル
    """
    # 主要指数のシンボル変換マッピング
    index_mapping = {
        # S&P 500
        "SPX": "^GSPC",
        "SP500": "^GSPC", 
        "^SPX": "^GSPC",
        
        # NASDAQ
        "NASDAQ": "^IXIC",
        "NDX": "^NDX",
        "COMP": "^IXIC",
        
        # Dow Jones
        "DJI": "^DJI",
        "DJIA": "^DJI",
        "DOW": "^DJI",
        
        # Russell
        "RUT": "^RUT",
        "RUSSELL2000": "^RUT",
        
        # VIX
        "VIX": "^VIX",
        
        # 日本の指数
        "NIKKEI": "^N225",
        "N225": "^N225",
        "TOPIX": "^TOPX",
        
        # ヨーロッパの指数
        "DAX": "^GDAXI",
        "FTSE": "^FTSE",
        "CAC": "^FCHI",
        
        # アジアの指数
        "HSI": "^HSI",  # ハンセン指数
        "STI": "^STI",  # シンガポール
    }
    
    return index_mapping.get(symbol.upper(), symbol)

def is_index_symbol(symbol: str) -> bool:
    """
    シンボルが指数かどうかを判別する関数
    
    Args:
        symbol: 銘柄シンボル
        
    Returns:
        bool: 指数の場合True
    """
    # 指数シンボル変換を試行
    converted_symbol = convert_index_symbol(symbol)
    
    # 変換されたシンボルが^で始まる場合は指数
    if converted_symbol.startswith('^'):
        return True
    
    # プレフィックスチェック
    if symbol.startswith('^'):
        return True
    
    return False

def is_etf_symbol(symbol: str) -> bool:
    """
    シンボルがETFかどうかを判別する関数
    
    Args:
        symbol: 銘柄シンボル
        
    Returns:
        bool: ETFの場合True
    """
    # 主要ETFのパターン
    etf_patterns = [
        'SPY', 'QQQ', 'IWM', 'VOO', 'VTI', 'VEA', 'VWO', 'GLD', 'TLT', 'EFA',
        'IEFA', 'VTV', 'VUG', 'VXUS', 'BND', 'XLF', 'XLK', 'XLE', 'XLV', 'XLI',
        'XLP', 'XLY', 'XLU', 'XLRE', 'XLB', 'VIG', 'SCHD', 'DGRO', 'HDV', 'NOBL'
    ]
    
    symbol_upper = symbol.upper()
    
    # 主要ETFチェック
    if symbol_upper in etf_patterns:
        return True
    
    # ETFの一般的な命名パターン
    etf_suffixes = ['ETF', 'FUND']
    for suffix in etf_suffixes:
        if symbol_upper.endswith(suffix):
            return True
    
    return False

def is_mutual_fund_symbol(symbol: str) -> bool:
    """
    シンボルが投資信託かどうかを判別する関数
    
    Args:
        symbol: 銘柄シンボル
        
    Returns:
        bool: 投資信託の場合True
    """
    # 定義済み投資信託シンボル（実際のファンドコード）
    mutual_fund_symbols = {fund['Symbol'] for fund in JAPAN_MUTUAL_FUNDS}
    if symbol in mutual_fund_symbols:
        return True
    
    # 日本の投資信託ファンドコードのパターン判定
    # 8桁の英数字（例：0331418A）
    if len(symbol) == 8 and symbol.isalnum():
        return True
    
    # 従来の.MFサフィックス（下位互換性のため）
    if symbol.endswith('.MF'):
        return True
        
    return False



def get_mutual_fund_details(symbol: str):
    """
    投資信託の詳細情報を取得する関数
    
    Args:
        symbol: 投資信託のファンドコード (例: '0331418A')
        
    Returns:
        dict: 投資信託の詳細情報
    """
    try:
        # 投資信託データから情報を取得
        fund_data = None
        for fund in JAPAN_MUTUAL_FUNDS:
            if fund['Symbol'] == symbol:
                fund_data = fund
                break
        
        if not fund_data:
            raise ValueError(f"Fund data not found for symbol: {symbol}")
        
        # 基本情報の構築
        market = "Japan"
        currency = "JPY"
        currency_symbol = "¥"
        
        # リアルタイム基準価額データを取得
        try:
            yahoo_code = fund_data.get('YahooCode', symbol)
            real_time_data = fetch_mutual_fund_real_time_price(yahoo_code)
            
            nav_value = real_time_data["nav"]
            change_value = real_time_data["change"]
            change_percent_value = real_time_data["change_percent"]
            last_updated = real_time_data["last_updated"]
            
            price_message = f"{currency_symbol}{nav_value:,}"
            change_message = f"{'+' if change_value > 0 else ''}{currency_symbol}{change_value}"
            change_percent_message = f"{'+' if change_percent_value > 0 else ''}{change_percent_value:.2f}%"
            is_positive_change = change_percent_value > 0
            
        except Exception as e:
            print(f"リアルタイムデータ取得失敗、静的データを使用: {e}")
            # フォールバック: 静的データを使用
            nav_value = fund_data.get('nav')
            change_value = fund_data.get('change', 0)
            change_percent_value = fund_data.get('change_percent', 0)
            last_updated = "静的データ"
            
            if nav_value:
                price_message = f"{currency_symbol}{nav_value:,}"
                change_message = f"{'+' if change_value > 0 else ''}{currency_symbol}{change_value}"
                change_percent_message = f"{'+' if change_percent_value > 0 else ''}{change_percent_value:.2f}%"
                is_positive_change = change_percent_value > 0
            else:
                price_message = "基準価額データなし"
                change_message = f"{currency_symbol}0"
                change_percent_message = "0.00%"
                is_positive_change = True
                last_updated = "データなし"
        
        # 企業プロフィール情報（投資信託の場合は運用会社情報等）
        company_profile_data = {
            "company_name": fund_data['Name'],
            "logo_url": None,
            "website": None,
            "market_cap_formatted": None,
            "business_summary": f"{fund_data['Category']}に投資する投資信託ファンド（運用会社: {fund_data['Company']}）",
            "industry_tags": [fund_data['Category'], "投資信託"],
            "full_time_employees": None,
            "city": None,
            "state": None,
            "country": "Japan",
            "phone": None,
            "founded_year": None,
        }
        
        # 取引情報（投資信託では利用できない項目が多い）
        trading_info = {
            "previous_close": "データなし",
            "open": "データなし",
            "day_high": "データなし", 
            "day_low": "データなし",
            "volume": "データなし",
            "avg_volume": "データなし",
            "market_cap": "データなし",
            "pe_ratio": None,
            "primary_exchange": "投資信託"
        }
        
        return {
            "symbol": symbol,
            "name": fund_data['Name'],
            "market": market,
            "market_name": "投資信託",
            "price": price_message,
            "change": change_message,
            "change_percent": change_percent_message,
            "is_positive": is_positive_change,
            "currency": currency,
            "logo_url": None,
            "sector": fund_data.get('Category', '投資信託'),
            "industry": "投資信託",
            "description": f"{fund_data['EnglishName']} - {fund_data['Company']}が運用する{fund_data['Category']}ファンド",
            "website": None,
            "trading_info": trading_info,
            "dividend_yield": None,
            "company_profile": company_profile_data,
            "last_updated": last_updated,
            "fund_info": {
                "fund_company": fund_data['Company'],
                "category": fund_data['Category'],
                "yahoo_code": fund_data.get('YahooCode', symbol),
                "note": "基準価額はYahoo Finance Japanからリアルタイム取得。取得失敗時は静的データを表示。"
            }
        }
    except Exception as e:
        print(f"Error fetching mutual fund details for {symbol}: {e}")
        raise ValueError(f"Failed to fetch mutual fund details for {symbol}")

def get_asset_type(symbol: str) -> AssetType:
    """
    シンボルからアセットタイプを判定する関数
    
    Args:
        symbol: 銘柄シンボル
        
    Returns:
        AssetType: 判定されたアセットタイプ
    """
    if is_index_symbol(symbol):
        return AssetType.INDEX
    elif is_etf_symbol(symbol):
        return AssetType.ETF
    elif is_mutual_fund_symbol(symbol):
        return AssetType.MUTUAL_FUND
    else:
        return AssetType.STOCK

def get_market_details(symbol: str):
    """
    銘柄の詳細情報を取得する関数
    
    Args:
        symbol: 銘柄シンボル (例: 'AAPL', '7203.T', '0331418A')
        
    Returns:
        dict: 銘柄の詳細情報
    """
    try:
        # 投資信託の場合は専用処理
        if is_mutual_fund_symbol(symbol):
            return get_mutual_fund_details(symbol)
        
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
            # latest_priceとchange_percentは既に数値として返される
            latest_price_value = float(latest_price)
            change_percent_value = float(change_percent)
            change_value = (latest_price_value * change_percent_value / 100)
            change = f"{'+' if change_percent_value > 0 else ''}{currency_symbol}{change_value:.2f}"
            is_positive = change_percent_value > 0
        except:
            change = f"{currency_symbol}0.00"
            is_positive = False
        
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
            "price": f"{currency_symbol}{latest_price:.2f}",
            "change": change,
            "change_percent": f"{'+' if change_percent_value > 0 else ''}{change_percent:.2f}%",
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
        symbol: 銘柄シンボル (例: 'AAPL', '7203.T', 'SPX')
        period: データ期間 (1D, 1W, 1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y, ALL)
        interval: データ間隔 (1m, 5m, 15m, 30m, 60m, 1D, 1W, 1M)
        
    Returns:
        dict: チャートデータ
    """
    try:
        # 指数シンボルをyfinance形式に変換
        yf_symbol = convert_index_symbol(symbol)
        
        # デバッグ情報（指数の場合のみ）
        if yf_symbol != symbol:
            print(f"Index symbol conversion: {symbol} → {yf_symbol}")
        
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
        
        # データ取得（変換されたシンボルを使用）
        ticker = yf.Ticker(yf_symbol)
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
        # 指数シンボル変換情報を含むエラーメッセージ
        yf_symbol = convert_index_symbol(symbol)
        error_msg = f"Error fetching chart data for {symbol}"
        if yf_symbol != symbol:
            error_msg += f" (converted to {yf_symbol})"
        error_msg += f": {e}"
        print(error_msg)
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

@lru_cache(maxsize=2048)  # キャッシュサイズを増加
def get_related_markets(symbol: str, limit: int = 5, criteria: str = "industry", min_dividend_yield: float = None):
    """
    関連銘柄を取得する最適化版関数
    
    パフォーマンス改善:
    1. 事前定義データによる高速検索
    2. API呼び出し削減
    3. 並行処理の最適化
    """
    try:
        # アセットタイプを判定
        asset_type = get_asset_type(symbol)
        
        # 利回り基準の場合は事前定義データ使用
        if criteria == "dividend_yield":
            return _get_dividend_yield_optimized(symbol, limit, min_dividend_yield)
        
        # 業界基準の場合は最適化版を使用
        related_symbols = []
        
        if asset_type == AssetType.STOCK:
            related_symbols = _get_related_stocks_optimized(symbol, limit)
        elif asset_type == AssetType.ETF:
            related_symbols = _get_related_etfs_optimized(symbol, limit)
        elif asset_type == AssetType.INDEX:
            related_symbols = _get_related_indices_optimized(symbol, limit)
        
        # 結果を制限
        related_symbols = related_symbols[:limit]
        
        # 高速化された価格情報取得
        items = []
        for stock_info in related_symbols:
            rel_symbol = stock_info['symbol']
            
            # 事前定義価格データから取得（高速）
            price_info = CACHED_PRICES.get(rel_symbol)
            if not price_info:
                # キャッシュにない場合のみAPI呼び出し
                try:
                    price_info = get_stock_price(rel_symbol)
                except:
                    price_info = {"price": 0, "change_percent": 0}
            
            # ロゴURLを取得
            logo_url = LOGO_URLS.get(rel_symbol)
            
            # 配当利回り（事前定義から取得）
            dividend_yield = stock_info.get('dividend_yield')
            
            items.append({
                "symbol": rel_symbol,
                "name": stock_info['name'],
                "price": price_info["price"],
                "change_percent": price_info["change_percent"],
                "logo_url": logo_url,
                "dividend_yield": dividend_yield
            })
        
        return {"items": items}
        
    except Exception as e:
        print(f"Error fetching optimized related markets for {symbol}: {e}")
        return {"items": []}

def _get_dividend_yield_optimized(symbol: str, limit: int, min_dividend_yield: float) -> Dict:
    """利回り基準の最適化版"""
    try:
        # 日本株かどうかを判定
        is_japan_stock = symbol.endswith('.T')
        
        # 事前定義された高配当銘柄リスト（配当利回り付き）
        if is_japan_stock:
            # 日本株の高配当銘柄（2024年実績ベース）
            high_dividend_stocks = {
                '8058.T': {'name': '三菱商事', 'yield': 3.87},
                '7203.T': {'name': 'トヨタ自動車', 'yield': 3.72},
                '8306.T': {'name': '三菱UFJ', 'yield': 3.62},
                '9432.T': {'name': 'NTT', 'yield': 3.43},
                '8031.T': {'name': '三井物産', 'yield': 3.20},
                '8316.T': {'name': '三井住友フィナンシャルグループ', 'yield': 3.15},
                '9434.T': {'name': 'ソフトバンク', 'yield': 2.95},
                '8411.T': {'name': 'みずほフィナンシャルグループ', 'yield': 2.85},
                '7267.T': {'name': 'ホンダ', 'yield': 2.75},
                '6752.T': {'name': 'パナソニック', 'yield': 2.65},
                '4502.T': {'name': '武田薬品工業', 'yield': 2.55},
                '9983.T': {'name': 'ファーストリテイリング', 'yield': 2.45},
                '6902.T': {'name': 'デンソー', 'yield': 2.35},
                '7974.T': {'name': '任天堂', 'yield': 2.25},
                '6758.T': {'name': 'ソニーグループ', 'yield': 0.67},
                '9984.T': {'name': 'ソフトバンクグループ', 'yield': 0.53}
            }
        else:
            # 米国株の高配当銘柄（2024年実績ベース）
            high_dividend_stocks = {
                'T': {'name': 'AT&T Inc.', 'yield': 6.85},
                'VZ': {'name': 'Verizon Communications Inc.', 'yield': 6.45},
                'XOM': {'name': 'Exxon Mobil Corporation', 'yield': 5.85},
                'CVX': {'name': 'Chevron Corporation', 'yield': 5.65},
                'IBM': {'name': 'International Business Machines Corporation', 'yield': 5.25},
                'PFE': {'name': 'Pfizer Inc.', 'yield': 4.95},
                'KO': {'name': 'The Coca-Cola Company', 'yield': 4.75},
                'PG': {'name': 'The Procter & Gamble Company', 'yield': 4.55},
                'JNJ': {'name': 'Johnson & Johnson', 'yield': 4.35},
                'MRK': {'name': 'Merck & Co., Inc.', 'yield': 4.15},
                'WBA': {'name': 'Walgreens Boots Alliance', 'yield': 8.78},
                'F': {'name': 'Ford Motor Company', 'yield': 7.19},
                'DOW': {'name': 'Dow Inc.', 'yield': 9.36},
                'LYB': {'name': 'LyondellBasell', 'yield': 9.12},
                'ARE': {'name': 'Alexandria Real Estate Equities', 'yield': 7.32}
            }
        
        # 対象銘柄を除外
        if symbol in high_dividend_stocks:
            del high_dividend_stocks[symbol]
        
        # 指定された利回り率の±0.5%の誤差範囲内の銘柄をフィルタリング
        qualifying_stocks = []
        tolerance = 0.5  # ±0.5%の誤差
        min_range = min_dividend_yield - tolerance
        max_range = min_dividend_yield + tolerance
        
        for stock_symbol, stock_data in high_dividend_stocks.items():
            if min_range <= stock_data['yield'] <= max_range:
                # 価格データを取得
                price_info = CACHED_PRICES.get(stock_symbol, {"price": 0, "change_percent": 0})
                
                qualifying_stocks.append({
                    "symbol": stock_symbol,
                    "name": stock_data['name'],
                    "price": price_info["price"],
                    "change_percent": price_info["change_percent"],
                    "logo_url": LOGO_URLS.get(stock_symbol),
                    "dividend_yield": f"{stock_data['yield']:.2f}%"
                })
        
        # 利回り率の高い順にソート
        qualifying_stocks.sort(key=lambda x: float(x['dividend_yield'].replace('%', '')), reverse=True)
        
        return {"items": qualifying_stocks[:limit]}
        
    except Exception as e:
        print(f"Error getting optimized dividend yield stocks for {symbol}: {e}")
        return {"items": []}

def _get_related_stocks(symbol: str, df: pd.DataFrame, limit: int) -> pd.DataFrame:
    """
    株式の関連銘柄を取得（同じ業界）
    """
    try:
        # 銘柄情報を取得
        company_info = get_company_info(symbol)
        sector = company_info.get('sector')
        market = company_info.get('market')
    except Exception as e:
        print(f"Error getting company info for {symbol}: {e}")
        sector = None
        market = None
    
    # 日本株かどうかを判定
    is_japan_stock = symbol.endswith('.T')
    if not market:
        market = 'Japan' if is_japan_stock else 'US'
    
    # セクター情報に基づいて関連銘柄を検索
    sector_matches = pd.DataFrame()
    
    if 'Sector' in df.columns and sector:
        if is_japan_stock:
            # 日本株の場合は、DataFrameのセクター情報（日本語）を使用
            # まず対象銘柄のDataFrame上のセクター情報を取得
            target_df_info = df[df['Symbol'] == symbol]
            if not target_df_info.empty:
                df_sector = target_df_info.iloc[0]['Sector']
                if market:
                    sector_matches = df[(df['Market'] == market) & 
                                       (df['Sector'] == df_sector) & 
                                       (df['Symbol'] != symbol)]
                else:
                    # 日本の全市場を対象
                    sector_matches = df[df['Symbol'].str.endswith('.T') & 
                                       (df['Sector'] == df_sector) & 
                                       (df['Symbol'] != symbol)]
        else:
            # 米国株の場合は、APIのセクター情報（英語）を使用
            sector_matches = df[(df['Market'] == market) & 
                               (df['Sector'].str.lower() == sector.lower()) & 
                               (df['Symbol'] != symbol)]
    
    # セクター情報がない、または十分な銘柄がない場合は同一市場の人気銘柄で補完
    if len(sector_matches) < limit:
        if is_japan_stock:
            # 日本株の人気銘柄
            popular_japan_stocks = [
                '7203.T', '6758.T', '7974.T', '7267.T', '6752.T', '7751.T', 
                '6501.T', '6701.T', '6702.T', '9433.T', '9432.T', '9984.T'
            ]
            # 対象銘柄を除外
            related_stocks = [s for s in popular_japan_stocks if s != symbol]
            
            # DataFrameから該当する銘柄を抽出
            market_matches = df[df['Symbol'].isin(related_stocks)]
            
            # 見つからない場合は、同一市場の銘柄をランダムに抽出
            if market_matches.empty:
                if market:
                    market_matches = df[(df['Market'] == market) & (df['Symbol'] != symbol)]
                else:
                    market_matches = df[df['Symbol'].str.endswith('.T') & (df['Symbol'] != symbol)]
        else:
            # 米国株の人気銘柄
            popular_us_stocks = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 
                'NFLX', 'PYPL', 'ADBE', 'CRM', 'ORCL', 'IBM', 'INTC', 'AMD'
            ]
            # 対象銘柄を除外
            related_stocks = [s for s in popular_us_stocks if s != symbol]
            
            # DataFrameから該当する銘柄を抽出
            market_matches = df[df['Symbol'].isin(related_stocks)]
            
            # 見つからない場合は、同一市場の銘柄をランダムに抽出
            if market_matches.empty:
                market_matches = df[(df['Market'] == market) & (df['Symbol'] != symbol)]
        
        # セクターマッチと市場マッチを結合
        if sector_matches.empty:
            sector_matches = market_matches
        else:
            # 不足分を市場マッチから追加
            remaining_needed = limit - len(sector_matches)
            if remaining_needed > 0 and not market_matches.empty:
                # 既存のセクターマッチに含まれていない銘柄のみ追加
                existing_symbols = set(sector_matches['Symbol'].tolist())
                additional_matches = market_matches[~market_matches['Symbol'].isin(existing_symbols)]
                if not additional_matches.empty:
                    additional_sample = additional_matches.head(remaining_needed)
                    sector_matches = pd.concat([sector_matches, additional_sample])
    
    return sector_matches

def _get_related_stocks_by_dividend_yield(symbol: str, df: pd.DataFrame, limit: int, min_dividend_yield: float) -> pd.DataFrame:
    """
    利回り率基準で関連銘柄を取得（指定利回り率の±0.5%の誤差範囲内の銘柄を返却）
    事前定義された高配当銘柄リストを使用
    """
    try:
        # 日本株かどうかを判定
        is_japan_stock = symbol.endswith('.T')
        
        # 事前定義された高配当銘柄リスト（配当利回り付き）
        if is_japan_stock:
            # 日本株の高配当銘柄（2024年実績ベース）
            high_dividend_stocks = {
                '8058.T': {'name': '三菱商事', 'yield': 3.87},
                '7203.T': {'name': 'トヨタ自動車', 'yield': 3.72},
                '8306.T': {'name': '三菱UFJ', 'yield': 3.62},
                '9432.T': {'name': 'NTT', 'yield': 3.43},
                '8031.T': {'name': '三井物産', 'yield': 3.20},
                '8316.T': {'name': '三井住友フィナンシャルグループ', 'yield': 3.15},
                '9434.T': {'name': 'ソフトバンク', 'yield': 2.95},
                '8411.T': {'name': 'みずほフィナンシャルグループ', 'yield': 2.85},
                '7267.T': {'name': 'ホンダ', 'yield': 2.75},
                '6752.T': {'name': 'パナソニック', 'yield': 2.65},
                '4502.T': {'name': '武田薬品工業', 'yield': 2.55},
                '9983.T': {'name': 'ファーストリテイリング', 'yield': 2.45},
                '6902.T': {'name': 'デンソー', 'yield': 2.35},
                '7974.T': {'name': '任天堂', 'yield': 2.25},
                '6758.T': {'name': 'ソニーグループ', 'yield': 0.67},
                '9984.T': {'name': 'ソフトバンクグループ', 'yield': 0.53}
            }
        else:
            # 米国株の高配当銘柄（2024年実績ベース）
            high_dividend_stocks = {
                'T': {'name': 'AT&T Inc.', 'yield': 6.85},
                'VZ': {'name': 'Verizon Communications Inc.', 'yield': 6.45},
                'XOM': {'name': 'Exxon Mobil Corporation', 'yield': 5.85},
                'CVX': {'name': 'Chevron Corporation', 'yield': 5.65},
                'IBM': {'name': 'International Business Machines Corporation', 'yield': 5.25},
                'PFE': {'name': 'Pfizer Inc.', 'yield': 4.95},
                'KO': {'name': 'The Coca-Cola Company', 'yield': 4.75},
                'PG': {'name': 'The Procter & Gamble Company', 'yield': 4.55},
                'JNJ': {'name': 'Johnson & Johnson', 'yield': 4.35},
                'MRK': {'name': 'Merck & Co., Inc.', 'yield': 4.15},
                'WBA': {'name': 'Walgreens Boots Alliance', 'yield': 8.78},
                'F': {'name': 'Ford Motor Company', 'yield': 7.19},
                'DOW': {'name': 'Dow Inc.', 'yield': 9.36},
                'LYB': {'name': 'LyondellBasell', 'yield': 9.12},
                'ARE': {'name': 'Alexandria Real Estate Equities', 'yield': 7.32}
            }
        
        # 対象銘柄を除外
        if symbol in high_dividend_stocks:
            del high_dividend_stocks[symbol]
        
        # 指定された利回り率の±0.5%の誤差範囲内の銘柄をフィルタリング
        qualifying_stocks = []
        tolerance = 0.5  # ±0.5%の誤差
        min_range = min_dividend_yield - tolerance
        max_range = min_dividend_yield + tolerance
        
        for stock_symbol, stock_data in high_dividend_stocks.items():
            if min_range <= stock_data['yield'] <= max_range:
                qualifying_stocks.append({
                    'Symbol': stock_symbol,
                    'Name': stock_data['name'],
                    'Market': 'Japan' if stock_symbol.endswith('.T') else 'US',
                    'Sector': '',
                    'dividend_yield': stock_data['yield']
                })
        
        if not qualifying_stocks:
            return pd.DataFrame()
        
        # 利回り率の高い順にソート
        qualifying_df = pd.DataFrame(qualifying_stocks)
        qualifying_df = qualifying_df.sort_values('dividend_yield', ascending=False)
        
        # 結果を制限
        return qualifying_df.head(limit)
        
    except Exception as e:
        print(f"Error getting related stocks by dividend yield for {symbol}: {e}")
        return pd.DataFrame()

def _get_related_etfs(symbol: str, df: pd.DataFrame, limit: int) -> pd.DataFrame:
    """
    ETFの関連銘柄を取得（他のETF）
    """
    # 人気ETFリスト（優先順位付き）
    popular_etfs = [
        'SPY', 'QQQ', 'VTI', 'VOO', 'IWM', 'VEA', 'VWO', 'GLD', 'TLT', 'EFA',
        'IEFA', 'VTV', 'VUG', 'VXUS', 'BND', 'XLF', 'XLK', 'XLE', 'XLV', 'XLI',
        'XLP', 'XLY', 'XLU', 'XLRE', 'XLB', 'VIG', 'SCHD', 'DGRO', 'HDV', 'NOBL'
    ]
    
    # 対象銘柄を除外
    related_etfs = [etf for etf in popular_etfs if etf != symbol.upper()]
    
    # DataFrameから該当するETFを抽出
    etf_matches = df[df['Symbol'].isin(related_etfs)]
    
    # 見つからない場合は、静的データから作成
    if etf_matches.empty or len(etf_matches) < limit:
        # 静的データからETFを作成
        static_etfs = []
        for etf_symbol in related_etfs[:limit * 2]:  # 余裕を持って取得
            static_etfs.append({
                'Symbol': etf_symbol,
                'Name': _get_etf_name(etf_symbol),
                'Market': 'US'
            })
        
        static_df = pd.DataFrame(static_etfs)
        if etf_matches.empty:
            etf_matches = static_df
        else:
            # 既存の結果と結合
            etf_matches = pd.concat([etf_matches, static_df]).drop_duplicates(subset=['Symbol'])
    
    return etf_matches

def _get_etf_name(symbol: str) -> str:
    """ETFの名前を取得"""
    etf_names = {
        'SPY': 'SPDR S&P 500 ETF Trust',
        'QQQ': 'Invesco QQQ Trust',
        'VTI': 'Vanguard Total Stock Market ETF',
        'VOO': 'Vanguard S&P 500 ETF',
        'IWM': 'iShares Russell 2000 ETF',
        'VEA': 'Vanguard FTSE Developed Markets ETF',
        'VWO': 'Vanguard FTSE Emerging Markets ETF',
        'GLD': 'SPDR Gold Shares',
        'TLT': 'iShares 20+ Year Treasury Bond ETF',
        'EFA': 'iShares MSCI EAFE ETF',
        'IEFA': 'iShares Core MSCI EAFE IMI Index ETF',
        'VTV': 'Vanguard Value ETF',
        'VUG': 'Vanguard Growth ETF',
        'VXUS': 'Vanguard Total International Stock ETF',
        'BND': 'Vanguard Total Bond Market ETF',
        'XLF': 'Financial Select Sector SPDR Fund',
        'XLK': 'Technology Select Sector SPDR Fund',
        'XLE': 'Energy Select Sector SPDR Fund',
        'XLV': 'Health Care Select Sector SPDR Fund',
        'XLI': 'Industrial Select Sector SPDR Fund',
        'XLP': 'Consumer Staples Select Sector SPDR Fund',
        'XLY': 'Consumer Discretionary Select Sector SPDR Fund',
        'XLU': 'Utilities Select Sector SPDR Fund',
        'XLRE': 'Real Estate Select Sector SPDR Fund',
        'XLB': 'Materials Select Sector SPDR Fund',
        'VIG': 'Vanguard Dividend Appreciation ETF',
        'SCHD': 'Schwab US Dividend Equity ETF',
        'DGRO': 'iShares Core Dividend Growth ETF',
        'HDV': 'iShares High Dividend ETF',
        'NOBL': 'ProShares S&P 500 Dividend Aristocrats ETF'
    }
    return etf_names.get(symbol, f"{symbol} ETF")

def _get_related_indices(symbol: str, df: pd.DataFrame, limit: int) -> pd.DataFrame:
    """
    指数の関連銘柄を取得（他の指数）
    """
    # 人気指数リスト（優先順位付き）
    popular_indices = [
        '^GSPC', '^IXIC', '^DJI', '^RUT', '^VIX', '^NDX', 
        '^N225', '^TOPX', '^FTSE', '^GDAXI', '^FCHI', '^HSI', '^STI'
    ]
    
    # 対象銘柄を除外
    related_indices = [idx for idx in popular_indices if idx != symbol]
    
    # DataFrameから該当する指数を抽出
    index_matches = df[df['Symbol'].isin(related_indices)]
    
    # 見つからない場合は、静的データから作成
    if index_matches.empty or len(index_matches) < limit:
        # 静的データから指数を作成
        static_indices = []
        for index_symbol in related_indices[:limit * 2]:  # 余裕を持って取得
            static_indices.append({
                'Symbol': index_symbol,
                'Name': _get_index_name(index_symbol),
                'Market': 'Japan' if index_symbol in ['^N225', '^TOPX'] else 'US'
            })
        
        static_df = pd.DataFrame(static_indices)
        if index_matches.empty:
            index_matches = static_df
        else:
            # 既存の結果と結合
            index_matches = pd.concat([index_matches, static_df]).drop_duplicates(subset=['Symbol'])
    
    return index_matches

def _get_index_name(symbol: str) -> str:
    """指数の名前を取得"""
    index_names = {
        '^GSPC': 'S&P 500',
        '^IXIC': 'NASDAQ Composite',
        '^DJI': 'Dow Jones Industrial Average',
        '^RUT': 'Russell 2000',
        '^VIX': 'CBOE Volatility Index',
        '^NDX': 'NASDAQ-100',
        '^N225': '日経平均株価',
        '^TOPX': '東証株価指数',
        '^FTSE': 'FTSE 100',
        '^GDAXI': 'DAX',
        '^FCHI': 'CAC 40',
        '^HSI': 'Hang Seng Index',
        '^STI': 'Straits Times Index'
    }
    return index_names.get(symbol, symbol.replace('^', '') + ' Index')

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
    all_tickers = INITIAL_TICKERS + JAPAN_TICKERS + JAPAN_MUTUAL_FUNDS
    df = pd.DataFrame(all_tickers)
    
    # 欠損値処理
    df = df.fillna('')
    
    print(f"静的銘柄データ読み込み完了：合計 {len(df)} 件（米国: {len(INITIAL_TICKERS)}, 日本株: {len(JAPAN_TICKERS)}, 投資信託: {len(JAPAN_MUTUAL_FUNDS)}）")
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

def get_dividend_history(symbol: str, years: int = None):
    """
    配当履歴を取得する関数
    
    Args:
        symbol: 銘柄シンボル (例: 'AAPL', '7203.T')
        years: 取得する年数（Noneの場合は取得可能な全履歴を取得）
        
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
            # 日本株の場合は会計年度（3月期）に合わせるが、表記はアメリカ株と統一
            if symbol.endswith('.T'):
                # 3月期の会計年度を計算
                if date_idx.month >= 4:  # 4月〜翌年3月
                    fiscal_year = date_idx.year + 1
                else:
                    fiscal_year = date_idx.year
                # アメリカ株と同じ表記にするため、会計年度から1を引く
                display_year = fiscal_year - 1
                fiscal_year_str = f"{display_year}年"
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
        
        # 日本株の場合、現在進行中の会計年度の予想配当データを追加
        if symbol.endswith('.T'):
            current_date = datetime.now()
            
            # 現在の会計年度を計算
            if current_date.month >= 4:  # 4月〜翌年3月
                current_fiscal_year = current_date.year + 1
            else:
                current_fiscal_year = current_date.year
            # アメリカ株と同じ表記にするため、会計年度から1を引く
            display_year = current_fiscal_year - 1
            current_fiscal_year_str = f"{display_year}年"
            
            # 現在の会計年度のデータがない場合、予想データを追加
            if current_fiscal_year_str not in dividend_by_year:
                try:
                    # yfinanceから予想配当を取得
                    info = ticker.info
                    dividend_rate = info.get('dividendRate')
                    
                    if dividend_rate and dividend_rate > 0:
                        # 予想配当データを作成
                        dividend_by_year[current_fiscal_year_str] = {
                            'total': dividend_rate,
                            'quarters': {},  # 四半期予想は空
                            'dates': [],
                            'is_forecast': True  # 予想フラグ
                        }
                        print(f"日本株 {symbol} の {display_year}年 予想配当データを追加: ¥{dividend_rate}")
                except Exception as e:
                    print(f"予想配当データの追加中にエラー: {e}")
        
        # 結果を配当履歴形式に変換
        dividend_history = []
        
        # 年度を降順でソート（最新年度が最初）
        sorted_years = sorted(dividend_by_year.keys(), reverse=True)
        
        # 指定された年数まで取得（yearsがNoneの場合は全履歴を取得）
        years_to_process = sorted_years if years is None else sorted_years[:years]
        for fiscal_year in years_to_process:
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
            
            # 予想/実績の判定
            current_year = datetime.now().year
            is_forecast = False
            
            # 予想フラグが設定されている場合は予想
            if year_data.get('is_forecast', False):
                is_forecast = True
            else:
                # 従来のロジック（日本株もアメリカ株も同じ表記になったため統一）
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

# 高速化のための事前定義された業界データと価格情報
SECTOR_STOCKS = {
    # 米国株 - セクター別分類
    "Technology": [
        {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
        {"symbol": "ADBE", "name": "Adobe Inc.", "sector": "Technology"},
        {"symbol": "CRM", "name": "Salesforce Inc.", "sector": "Technology"},
        {"symbol": "ORCL", "name": "Oracle Corporation", "sector": "Technology"},
        {"symbol": "IBM", "name": "International Business Machines Corporation", "sector": "Technology"},
        {"symbol": "INTC", "name": "Intel Corporation", "sector": "Technology"},
        {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "sector": "Technology"},
    ],
    "Consumer Cyclical": [
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Cyclical"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Cyclical"},
        {"symbol": "DIS", "name": "The Walt Disney Company", "sector": "Consumer Cyclical"},
        {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Consumer Cyclical"},
    ],
    "Communication Services": [
        {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Communication Services"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Communication Services"},
        {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Communication Services"},
    ],
    
    # 日本株 - セクター別分類（日本語）
    "自動車": [
        {"symbol": "7203.T", "name": "トヨタ自動車", "sector": "自動車"},
        {"symbol": "7267.T", "name": "ホンダ", "sector": "自動車"},
        {"symbol": "7201.T", "name": "日産自動車", "sector": "自動車"},
        {"symbol": "7269.T", "name": "スズキ", "sector": "自動車"},
        {"symbol": "7270.T", "name": "SUBARU", "sector": "自動車"},
    ],
    "電気機器": [
        {"symbol": "6758.T", "name": "ソニーグループ", "sector": "電気機器"},
        {"symbol": "6752.T", "name": "パナソニック", "sector": "電気機器"},
        {"symbol": "6501.T", "name": "日立製作所", "sector": "電気機器"},
        {"symbol": "6701.T", "name": "NEC", "sector": "電気機器"},
        {"symbol": "6702.T", "name": "富士通", "sector": "電気機器"},
    ],
    "情報・通信": [
        {"symbol": "9432.T", "name": "日本電信電話", "sector": "情報・通信"},
        {"symbol": "9433.T", "name": "KDDI", "sector": "情報・通信"},
        {"symbol": "9984.T", "name": "ソフトバンクグループ", "sector": "情報・通信"},
        {"symbol": "9434.T", "name": "ソフトバンク", "sector": "情報・通信"},
        {"symbol": "4755.T", "name": "楽天グループ", "sector": "情報・通信"},
    ],
}

# 事前定義された価格データ（キャッシュ代替用）
CACHED_PRICES = {
    # 米国株
    "AAPL": {"price": 225.77, "change_percent": 1.2},
    "MSFT": {"price": 441.58, "change_percent": 0.8},
    "GOOGL": {"price": 186.35, "change_percent": -0.5},
    "AMZN": {"price": 219.25, "change_percent": 2.1},
    "TSLA": {"price": 425.32, "change_percent": -1.3},
    "META": {"price": 598.67, "change_percent": 1.8},
    "NVDA": {"price": 145.89, "change_percent": 3.2},
    "NFLX": {"price": 891.38, "change_percent": -0.4},
    
    # 日本株（円）
    "7203.T": {"price": 2891, "change_percent": 0.7},
    "6758.T": {"price": 2855, "change_percent": -0.3},
    "7267.T": {"price": 1489, "change_percent": 1.1},
    "9432.T": {"price": 143.8, "change_percent": 0.2},
    "6752.T": {"price": 1233, "change_percent": -0.8},
    
    # ETF
    "SPY": {"price": 601.45, "change_percent": 0.6},
    "QQQ": {"price": 519.23, "change_percent": 1.1},
    "VTI": {"price": 295.67, "change_percent": 0.4},
}



def _get_related_stocks_optimized(symbol: str, limit: int) -> List[Dict]:
    """
    最適化された株式関連銘柄取得
    事前定義データを使用して高速化
    """
    try:
        # 日本株かどうかを判定
        is_japan_stock = symbol.endswith('.T')
        
        # 対象銘柄のセクターを特定
        target_sector = None
        
        # 事前定義データから検索
        for sector, stocks in SECTOR_STOCKS.items():
            for stock in stocks:
                if stock['symbol'] == symbol:
                    target_sector = sector
                    break
            if target_sector:
                break
        
        related_stocks = []
        
        if target_sector and target_sector in SECTOR_STOCKS:
            # 同セクターの銘柄を取得（対象銘柄を除く）
            sector_stocks = [
                stock for stock in SECTOR_STOCKS[target_sector] 
                if stock['symbol'] != symbol
            ]
            
            # 人気度順にソート
            sector_stocks.sort(
                key=lambda x: POPULARITY_SCORES.get(x['symbol'], 0), 
                reverse=True
            )
            
            related_stocks.extend(sector_stocks[:limit])
        
        # 不足分を人気銘柄で補完
        if len(related_stocks) < limit:
            if is_japan_stock:
                popular_stocks = [
                    '7203.T', '6758.T', '7974.T', '7267.T', '6752.T', 
                    '9432.T', '9984.T', '8058.T', '4502.T', '9983.T'
                ]
            else:
                popular_stocks = [
                    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 
                    'META', 'NVDA', 'NFLX', 'PYPL', 'ADBE'
                ]
            
            # 既存に含まれていない人気銘柄を追加
            existing_symbols = {stock['symbol'] for stock in related_stocks}
            for popular_symbol in popular_stocks:
                if popular_symbol != symbol and popular_symbol not in existing_symbols:
                    # SECTOR_STOCKSから名前を検索
                    name = popular_symbol
                    for sector_stocks in SECTOR_STOCKS.values():
                        for stock in sector_stocks:
                            if stock['symbol'] == popular_symbol:
                                name = stock['name']
                                break
                    
                    related_stocks.append({
                        'symbol': popular_symbol,
                        'name': name,
                        'sector': ''
                    })
                    
                    if len(related_stocks) >= limit:
                        break
        
        return related_stocks
        
    except Exception as e:
        print(f"Error getting optimized related stocks for {symbol}: {e}")
        return []

def _get_related_etfs_optimized(symbol: str, limit: int) -> List[Dict]:
    """最適化されたETF関連銘柄取得"""
    popular_etfs = [
        {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust'},
        {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust'},
        {'symbol': 'VTI', 'name': 'Vanguard Total Stock Market ETF'},
        {'symbol': 'VOO', 'name': 'Vanguard S&P 500 ETF'},
        {'symbol': 'IWM', 'name': 'iShares Russell 2000 ETF'},
        {'symbol': 'VEA', 'name': 'Vanguard FTSE Developed Markets ETF'},
        {'symbol': 'VWO', 'name': 'Vanguard FTSE Emerging Markets ETF'},
        {'symbol': 'GLD', 'name': 'SPDR Gold Shares'},
        {'symbol': 'TLT', 'name': 'iShares 20+ Year Treasury Bond ETF'},
        {'symbol': 'EFA', 'name': 'iShares MSCI EAFE ETF'},
    ]
    
    # 対象銘柄を除外
    related_etfs = [etf for etf in popular_etfs if etf['symbol'] != symbol.upper()]
    
    return related_etfs[:limit]

def _get_related_indices_optimized(symbol: str, limit: int) -> List[Dict]:
    """最適化された指数関連銘柄取得"""
    popular_indices = [
        {'symbol': '^GSPC', 'name': 'S&P 500'},
        {'symbol': '^IXIC', 'name': 'NASDAQ Composite'},
        {'symbol': '^DJI', 'name': 'Dow Jones Industrial Average'},
        {'symbol': '^RUT', 'name': 'Russell 2000'},
        {'symbol': '^VIX', 'name': 'CBOE Volatility Index'},
        {'symbol': '^NDX', 'name': 'NASDAQ-100'},
        {'symbol': '^N225', 'name': '日経平均株価'},
        {'symbol': '^TOPX', 'name': '東証株価指数'},
        {'symbol': '^FTSE', 'name': 'FTSE 100'},
        {'symbol': '^GDAXI', 'name': 'DAX'},
    ]
    
    # 対象銘柄を除外
    related_indices = [idx for idx in popular_indices if idx['symbol'] != symbol]
    
    return related_indices[:limit]

def fetch_mutual_fund_real_time_price(yahoo_code: str) -> dict:
    """
    Yahoo Finance Japanから投資信託の基準価額をリアルタイムで取得する関数
    
    Args:
        yahoo_code: Yahoo Financeのファンドコード (例: '0331418A')
        
    Returns:
        dict: 基準価額データ（nav, change, change_percent, last_updated）
    """
    try:
        # Yahoo Finance Japan の投資信託ページURL
        url = f"https://finance.yahoo.co.jp/quote/{yahoo_code}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # リクエスト送信
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # HTMLをパース
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 基準価額を取得 (複数のセレクタを試行)
        price_selectors = [
            '[data-test="MUTUAL_FUND_PRICE-value"]',
            '.stoksPrice',
            '#main .time',
            '.fw600 span'
        ]
        
        nav_value = None
        change_value = 0
        change_percent_value = 0
        
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text(strip=True)
                # 数値部分を抽出（円、カンマを除去）
                import re
                price_match = re.search(r'[\d,]+', price_text.replace('円', '').replace(',', ''))
                if price_match:
                    nav_value = int(price_match.group())
                    break
        
        # 前日比変動を取得
        change_selectors = [
            '[data-test="MUTUAL_FUND_CHANGE-value"]',
            '.change span',
            '.stoksChange'
        ]
        
        for selector in change_selectors:
            change_element = soup.select_one(selector)
            if change_element:
                change_text = change_element.get_text(strip=True)
                # 変動値と変動率を抽出
                import re
                # 例: "+115 (+0.57%)" のような形式から抽出
                change_match = re.search(r'([+\-]?\d+)', change_text)
                percent_match = re.search(r'([+\-]?\d+\.?\d*)%', change_text)
                
                if change_match:
                    change_value = int(change_match.group())
                if percent_match:
                    change_percent_value = float(percent_match.group(1))
                break
        
        # データが取得できた場合
        if nav_value is not None:
            return {
                "nav": nav_value,
                "change": change_value,
                "change_percent": change_percent_value,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "Yahoo Finance Japan"
            }
        else:
            raise ValueError("基準価額データが見つかりませんでした")
            
    except Exception as e:
        logging.warning(f"Yahoo Finance Japanからの価格取得に失敗: {yahoo_code}, エラー: {str(e)}")
        # フォールバック: 静的データを使用
        for fund in JAPAN_MUTUAL_FUNDS:
            if fund['Symbol'] == yahoo_code or fund.get('YahooCode') == yahoo_code:
                return {
                    "nav": fund.get('nav', 0),
                    "change": fund.get('change', 0),
                    "change_percent": fund.get('change_percent', 0),
                    "last_updated": "静的データ（リアルタイム取得失敗）",
                    "source": "Static Data"
                }
        
        # ファンドが見つからない場合
        raise ValueError(f"投資信託データが見つかりません: {yahoo_code}")

def get_mutual_fund_price_data(symbol: str):
    """
    投資信託の価格データを取得する関数
    
    Args:
        symbol: 投資信託のファンドコード (例: '0331418A')
        
    Returns:
        dict: 価格データ（price, change_percent）
    """
    try:
        # 投資信託データからYahoo Codeを取得
        yahoo_code = None
        for fund in JAPAN_MUTUAL_FUNDS:
            if fund['Symbol'] == symbol:
                yahoo_code = fund.get('YahooCode', symbol)
                break
        
        if not yahoo_code:
            raise ValueError(f"ファンドが見つかりません: {symbol}")
        
        # リアルタイム価格を取得
        price_data = fetch_mutual_fund_real_time_price(yahoo_code)
        
        return {
            "price": price_data["nav"],
            "change_percent": price_data["change_percent"],
            "last_updated": price_data["last_updated"]
        }
        
    except Exception as e:
        print(f"Error fetching mutual fund price for {symbol}: {e}")
        # フォールバック: 静的データを使用
        for fund in JAPAN_MUTUAL_FUNDS:
            if fund['Symbol'] == symbol:
                nav_value = fund.get('nav')
                change_percent_value = fund.get('change_percent', 0)
                
                if nav_value:
                    return {
                        "price": nav_value,
                        "change_percent": change_percent_value,
                        "last_updated": "静的データ（フォールバック）"
                    }
        
        raise ValueError(f"Failed to fetch mutual fund price for {symbol}")
