import os
import requests

API_KEY = os.environ.get("OPENROUTER_API_KEY")
assert API_KEY, "Set OPENROUTER_API_KEY in environment"

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "gpt-4o-mini",  # replace with a model you have access to
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a short README for a toy project."}
    ],
    "max_tokens": 200
}

resp = requests.post(url, headers=headers, json=payload)
resp.raise_for_status()
data = resp.json()
print(data.get("id"))
text = None
choices = data.get("choices") or []
if choices:
    msg = choices[0].get("message") or {}
    text = msg.get("content") or choices[0].get("text")

print("--- RESPONSE ---")
print(text)
