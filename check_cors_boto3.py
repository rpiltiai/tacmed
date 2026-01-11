
import boto3
import json

client = boto3.client('apigatewayv2', region_name='eu-central-1')

def main():
    # Find API
    apis = client.get_apis()
    for item in apis['Items']:
            print(f"API: {item['Name']} ({item['ApiId']})")
            cors = item.get('CorsConfiguration')
            print(f"CORS_CONFIGURED: {bool(cors)}")
            if cors:
                 print(f"AlignOrigins: {cors.get('AllowOrigins')}")
            
            # Check routes too
            routes = client.get_routes(ApiId=item['ApiId'])
            opts_score = any(r['RouteKey'] == 'OPTIONS /score' for r in routes['Items'])
            print(f"OPTIONS_ROUTE_EXISTS: {opts_score}")
            
            # Default route?
            default_route = any(r['RouteKey'] == '$default' for r in routes['Items'])
            print(f"DEFAULT_ROUTE_EXISTS: {default_route}")

if __name__ == '__main__':
    main()
