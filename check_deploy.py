import urllib.request, json

headers = {'Authorization': 'Bearer rnd_0xIMlSdVK3MeyuGAxuc6X8csimml', 'Accept': 'application/json'}
req = urllib.request.Request('https://api.render.com/v1/services/srv-d8ac3sa8qa3s73enggp0/deploys?limit=3', headers=headers)
with urllib.request.urlopen(req) as response:
    deploys = json.loads(response.read().decode())
    for d in deploys:
        dep = d.get('deploy', {})
        print(f"ID: {dep.get('id')} | Status: {dep.get('status')} | Created: {dep.get('createdAt')} | Finished: {dep.get('finishedAt')}")
