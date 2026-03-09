import json
import boto3
import os

def build_api_response(status_code, body):
    """Standardized API response format for API Gateway"""
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }

def get_dynamodb_table(table_name_env_var='SESSIONS_TABLE', default_name='setu-ai-sessions'):
    """Helper to get DynamoDB table resource"""
    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ.get(table_name_env_var, default_name)
    return dynamodb.Table(table_name)