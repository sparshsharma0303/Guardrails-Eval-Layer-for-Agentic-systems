import time


class RateLimitExceededError(Exception):
    pass

LIMITS = {
    "groq": {"max_calls": 30, "window_seconds": 60},
    "gemini": {"max_calls": 1000, "window_seconds": 86400},
}

call_history = {"groq": [], "gemini": []}

def check_rate_limit(provider, stats=None):
    now = time.time()
    window = LIMITS[provider]["window_seconds"]
    call_history[provider] = [t for t in call_history[provider] if (now - t) < window]
    if len(call_history[provider]) >= LIMITS[provider]["max_calls"]:
        if stats is not None:
            stats["was_rate_limited"] = True
        raise RateLimitExceededError(f"Rate limit exceeded for {provider}")

def record_call(provider:str):
    call_history[provider].append(time.time())

if __name__ == "__main__":
    try:
        for i in range(35):
            check_rate_limit("groq")
            record_call("groq")
        print("Limit never triggered — something's wrong")
    except RateLimitExceededError as e:
        print(f"Correctly raised after {i} calls:", e)