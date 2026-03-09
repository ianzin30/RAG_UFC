import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))

# Ensure you have your GROQ_API_KEY set in your environment
url = "https://api.groq.com/openai/v1/models"
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise SystemExit("Missing GROQ_API_KEY. Put it in `.env` or export it in your shell.")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)
payload = response.json()

if "error" in payload:
    print(payload)
else:
    for model in payload.get("data", []):
        model_id = model.get("id")
        if model_id:
            print(model_id)
