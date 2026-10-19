import os 
import time
import groq
from groq import Groq
from google import genai
from google.genai import errors
# from src.gel.providers import gemini_test,groq_test
from gel.providers.cache_store import conn,compute_cache_key,save_to_cache,get_cached_response
from gel.providers.retry import with_retry,RetryableError
from gel.providers.rate_limiter import RateLimitExceededError,check_rate_limit,record_call
from dotenv import load_dotenv
load_dotenv()

def call_llm(provider:str,model: str, prompt : str) -> str:
    if provider == "mock":
        return prompt
    cache_key = compute_cache_key(provider=provider,model=model,prompt=prompt)
    cached_response = get_cached_response(conn=conn,cache_key=cache_key)
    if cached_response:
        return cached_response
    else:
        if provider =="groq":
            check_rate_limit(provider=provider)
            def groq_call():
                client = Groq(api_key=os.environ["GROQ_API_KEY"])
                response = client.chat.completions.create(
                    model=model,
                    messages = [{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
            response = with_retry(groq_call,max_retries=5, base_delay=1, retryable_exceptions=(groq.RateLimitError, groq.InternalServerError, groq.APIConnectionError))
            record_call(provider=provider)
            save_to_cache(conn= conn,model=model,provider=provider,prompt=prompt,response=response)
            return response

        elif provider == "gemini":
            check_rate_limit(provider=provider)
            def gemini_call():
                client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
                try:
                    response = client.models.generate_content(model=model, contents=prompt)
                    return response.text
                except errors.ServerError as e:
                    raise RetryableError(e)
                except errors.ClientError as e:
                    if e.code == 429:
                        raise RetryableError(e)
                    raise
            response = with_retry(gemini_call, max_retries = 5 , base_delay=1,retryable_exceptions=(RetryableError,))
            record_call(provider=provider)
            save_to_cache(conn= conn,model=model,provider=provider,prompt=prompt,response=response)
            return response
        else:
            raise ValueError(f'unkown provider: {provider}')




if __name__ == "__main__":
    start = time.time()
    groq_result = call_llm(provider="groq",prompt= "what are transformers in deep learning",model= "openai/gpt-oss-20b")
    end = time.time()
    elapsed = end-start
    # print("GROQ:", groq_result)
    print("GROQ time:", elapsed)

    start = time.time()
    gemini_result = call_llm(provider="gemini", prompt="what are transformers in deep learning", model="gemini-3.5-flash-lite")
    end = time.time()
    elapsed = end - start
    # print("GEMINI:", gemini_result)
    print("GEMINI time:", elapsed)

    # print("OPENAI:",call_llm("openai", "what's 2 + 2", "miscellanious"))
    start = time.time()
    mock_result = call_llm(provider="mock",prompt= "what are transformers in deep learning", model="irrelevant-model-name")
    end = time.time()
    elapsed = end-start
    print("MOCK:", mock_result)
    print("MOCK_time:", elapsed)

    start = time.time()
    gemini_result_2 = call_llm(provider="gemini",prompt= "what are transformers in deep learning", model= "gemini-3.5-flash-lite")
    end = time.time()
    elapsed = end - start
    # print("GEMINI_2:", gemini_result_2)
    print("GEMINI_2 time:", elapsed)