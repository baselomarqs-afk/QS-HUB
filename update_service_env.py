import json
import urllib.request

with open(".env", "r", encoding="utf-8") as f:
    lines = f.readlines()

env_dict = {}
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
    env_dict[key] = val

env_vars = [{"key": k, "value": v} for k, v in env_dict.items()]

headers = {
    'Authorization': 'Bearer rnd_0xIMlSdVK3MeyuGAxuc6X8csimml',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

req = urllib.request.Request(
    'https://api.render.com/v1/services/srv-d8ac3sa8qa3s73enggp0/env-vars',
    data=json.dumps(env_vars).encode('utf-8'),
    headers=headers,
    method='PUT'
)

try:
    with urllib.request.urlopen(req) as response:
        print("Render Service Env Vars Updated! Status:", response.status)
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())
