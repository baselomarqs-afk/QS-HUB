import urllib.request, json, time

headers = {'Authorization': 'Bearer rnd_0xIMlSdVK3MeyuGAxuc6X8csimml', 'Accept': 'application/json', 'Content-Type': 'application/json'}

# Clear build cache and trigger fresh deploy
data = json.dumps({"clearCache": "clear"}).encode()
req = urllib.request.Request('https://api.render.com/v1/services/srv-d8ac3sa8qa3s73enggp0/deploys', data=data, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
        deploy = result.get('deploy', result)
        deploy_id = deploy.get('id', 'unknown')
        print(f"Deploy triggered! ID: {deploy_id}")
        print(f"Status: {deploy.get('status')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Error {e.code}: {body}")
except Exception as e:
    print(f"Error: {e}")
