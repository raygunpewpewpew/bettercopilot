import os
import requests

API_KEY = os.environ.get("OPENROUTER_API_KEY")
assert API_KEY, "Set OPENROUTER_API_KEY in environment"

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {"role": "system", "content": "You are an assistant that streams output."},
        {"role": "user", "content": "Stream a 200-word short story about a friendly robot."}
    ],
    "stream": True
}

with requests.post(url, headers=headers, json=payload, stream=True) as r:
    r.raise_for_status()
    # OpenRouter uses SSE-ish streaming; skip lines that begin with ':' (comments)
    for raw_line in r.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.decode() if isinstance(raw_line, bytes) else raw_line
        if line.startswith(":"):
            continue
        # Each event may be JSON; try to parse incremental content
        try:
            import json
            obj = json.loads(line)
            # print partials if present
            if isinstance(obj, dict) and obj.get("type") == "response.delta":
                print(obj.get("delta"), end="", flush=True)
            else:
                print(line)
        except Exception:
            print(line)
