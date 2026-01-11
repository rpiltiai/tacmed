
import json

try:
    with open('apis.json', 'r') as f:
        data = json.load(f)
        
    for item in data.get('Items', []):
        name = item.get('Name')
        api_id = item.get('ApiId')
        cors = item.get('CorsConfiguration', 'NO_CORS')
        print(f"API: {name} ({api_id})")
        print(f"CORS: {json.dumps(cors, indent=2)}")
except Exception as e:
    print(f"Error: {e}")
