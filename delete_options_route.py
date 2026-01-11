
import boto3
import json
import sys

client = boto3.client('apigatewayv2', region_name='eu-central-1')

def main():
    # 1. Get API ID
    try:
        with open('infrastructure_outputs.json', 'r') as f:
            config = json.load(f)
        api_endpoint = config.get('ApiEndpoint', '')
        if 'execute-api' in api_endpoint:
            api_id = api_endpoint.split('//')[1].split('.')[0]
        else:
            sys.exit(1)
    except:
        sys.exit(1)
        
    # 2. Check Routes
    routes = client.get_routes(ApiId=api_id)
    
    for r in routes['Items']:
        if r['RouteKey'] == 'OPTIONS /score':
            print(f"Deleting conflicting route: {r['RouteKey']} ({r['RouteId']})")
            client.delete_route(ApiId=api_id, RouteId=r['RouteId'])
            
    # 3. Deploy
    print("Deploying...")
    try:
        client.create_deployment(ApiId=api_id, StageName='$default', Description="Fix CORS conflict")
        print("Deployed.")
    except Exception as e:
        print(f"Deploy check: {e}")

if __name__ == '__main__':
    main()
