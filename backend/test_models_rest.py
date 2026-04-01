import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("No API key")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
res = requests.get(url)

try:
    data = res.json()
    models = data.get('models', [])
    for m in models:
        name = m.get('name', '')
        if 'gemini' in name:
            print(name)
except Exception as e:
    print(e)
