# chat_service/llm_client.py

import re
import os
import json
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors
from huggingface_hub import AsyncInferenceClient

load_dotenv()

HF_MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

class LLMClient:

    def __init__(self):
        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )
        
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.hf_client = None
        if self.hf_api_key:
            self.hf_client = AsyncInferenceClient(model=HF_MODEL_NAME, token=self.hf_api_key)

    async def _fallback_hf(self, prompt: str, temperature: float = 0.3) -> str:
        """Fallback to Hugging Face Qwen-72B if Gemini fails"""
        if not self.hf_client:
            raise ValueError("Hugging Face API key not found in environment.")
            
        messages = [{"role": "user", "content": prompt}]
        response = await self.hf_client.chat_completion(
            messages, 
            max_tokens=800,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()

    # -------------------------------------------------
    # 1️⃣ Extract JSON (Used by Interpreter)
    # -------------------------------------------------
    async def extract_json(self, prompt: str):
        text = ""
        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0
                )
            )
            text = response.text
        except Exception as e:
            print(f"Gemini failed completely. Falling back to {HF_MODEL_NAME}...", e)
            try:
                text = await self._fallback_hf(prompt, temperature=0.0)
            except Exception as hf_e:
                print(f"Fallback also failed: {hf_e}")
                raise hf_e

        # 🔥 REMOVE markdown code blocks if present
        if text.startswith("```"):
            text = re.sub(r"^```json", "", text)
            text = re.sub(r"^```", "", text)
            text = re.sub(r"```$", "", text)
            text = text.strip()

        # Now safely parse
        return json.loads(text)

    # -------------------------------------------------
    # 2️⃣ Generate Plain Text (Used by Explanation Layer)
    # -------------------------------------------------
    async def generate_text(self, prompt: str):
        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7
                )
            )
            return response.text
        except Exception as e:
            try:
                print(f"Gemini text generation failed. Falling back to {HF_MODEL_NAME}...", e)
                return await self._fallback_hf(prompt, temperature=0.7)
            except Exception as hf_e:
                print(f"Fallback also failed: {hf_e}")
                raise hf_e