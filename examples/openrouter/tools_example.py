import os
import requests
import json

API_KEY = os.environ.get("OPENROUTER_API_KEY")
assert API_KEY, "Set OPENROUTER_API_KEY in environment"

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {"role": "system", "content": "You can call tools: list_files and read_file."},
        {"role": "user", "content": "Return a tool call to list_files with path=/src"}
    ],
    "tools": [
        {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
        }
    ],
    "max_tokens": 200
}

resp = requests.post(url, headers=headers, json=payload)
resp.raise_for_status()
data = resp.json()

print(json.dumps(data, indent=2))
