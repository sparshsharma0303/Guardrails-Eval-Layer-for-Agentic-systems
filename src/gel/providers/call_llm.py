import os 
from groq import Groq
from google import genai
# from src.gel.providers import gemini_test,groq_test
from dotenv import load_dotenv
load_dotenv()
from gel.providers.cache_store import conn,compute_cache_key,save_to_cache,get_cached_response
import time


def call_llm(provider:str,model: str, prompt : str) -> str:
    if provider == "mock":
        return prompt
    cache_key = compute_cache_key(provider=provider,model=model,prompt=prompt)
    cached_response = get_cached_response(conn=conn,cache_key=cache_key)
    if cached_response:
        return cached_response
    else:
        if provider =="groq":
            client = Groq(api_key=os.environ["GROQ_API_KEY"])
            response = client.chat.completions.create(
                model=model,
                messages = [{"role": "user", "content": prompt}]
            )
            save_to_cache(conn= conn,model=model,provider=provider,prompt=prompt,response=response.choices[0].message.content)
            return response.choices[0].message.content

        elif provider == "gemini":
            client = genai.Client(api_key = os.environ["GEMINI_API_KEY"])
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            save_to_cache(conn= conn,model=model,provider=provider,prompt=prompt,response=response.text)
            return response.text
        else:
            raise ValueError(f'unkown provider: {provider}')


if __name__ == "__main__":
    start = time.time()
    groq_result = call_llm(provider="groq",prompt= "what is 2+2",model= "openai/gpt-oss-20b")
    end = time.time()
    elapsed = end-start
    # print("GROQ:", groq_result)
    print("GROQ time:", elapsed)

    start = time.time()
    gemini_result = call_llm(provider="gemini", prompt="tell me about india", model="gemini-3.5-flash-lite")
    end = time.time()
    elapsed = end - start
    # print("GEMINI:", gemini_result)
    print("GEMINI time:", elapsed)

    # print("OPENAI:",call_llm("openai", "what's 2 + 2", "miscellanious"))
    start = time.time()
    mock_result = call_llm(provider="mock",prompt= "tell me about india", model="irrelevant-model-name")
    end = time.time()
    elapsed = end-start
    print("MOCK:", mock_result)
    print("MOCK_time:", elapsed)

    start = time.time()
    gemini_result_2 = call_llm(provider="gemini",prompt= "tell me about india", model= "gemini-3.5-flash-lite")
    end = time.time()
    elapsed = end - start
    # print("GEMINI_2:", gemini_result_2)
    print("GEMINI_2 time:", elapsed)