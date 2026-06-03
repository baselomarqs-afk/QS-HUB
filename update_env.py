import os
import urllib.request
import json
import re

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
        
    env_vars.append({"envVar": {"key": key, "value": val}})

headers = {
    'Authorization': 'Bearer rnd_0xIMlSdVK3MeyuGAxuc6X8csimml',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

req_service = urllib.request.Request(
    'https://api.render.com/v1/services/srv-d8ac3sa8qa3s73enggp0/env-vars',
    data=json.dumps(env_vars).encode('utf-8'),
    headers=headers,
    method='PUT'
)

req_group = urllib.request.Request(
    'https://api.render.com/v1/env-groups/evg-d8a9hfh9rddc739udg80',
    data=json.dumps({"envVars": [ev["envVar"] for ev in env_vars]}).encode('utf-8'),
    headers=headers,
    method='PATCH'
)

try:
    with urllib.request.urlopen(req_group) as response:
        print("Env Group Update Response:", response.status)
except Exception as e:
    print("Env Group Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())

try:
    with urllib.request.urlopen(req_service) as response:
        print("Web App Env Update Response:", response.status)
except Exception as e:
    print("Web App Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())
