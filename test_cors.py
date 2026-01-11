
import requests
import json

try:
    with open('infrastructure_outputs.json', 'r') as f:
        config = json.load(f)

    url = f"{config['ApiEndpoint']}/score"
    print(f"Testing OPTIONS {url}")
    
    resp = requests.options(url, headers={'Origin': 'http://localhost'})
    print(f"Status: {resp.status_code}")
    print("Headers:")
    headers = resp.headers
    print(f"Origin: {headers.get('Access-Control-Allow-Origin', 'MISSING')}")
    print(f"Methods: {headers.get('Access-Control-Allow-Methods', 'MISSING')}")
    print(f"Headers: {headers.get('Access-Control-Allow-Headers', 'MISSING')}")
except Exception as e:
    print(f"Error: {e}")
