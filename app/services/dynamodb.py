import boto3
from botocore.exceptions import ClientError
import json
from typing import List, Dict, Any, Optional
import pandas as pd
import os
from dotenv import load_dotenv

# .env.localファイルを読み込む
load_dotenv('.env.local')

# 環境変数から設定を取得
aws_region = os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-1')

# DynamoDBクライアントの初期化
dynamodb = boto3.resource('dynamodb', region_name=aws_region)

table = dynamodb.Table('LaplaceMarketData')

def save_stock_data(stock_data: List[Dict[str, Any]]) -> bool:
    """
    株式データをDynamoDBに保存する
    
    Args:
        stock_data: 保存する株式データのリスト
        
    Returns:
        bool: 保存が成功したかどうか
    """
    try:
        with table.batch_writer() as batch:
            for item in stock_data:
                # データをDynamoDBの形式に変換（小文字keyで統一）
                dynamo_item = {
                    'symbol': item.get('symbol') or item.get('Symbol'),  # パーティションキー
                    'name': item.get('name') or item.get('Name', ''),
                    'market': item.get('market') or item.get('Market', 'US'),
                    'sector': item.get('sector') or item.get('Sector', ''),
                    'industry': item.get('industry') or item.get('Industry', ''),
                    'logoUrl': item.get('logoUrl') or item.get('LogoUrl', '')
                }
                batch.put_item(Item=dynamo_item)
        return True
    except Exception as e:
        print(f"Error saving stock data: {e}")
        return False

def get_stock_data(symbol: Optional[str] = None, market: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    株式データをDynamoDBから取得する
    
    Args:
        symbol: 取得する銘柄のシンボル（オプション）
        market: 取得する市場（オプション）
        
    Returns:
        List[Dict[str, Any]]: 取得した株式データのリスト
    """
    try:
        if symbol:
            # 特定の銘柄を取得
            response = table.get_item(Key={'symbol': symbol})
            return [response['Item']] if 'Item' in response else []
        elif market:
            # 特定の市場の銘柄を取得
            response = table.query(
                IndexName='MarketIndex',
                KeyConditionExpression='market = :market',
                ExpressionAttributeValues={':market': market}
            )
            return response.get('Items', [])
        else:
            # 全銘柄を取得
            response = table.scan()
            return response.get('Items', [])
    except ClientError as e:
        print(f"Error getting stock data: {e}")
        return []

def update_stock_data(symbol: str, update_data: Dict[str, Any]) -> bool:
    """
    株式データを更新する
    
    Args:
        symbol: 更新する銘柄のシンボル
        update_data: 更新するデータ
        
    Returns:
        bool: 更新が成功したかどうか
    """
    try:
        # 更新式と属性値を構築
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        for key, value in update_data.items():
            if key != 'symbol':  # symbolは更新できない
                # キー名を小文字に変換
                dynamo_key = key.lower()
                # 予約語をエスケープ
                expression_attribute_names[f"#{dynamo_key}"] = dynamo_key
                update_expression += f"#{dynamo_key} = :{dynamo_key}, "
                expression_attribute_values[f":{dynamo_key}"] = value
        
        update_expression = update_expression.rstrip(", ")
        
        # 更新を実行
        table.update_item(
            Key={'symbol': symbol},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames=expression_attribute_names
        )
        return True
    except ClientError as e:
        print(f"Error updating stock data: {e}")
        return False

def delete_stock_data(symbol: str) -> bool:
    """
    株式データを削除する
    
    Args:
        symbol: 削除する銘柄のシンボル
        
    Returns:
        bool: 削除が成功したかどうか
    """
    try:
        table.delete_item(Key={'symbol': symbol})
        return True
    except ClientError as e:
        print(f"Error deleting stock data: {e}")
        return False

def convert_to_dataframe(items: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    DynamoDBのアイテムをPandas DataFrameに変換する
    
    Args:
        items: DynamoDBから取得したアイテムのリスト
        
    Returns:
        pd.DataFrame: 変換されたDataFrame
    """
    df = pd.DataFrame(items)
    # カラム名を先頭大文字に統一
    df.rename(columns={k: k.capitalize() for k in df.columns}, inplace=True)
    return df 