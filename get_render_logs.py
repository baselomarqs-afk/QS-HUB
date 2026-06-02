import urllib.request, json
import time

headers = {'Authorization': 'Bearer rnd_0xIMlSdVK3MeyuGAxuc6X8csimml', 'Accept': 'application/json'}
# Get latest deploy
req = urllib.request.Request('https://api.render.com/v1/services/srv-d8ac3sa8qa3s73enggp0/deploys?limit=1', headers=headers)
with urllib.request.urlopen(req) as response:
    deploys = json.loads(response.read().decode())
    latest_id = deploys[0]['deploy']['id']

# Get logs for latest deploy
# Wait a bit because logs might take a second to be fully available
print(f"Fetching logs for deploy: {latest_id}")
logs_req = urllib.request.Request(f'https://api.render.com/v1/services/srv-d8ac3sa8qa3s73enggp0/deploys/{latest_id}/logs', headers=headers)
try:
    with urllib.request.urlopen(logs_req) as response:
        logs = response.read().decode()
        print("--- LOGS ---")
        # Render returns text/plain, just print last 50 lines
        lines = logs.split('\n')
        for line in lines[-50:]:
            print(line)
        print("--- END LOGS ---")
except urllib.error.HTTPError as e:
    print(f"Failed to fetch logs: {e.code} - {e.read().decode()}")

