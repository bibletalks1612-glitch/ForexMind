# debug_llm.py -- ForexMind LLM Key Tester
# Tests all Groq keys + other providers
# python debug_llm.py

import os, requests, time
from dotenv import load_dotenv
load_dotenv()

GROQ_KEYS = [
    os.getenv("GROQ_API_KEY",   ""),
    os.getenv("GROQ_API_KEY_1", ""),
    os.getenv("GROQ_API_KEY_2", ""),
    os.getenv("GROQ_API_KEY_3", ""),
    os.getenv("GROQ_API_KEY_4", ""),
]
GROQ_KEYS = list(dict.fromkeys([k.strip() for k in GROQ_KEYS if k.strip()]))

CEREBRAS_KEY   = os.getenv("CEREBRAS_API_KEY",   "")
MISTRAL_KEY    = os.getenv("MISTRAL_API_KEY",     "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY",  "")
PROMPT = "Say HELLO and nothing else."

print("\n" + "="*55)
print("  ForexMind LLM Key Tester")
print("="*55)

def test(name, url, key, model):
    print(f"\n[{name}]  model={model}")
    if not key:
        print("  SKIP -- key not set")
        return
    print(f"  key = {key[:14]}...")
    try:
        r = requests.post(url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role":"user","content": PROMPT}], "max_tokens": 10},
            timeout=20)
        print(f"  status = {r.status_code}")
        if r.status_code == 200:
            print(f"  OK -- {r.json()['choices'][0]['message']['content'].strip()}")
        else:
            print(f"  FAIL -- {r.text[:200]}")
    except Exception as e:
        print(f"  ERROR -- {e}")

# Test each Groq key individually
for i, key in enumerate(GROQ_KEYS, 1):
    test(f"Groq key {i}", "https://api.groq.com/openai/v1/chat/completions",
         key, "llama-3.3-70b-versatile")
    time.sleep(1)

# Test other providers
test("Cerebras",   "https://api.cerebras.ai/v1/chat/completions",  CEREBRAS_KEY,   "llama3.1-8b")
time.sleep(1)
test("Mistral",    "https://api.mistral.ai/v1/chat/completions",    MISTRAL_KEY,    "mistral-large-latest")
time.sleep(1)
test("OpenRouter", "https://openrouter.ai/api/v1/chat/completions", OPENROUTER_KEY, "meta-llama/llama-3.2-3b-instruct:free")

print("\n" + "="*55)
print("  OK = ready   FAIL/SKIP = fix .env")
print("="*55 + "\n")
