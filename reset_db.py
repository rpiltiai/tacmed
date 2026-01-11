
import boto3
import time

TABLE_NAME = 'TacMed_Users'
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table(TABLE_NAME)

print(f"Scanning table {TABLE_NAME}...")
try:
    response = table.scan()
    items = response.get('Items', [])
    print(f"Found {len(items)} items to delete.")
    
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={'UserId': item['UserId']})
            
    print("Table cleared.")
except Exception as e:
    print(f"Error clearing table: {e}")
