
import requests
import json
import time

# Get endpoint
with open('infrastructure_outputs.json', 'r') as f:
    config = json.load(f)

url = f"{config['ApiEndpoint']}/quiz"

print(f"Testing URL: {url}")

for i in range(1, 4):
    print(f"\nRequest {i}...")
    try:
        resp = requests.post(url, json={})
        print(f"Status: {resp.status_code}")
        data = resp.json()
        # Check if fallback
        if "Fallback" in data.get('question', ''):
            print("RESULT: FALLBACK DETECTED")
        else:
            print("RESULT: SUCCESS (Generated)")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(1)
