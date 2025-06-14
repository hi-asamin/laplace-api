"""
業界平均PER/PBRデータ管理サービス

このモジュールは主要業界の平均PER/PBRデータを提供します。
データは定期的に更新される静的データベースとして管理されます。
"""

from typing import Dict, Optional
from datetime import datetime

class IndustryAveragesService:
    """業界平均データ管理サービス"""
    
    def __init__(self):
        """業界平均データを初期化"""
        self._industry_data = self._load_industry_averages()
        self._last_updated = "2024-12-01"  # データ更新日
    
    def _load_industry_averages(self) -> Dict[str, Dict]:
        """
        業界平均データを読み込む
        
        Returns:
            Dict: 業界名をキーとした平均データ辞書
        """
        return {
            # 日本株主要業界（日本語業界名）
            "自動車": {
                "average_per": 12.5,
                "average_pbr": 0.8,
                "sample_size": 15,
                "description": "自動車・輸送機器"
            },
            "電機・精密": {
                "average_per": 18.2,
                "average_pbr": 1.2,
                "sample_size": 25,
                "description": "電機・精密機器"
            },
            "銀行": {
                "average_per": 8.5,
                "average_pbr": 0.4,
                "sample_size": 12,
                "description": "銀行業"
            },
            "通信": {
                "average_per": 14.8,
                "average_pbr": 1.1,
                "sample_size": 8,
                "description": "情報・通信業"
            },
            "小売": {
                "average_per": 16.3,
                "average_pbr": 1.5,
                "sample_size": 20,
                "description": "小売業"
            },
            "不動産": {
                "average_per": 11.2,
                "average_pbr": 0.9,
                "sample_size": 18,
                "description": "不動産業"
            },
            "建設": {
                "average_per": 10.8,
                "average_pbr": 0.7,
                "sample_size": 22,
                "description": "建設業"
            },
            "化学": {
                "average_per": 13.5,
                "average_pbr": 1.0,
                "sample_size": 16,
                "description": "化学"
            },
            "医薬品": {
                "average_per": 19.8,
                "average_pbr": 1.8,
                "sample_size": 12,
                "description": "医薬品"
            },
            "食品": {
                "average_per": 15.2,
                "average_pbr": 1.3,
                "sample_size": 14,
                "description": "食品"
            },
            
            # 米国株主要業界（英語業界名）
            "Technology": {
                "average_per": 28.5,
                "average_pbr": 6.2,
                "sample_size": 50,
                "description": "テクノロジー"
            },
            "Healthcare": {
                "average_per": 22.1,
                "average_pbr": 3.8,
                "sample_size": 35,
                "description": "ヘルスケア"
            },
            "Financial Services": {
                "average_per": 13.2,
                "average_pbr": 1.1,
                "sample_size": 40,
                "description": "金融サービス"
            },
            "Consumer Cyclical": {
                "average_per": 19.8,
                "average_pbr": 2.4,
                "sample_size": 30,
                "description": "一般消費財"
            },
            "Communication Services": {
                "average_per": 21.5,
                "average_pbr": 2.9,
                "sample_size": 15,
                "description": "通信サービス"
            },
            "Consumer Defensive": {
                "average_per": 17.3,
                "average_pbr": 2.1,
                "sample_size": 25,
                "description": "生活必需品"
            },
            "Energy": {
                "average_per": 11.8,
                "average_pbr": 1.3,
                "sample_size": 20,
                "description": "エネルギー"
            },
            "Industrials": {
                "average_per": 18.9,
                "average_pbr": 2.8,
                "sample_size": 35,
                "description": "資本財"
            },
            "Basic Materials": {
                "average_per": 14.6,
                "average_pbr": 1.7,
                "sample_size": 18,
                "description": "素材"
            },
            "Real Estate": {
                "average_per": 16.4,
                "average_pbr": 1.2,
                "sample_size": 12,
                "description": "不動産"
            },
            "Utilities": {
                "average_per": 19.2,
                "average_pbr": 1.4,
                "sample_size": 15,
                "description": "公益事業"
            }
        }
    
    def get_industry_averages(self, industry: str) -> Optional[Dict]:
        """
        指定業界の平均データを取得
        
        Args:
            industry: 業界名（日本語または英語）
            
        Returns:
            Dict: 業界平均データ、見つからない場合はNone
        """
        if not industry:
            return None
            
        # 完全一致を試行
        if industry in self._industry_data:
            data = self._industry_data[industry].copy()
            data["industry_name"] = industry
            data["last_updated"] = self._last_updated
            return data
        
        # 部分一致を試行（大文字小文字を無視）
        industry_lower = industry.lower()
        for key, value in self._industry_data.items():
            if (key.lower() == industry_lower or 
                industry_lower in key.lower() or 
                key.lower() in industry_lower):
                data = value.copy()
                data["industry_name"] = key
                data["last_updated"] = self._last_updated
                return data
        
        return None
    
    def get_all_industries(self) -> Dict[str, Dict]:
        """
        全業界の平均データを取得
        
        Returns:
            Dict: 全業界の平均データ
        """
        result = {}
        for industry, data in self._industry_data.items():
            result[industry] = data.copy()
            result[industry]["industry_name"] = industry
            result[industry]["last_updated"] = self._last_updated
        
        return result
    
    def is_supported_industry(self, industry: str) -> bool:
        """
        指定業界がサポートされているかチェック
        
        Args:
            industry: 業界名
            
        Returns:
            bool: サポートされている場合True
        """
        return self.get_industry_averages(industry) is not None

# グローバルインスタンス
industry_averages_service = IndustryAveragesService() 