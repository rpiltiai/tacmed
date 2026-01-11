
import requests
import json
import time

# Get endpoint
with open('infrastructure_outputs.json', 'r') as f:
    config = json.load(f)

url = config['ApiEndpoint']
leaderboard_url = f"{url}/leaderboard"
score_url = f"{url}/score"

print(f"Testing Leaderboard V2: {leaderboard_url}")

# 1. Fetch Leaderboard (should auto-seed 5 mocks)
print("\n--- Initial Leaderboard (Expect 5 mocks) ---")
try:
    resp = requests.get(leaderboard_url)
    data = resp.json()
    count = len(data.get('leaderboard', []))
    print(f"Status: {resp.status_code}")
    print(f"Count: {count} (Should be 5)")
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error: {e}")

# 2. Update Score
print("\n--- Updating Score for 'TestUserV2' ---")
try:
    resp = requests.post(score_url, json={'userId': 'TestUserV2'})
    print(json.dumps(resp.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

# 3. Fetch Leaderboard Again (Expect 6 items)
print("\n--- Updated Leaderboard (Expect 6 items) ---")
time.sleep(1)
try:
    resp = requests.get(leaderboard_url)
    data = resp.json()
    leaderboard = data.get('leaderboard', [])
    print(f"Count: {len(leaderboard)}")
    print(json.dumps(leaderboard, indent=2))
        
except Exception as e:
    print(f"Error: {e}")
