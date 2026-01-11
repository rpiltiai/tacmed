
import requests
import json
import time

# Get endpoint
with open('infrastructure_outputs.json', 'r') as f:
    config = json.load(f)

url = config['ApiEndpoint']
leaderboard_url = f"{url}/leaderboard"
score_url = f"{url}/score"

print(f"Testing Leaderboard: {leaderboard_url}")

# 1. Fetch Leaderboard (should auto-seed)
print("\n--- Initial Leaderboard ---")
try:
    resp = requests.get(leaderboard_url)
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error: {e}")

# 2. Update Score
print("\n--- Updating Score for 'TestUser' ---")
try:
    resp = requests.post(score_url, json={'userId': 'TestUser'})
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")

# 3. Fetch Leaderboard Again
print("\n--- Updated Leaderboard ---")
time.sleep(1) # Consistency delay
try:
    resp = requests.get(leaderboard_url)
    data = resp.json()
    leaderboard = data.get('leaderboard', [])
    print(json.dumps(leaderboard, indent=2))
    
    # Validation
    found = False
    for user in leaderboard:
        if user.get('UserId') == 'TestUser':
            found = True
            print(f"\nSUCCESS: TestUser found with score {user.get('TotalScore')}")
    if not found:
        print("\nFAILURE: TestUser not found in leaderboard")
        
except Exception as e:
    print(f"Error: {e}")
