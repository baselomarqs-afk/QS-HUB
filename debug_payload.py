import json, os, urllib.request

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
        
    env_vars.append({"key": key, "value": val})

render_key = os.environ.get("RENDER_API_KEY")
if not render_key:
    raise SystemExit("Set RENDER_API_KEY env var before running debug_payload.py")
headers = {
    'Authorization': f'Bearer {render_key}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

req_group = urllib.request.Request(
    'https://api.render.com/v1/env-groups/evg-d8a9hfh9rddc739udg80',
    data=json.dumps({
        "name": "qto-env",
        "envVars": env_vars,
        "secretFiles": []
    }).encode('utf-8'),
    headers=headers,
    method='PUT'
)
