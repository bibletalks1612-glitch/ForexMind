"""
ForexMind - Multi-Provider LLM Client (FINAL - Rate Limited)
Provider chain:
1. Groq      -- 7-key random rotation (PRIMARY)
2. Cerebras  -- single key fallback
3. Mistral   -- single key fallback
4. OpenRouter-- single key fallback

Features:
- 2-second minimum between ALL API calls (prevents rate limits)
- Random key order for Groq (even load distribution)
- No retries on 429 (immediately moves to next key)
"""

import os
import time
import random
import threading
import requests
from dotenv import load_dotenv

load_dotenv()

# ========== RATE LIMITER (2 seconds between ALL calls) ==========
_last_request_time = 0
_request_lock = threading.Lock()

def rate_limited_request(func):
    """Decorator to ensure minimum 2 seconds between ALL LLM calls."""
    def wrapper(*args, **kwargs):
        global _last_request_time
        with _request_lock:
            now = time.time()
            elapsed = now - _last_request_time
            if elapsed < 2.0:
                time.sleep(2.0 - elapsed)
            _last_request_time = time.time()
        return func(*args, **kwargs)
    return wrapper

# ========== LOAD API KEYS ==========
# Groq: up to 7 keys
_groq_keys_raw = [
    os.getenv("GROQ_API_KEY",   "").strip(),
    os.getenv("GROQ_API_KEY_1", "").strip(),
    os.getenv("GROQ_API_KEY_2", "").strip(),
    os.getenv("GROQ_API_KEY_3", "").strip(),
    os.getenv("GROQ_API_KEY_4", "").strip(),
    os.getenv("GROQ_API_KEY_5", "").strip(),
    os.getenv("GROQ_API_KEY_6", "").strip(),
    os.getenv("GROQ_API_KEY_7", "").strip(),
]
GROQ_KEYS = [k for k in _groq_keys_raw if k]  # remove empty ones

# Other providers
CEREBRAS_KEY   = os.getenv("CEREBRAS_API_KEY",   "").strip()
MISTRAL_KEY    = os.getenv("MISTRAL_API_KEY",    "").strip()
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

# ========== SETTINGS ==========
MAX_TOKENS     = 2048
TEMPERATURE    = 0.3
RETRY_ATTEMPTS = 1  # Only 1 attempt per key – move fast

# ========== API ENDPOINTS ==========
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL   = "https://api.cerebras.ai/v1/chat/completions"
MISTRAL_URL    = "https://api.mistral.ai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ========== MODEL NAMES ==========
GROQ_MODEL       = "llama-3.3-70b-versatile"
CEREBRAS_MODEL   = "llama3.1-8b"
MISTRAL_MODEL    = "mistral-large-latest"
OPENROUTER_MODEL = "meta-llama/llama-3.2-3b-instruct:free"


