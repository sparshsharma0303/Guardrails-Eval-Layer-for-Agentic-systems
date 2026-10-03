import os 
from groq import Groq
from google import genai
# from src.gel.providers import gemini_test,groq_test
from dotenv import load_dotenv
load_dotenv()



def call_llm(provider:str,  prompt : str, model: str) -> str:
    if provider =="groq":
        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        response = client.chat.completions.create(
            model=model,
            messages = [{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    elif provider == "gemini":
        client = genai.Client(api_key = os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        return response.text
    elif provider == "mock":
        return prompt
    else:
        raise ValueError(f'unkown provider: {provider}')


if __name__ == "__main__":
    groq_result = call_llm("groq", "what is 2+2", "openai/gpt-oss-20b")
    print("GROQ:", groq_result)

    gemini_result = call_llm("gemini", "what is 2+2", "gemini-3.5-flash-lite")
    print("GEMINI:", gemini_result)

    # print("OPENAI:",call_llm("openai", "what's 2 + 2", "miscellanious"))

    mock_result = call_llm("mock", "what is 2+2", "irrelevant-model-name")
    print("MOCK:", mock_result)

    # determinism check — same input should give identical output
    mock_result_2 = call_llm("mock", "what is 2+2", "irrelevant-model-name")
    print("Deterministic:", mock_result == mock_result_2)