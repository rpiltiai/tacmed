
import json
import boto3
import sys

# Hardcoded API ID based on previous context if file read fails, 
# but let's try to find it first.
client = boto3.client('apigatewayv2', region_name='eu-central-1')

def get_api_id():
    # Try listing
    resp = client.get_apis()
    for item in resp.get('Items', []):
        if item['Name'] == 'TacMed_API':
            return item['ApiId']
    return None

def main():
    api_id = get_api_id()
    if not api_id:
        print("API not found")
        sys.exit(1)
        
    print(f"API ID: {api_id}")
    
    # Get Integration
    resp = client.get_integrations(ApiId=api_id)
    items = resp.get('Items', [])
    if not items:
        print("No integrations found")
        sys.exit(1)
        
    integration_id = items[0]['IntegrationId']
    print(f"Integration ID: {integration_id}")
    
    # Check Route
    route_key = "OPTIONS /score"
    routes = client.get_routes(ApiId=api_id)
    
    exists = False
    for r in routes.get('Items', []):
        if r['RouteKey'] == route_key:
            exists = True
            break
            
    if exists:
        print(f"Route {route_key} already exists.")
        print(f"Creating Route {route_key}...")
        client.create_route(
            ApiId=api_id,
            RouteKey=route_key,
            Target=f"integrations/{integration_id}"
        )
        print("Route created.")
        
    # Deploy
    print("Deploying Changes...")
    try:
        # Check if $default stage exists and has autoDeploy
        stage = client.get_stage(ApiId=api_id, StageName='$default')
        if stage.get('AutoDeploy'):
            print("AutoDeploy is enabled. No manual deployment needed.")
        else:
             desc = f"Manual deploy {datetime.now().isoformat()}"
             client.create_deployment(ApiId=api_id, Description=desc, StageName='$default')
             print("Deployment created.")
    except Exception as e:
        print(f"Deployment might be needed but failed to check/create: {e}")
        # Try creating deployment just in case (if stage check failed)
        try:
             client.create_deployment(ApiId=api_id, StageName='$default', Description="Forced deploy")
             print("Forced deployment created.")
        except:
             pass

if __name__ == '__main__':
    main()
