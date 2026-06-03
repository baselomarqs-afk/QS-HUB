import urllib.request, json

headers = {
    'Authorization': 'Bearer rnd_0xIMlSdVK3MeyuGAxuc6X8csimml',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

with open('.env', 'r', encoding='utf-8') as f:
    lines = f.readlines()

env_vars_dict = {}
for line in lines:
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k, v = line.split('=', 1)
    k = k.strip()
    v = v.strip().strip('"').strip("'")
    if not k: continue
    env_vars_dict[k] = v

env_vars = [{"key": k, "value": v} for k, v in env_vars_dict.items()]

req = urllib.request.Request(
    'https://api.render.com/v1/services/srv-d8ac3sa8qa3s73enggp0/env-vars',
    data=json.dumps(env_vars).encode('utf-8'),
    headers=headers,
    method='PUT'
)
try:
    with urllib.request.urlopen(req) as res:
        print("Success:", res.read().decode())
except Exception as e:
    print("Error:", e.read().decode() if hasattr(e, 'read') else str(e))
