import os
import requests
import json

API_KEY = os.environ.get("OPENROUTER_API_KEY")
assert API_KEY, "Set OPENROUTER_API_KEY in environment"

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# Request a JSON object matching a small schema
payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {"role": "system", "content": "You are a deterministic JSON generator."},
        {"role": "user", "content": "Return a JSON object with keys: title, summary, and files (array of filenames)."}
    ],
    "response_format": {"type": "json_object"},
    "max_tokens": 400
}

resp = requests.post(url, headers=headers, json=payload)
resp.raise_for_status()
data = resp.json()

text = None
choices = data.get("choices") or []
if choices:
    msg = choices[0].get("message") or {}
    text = msg.get("content") or choices[0].get("text")

print("--- RAW ---")
print(json.dumps(data, indent=2))

print("--- PARSED JSON (if any) ---")
try:
    parsed = json.loads(text)
    print(json.dumps(parsed, indent=2))
except Exception:
    print("Could not parse assistant text as JSON:")
    print(text)
