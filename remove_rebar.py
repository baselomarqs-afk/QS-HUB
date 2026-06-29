import re
import json

with open('engine/item_detection_map.py', 'r', encoding='utf-8') as f:
    text = f.read()

# We'll find each block of item using regex:
# { "key": "...", ... }
# Then we remove it if it contains rebar or formwork or staircase

def replacer(match):
    block = match.group(0)
    # Check if this block should be removed
    key_match = re.search(r'"key"\s*:\s*"([^"]+)"', block)
    if key_match:
        key = key_match.group(1).lower()
        if "rebar" in key or "formwork" in key or "staircase" in key:
            # We return empty string to remove the block
            return ""
    return block

# The regex matches a dict starting with { and ending with }
# We need to match precisely the items inside the "items": [ ... ] array
# Items look like: {\n "key": ... \n },
# We will use a regex that matches {\s*"key": [^{}]+\}
# Wait, some items might have nested braces if there's a typo, but they don't in this file.

new_text = re.sub(r'\{\s*"key"\s*:[^}]+(?:\}|\}[ \t]*,)', replacer, text, flags=re.MULTILINE)

with open('engine/item_detection_map.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Done")
