import json
import urllib.request

with open(".env", "r", encoding="utf-8") as f:
    lines = f.readlines()

env_vars = []
for line in lines:
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if "=" not in line:
        continue
    key, val = line.split("=", 1)
    key = key.strip()
    val = val.strip().strip('"').strip("'")
    
    if key == "APP_BASE_URL":
        val = "https://qshub.online"
        
    env_vars.append((key, val))

headers = {
    'Authorization': 'Bearer rnd_0xIMlSdVK3MeyuGAxuc6X8csimml',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

env_group_id = 'evg-d8a9hfh9rddc739udg80'

for key, val in env_vars:
    url = f'https://api.render.com/v1/env-groups/{env_group_id}/env-vars/{key}'
    req = urllib.request.Request(
        url,
        data=json.dumps({"value": val}).encode('utf-8'),
        headers=headers,
        method='PUT'
    )
    try:
        urllib.request.urlopen(req)
        print(f"Updated {key}")
    except Exception as e:
        print(f"Failed to update {key}:", e)
        if hasattr(e, 'read'):
            print(e.read().decode())