class GroqClient:
    def __init__(self):
        print("  [LLM] Provider chain:")
        if GROQ_KEYS:
            print(f"    OK Groq ({len(GROQ_KEYS)} keys, random order, rate-limited) -- PRIMARY")
        else:
            print("    -- Groq -- no keys (add GROQ_API_KEY_1..7)")
        if CEREBRAS_KEY:
            print("    OK Cerebras -- FALLBACK 1")
        else:
            print("    -- Cerebras -- key missing")
        if MISTRAL_KEY:
            print("    OK Mistral -- FALLBACK 2")
        else:
            print("    -- Mistral -- key missing")
        if OPENROUTER_KEY:
            print("    OK OpenRouter -- FALLBACK 3")
        else:
            print("    -- OpenRouter -- key missing")

    # ========== PUBLIC INTERFACE ==========
    def call(self, prompt, system=None, max_tokens=MAX_TOKENS):
        return self._chain([{"role": "user", "content": prompt}], system, max_tokens)

    def chat(self, messages, system=None, max_tokens=MAX_TOKENS):
        return self._chain(messages, system, max_tokens)

    def quick(self, prompt, system=""):
        return self.call(prompt, system)

    # ========== CORE CHAIN WITH FALLBACK ==========
    def _chain(self, messages, system=None, max_tokens=MAX_TOKENS):
        providers = []
        if GROQ_KEYS:
            providers.append(("Groq", self._groq))
        if CEREBRAS_KEY:
            providers.append(("Cerebras", self._cerebras))
        if MISTRAL_KEY:
            providers.append(("Mistral", self._mistral))
        if OPENROUTER_KEY:
            providers.append(("OpenRouter", self._openrouter))

        if not providers:
            return "[ERROR] No LLM API keys configured in .env!"

        for name, func in providers:
            try:
                result = func(messages, system, max_tokens)
                if result and not result.startswith("Error:") and not result.startswith("[ERROR]"):
                    return result
                print(f"  [LLM] {name} failed -- {result[:70] if result else 'None'} -- trying next...")
            except Exception as e:
                print(f"  [LLM] {name} exception: {str(e)[:70]} -- trying next...")

        return "Analysis unavailable -- all providers exhausted."

    # ========== HELPER: BUILD MESSAGES ==========
    def _build(self, messages, system):
        full = []
        if system:
            full.append({"role": "system", "content": system})
        full.extend(messages)
        return full

    # ========== GENERIC POST REQUEST (SINGLE ATTEMPT) ==========
    def _post(self, url, headers, payload, name):
        """Single attempt – no retries. Rate-limited by decorator."""
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            elif r.status_code == 429:
                return "rate_limited"
            elif r.status_code in (401, 403):
                return f"Error: {name} {r.status_code} -- auth failed"
            elif r.status_code == 402:
                return f"Error: {name} 402 -- no credits"
            else:
                return f"Error: {name} HTTP {r.status_code}"
        except requests.exceptions.Timeout:
            return f"Error: {name} timeout"
        except Exception as e:
            return f"Error: {name} -- {str(e)}"

    # ========== GROQ (7 keys, random order) ==========
    @rate_limited_request
    def _groq(self, messages, system, max_tokens):
        if not GROQ_KEYS:
            return "Error: No Groq keys"

        # Random order for even load distribution
        keys = GROQ_KEYS.copy()
        random.shuffle(keys)

        for idx, key in enumerate(keys):
            result = self._post(
                GROQ_URL,
                {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                {"model": GROQ_MODEL,
                 "messages": self._build(messages, system),
                 "max_tokens": max_tokens,
                 "temperature": TEMPERATURE},
                f"Groq[key{idx+1}]"
            )
            if result == "rate_limited":
                continue  # Try next key immediately
            if result and not result.startswith("Error:"):
                return result
            print(f"  [LLM] Groq key {idx+1} failed -- rotating...")

        return "Error: All Groq keys exhausted"

    # ========== CEREBRAS (fallback 1) ==========
    @rate_limited_request
    def _cerebras(self, messages, system, max_tokens):
        if not CEREBRAS_KEY:
            return "Error: No Cerebras key"

        result = self._post(
            CEREBRAS_URL,
            {"Authorization": f"Bearer {CEREBRAS_KEY}", "Content-Type": "application/json"},
            {"model": CEREBRAS_MODEL,
             "messages": self._build(messages, system),
             "max_tokens": max_tokens,
             "temperature": TEMPERATURE},
            "Cerebras"
        )
        return result

    # ========== MISTRAL (fallback 2) ==========
    @rate_limited_request
    def _mistral(self, messages, system, max_tokens):
        if not MISTRAL_KEY:
            return "Error: No Mistral key"

        result = self._post(
            MISTRAL_URL,
            {"Authorization": f"Bearer {MISTRAL_KEY}", "Content-Type": "application/json"},
            {"model": MISTRAL_MODEL,
             "messages": self._build(messages, system),
             "max_tokens": max_tokens,
             "temperature": TEMPERATURE},
            "Mistral"
        )
        return result

    # ========== OPENROUTER (fallback 3) ==========
    @rate_limited_request
    def _openrouter(self, messages, system, max_tokens):
        if not OPENROUTER_KEY:
            return "Error: No OpenRouter key"

        result = self._post(
            OPENROUTER_URL,
            {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
            {"model": OPENROUTER_MODEL,
             "messages": self._build(messages, system),
             "max_tokens": max_tokens,
             "temperature": TEMPERATURE},
            "OpenRouter"
        )
        return result


# ========== SINGLETON ==========
_client = None

def get_llm():
    global _client
    if _client is None:
        _client = GroqClient()
    return _client