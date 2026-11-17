import uuid
from gel.providers.call_llm import call_llm
from gel.providers import rate_limiter

if __name__ == "__main__":
    prompt = f"Reply with the single word OK. Nonce: {uuid.uuid4()}"  # never seen before
    model = "openai/gpt-oss-20b"

    before = len(rate_limiter.call_history.get("groq", []))
    first = call_llm("groq", model, prompt)
    after_first = len(rate_limiter.call_history.get("groq", []))
    second = call_llm("groq", model, prompt)
    after_second = len(rate_limiter.call_history.get("groq", []))

    assert after_first == before + 1, "first call should hit the provider once"
    assert after_second == after_first, "identical call was re-sent to the provider"
    assert first == second, "cached response differs from original"
    print("cache benchmark passed: 1 real call, identical repeat served from cache")
    