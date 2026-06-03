import urllib.request, json, time, sys
headers = {'Authorization': 'Bearer rnd_0xIMlSdVK3MeyuGAxuc6X8csimml', 'Accept': 'application/json'}
req = urllib.request.Request('https://api.render.com/v1/services/srv-d8ac3sa8qa3s73enggp0/deploys?limit=1', headers=headers)
while True:
    try:
        with urllib.request.urlopen(req) as response:
            deploys = json.loads(response.read().decode())
            status = deploys[0].get('deploy', {}).get('status')
            print(f"Status: {status}")
            if status in ['live', 'build_failed', 'update_failed', 'canceled', 'deactivated']:
                sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(15)
