import os
import sys
from dotenv import load_dotenv

import google.generativeai as genai

def main():
    print("Loading dotenv...", flush=True)
    load_dotenv()
    
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment or .env file.")
        sys.exit(1)
        
    print(f"API key loaded (starts with: {api_key[:10]}...). Configuring genai...", flush=True)
    genai.configure(api_key=api_key)
    
    print("Fetching models...", flush=True)
    try:
        models = genai.list_models()
        available_models = [m.name for m in models]
        print(f"\nSuccessfully fetched {len(available_models)} models:")
        for name in available_models:
            print(f" - {name}")
    except Exception as e:
        print(f"Failed to fetch models: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
