
import boto3
import json

client = boto3.client('apigatewayv2', region_name='eu-central-1')

resp = client.get_apis()
for item in resp['Items']:
    print(f"--- API: {item['Name']} ({item['ApiId']}) ---")
    print(f"Endpoint: {item.get('ApiEndpoint')}")
    routes = client.get_routes(ApiId=item['ApiId'])
    print(f"Routes ({len(routes['Items'])}):")
    for r in routes['Items']:
        print(f"  {r['RouteKey']}")
