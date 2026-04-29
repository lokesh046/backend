import asyncio
import os
from dotenv import load_dotenv
from huggingface_hub import AsyncInferenceClient

load_dotenv()
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

async def test_hf():
    models = [
        "meta-llama/Llama-3.2-3B-Instruct",
        "Qwen/Qwen2.5-7B-Instruct",
        "Qwen/Qwen2.5-72B-Instruct",
        "mistralai/Mixtral-8x7B-Instruct-v0.1"
    ]
    
    for model in models:
        print(f"Testing {model}...")
        client = AsyncInferenceClient(model=model, token=HF_API_KEY)
        messages = [{"role": "user", "content": "What is the 4% rule in FIRE?"}]
        try:
            resp = await client.chat_completion(messages, max_tokens=100)
            print("Success!")
        except Exception as e:
            print("Failed:", e)
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(test_hf())
