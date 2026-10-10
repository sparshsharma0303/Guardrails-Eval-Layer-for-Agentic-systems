import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# models = client.models.list()
# for m in models.data:
#     print(m.id)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages = [{"role": "user", "content": "tell me about india"}]
)

if __name__ == "__main__":
    # print(response.__getattribute__)
    print(response.choices[0].message.content)





