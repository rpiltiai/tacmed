
import boto3
import json
import sys

client = boto3.client('apigatewayv2', region_name='eu-central-1')

def main():
    # 1. Get API ID (Robustly)
    # Reading file first
    try:
        with open('infrastructure_outputs.json', 'r') as f:
            config = json.load(f)
        api_endpoint = config.get('ApiEndpoint', '')
        # https://<id>.execute...
        if 'execute-api' in api_endpoint:
            api_id = api_endpoint.split('//')[1].split('.')[0]
            print(f"Targeting API ID from config: {api_id}")
        else:
            print("Could not parse ApiEndpoint from config")
            sys.exit(1)
    except Exception as e:
        print(f"Error reading config: {e}")
        sys.exit(1)
        
    # 2. Get Integration ID
    resp = client.get_integrations(ApiId=api_id)
    if not resp.get('Items'):
        print("No integrations found!")
        sys.exit(1)
    integration_id = resp['Items'][0]['IntegrationId']
    print(f"Using Integration: {integration_id}")
    
    # 3. Check and Create Routes
    routes = client.get_routes(ApiId=api_id)
    existing_keys = [r['RouteKey'] for r in routes['Items']]
    
    target = f"integrations/{integration_id}"
    
    for method in ['POST', 'OPTIONS']:
        key = f"{method} /score"
        if key in existing_keys:
            print(f"Route {key} exists.")
        else:
            print(f"Creating Route {key}...")
            client.create_route(
                ApiId=api_id,
                RouteKey=key,
                Target=target
            )
            print("Created.")

    # 4. Deploy
    print("Deploying...")
    try:
        client.create_deployment(ApiId=api_id, StageName='$default', Description="Fix missing routes")
        print("Deployed.")
    except Exception as e:
        print(f"Deploy error (might be auto-deploy): {e}")

if __name__ == '__main__':
    main()
