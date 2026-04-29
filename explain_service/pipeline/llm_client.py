import os
import hashlib
import json
import re
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from huggingface_hub import AsyncInferenceClient

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

MODEL_NAME = "gemini-2.5-flash"
HF_MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"

LLM_CACHE = {}

async def _fallback_generate(prompt: str, is_raw_text: bool = False) -> str:
    """Fallback to Hugging Face Llama 3.2 if Gemini fails"""
    if not HF_API_KEY:
        raise ValueError("Hugging Face API key not found in environment.")
        
    try:
        client = AsyncInferenceClient(model=HF_MODEL_NAME, token=HF_API_KEY)
        messages = [{"role": "user", "content": prompt}]
        
        response = await client.chat_completion(
            messages, 
            max_tokens=800,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Fallback Model ({HF_MODEL_NAME}) also failed: {str(e)}")
        raise e


async def generate_explanation(prompt: str):
    """
    Calls Gemini and returns structured output compatible with FastAPI response model.
    """
    cache_key = hashlib.sha256(prompt.encode()).hexdigest()

    if cache_key in LLM_CACHE:
        return LLM_CACHE[cache_key]
        
    system_instructions = (
        "You are a professional financial advisor.\n"
        "Return STRICT JSON only with this structure:\n"
        "{\n"
        "  \"summary\": \"string\",\n"
        "  \"reasoning_points\": [\"string\"],\n"
        "  \"risk_note\": \"string\"\n"
        "}"
    )
    
    full_prompt = system_instructions + "\n\nUser Prompt: " + prompt
    raw_output = ""
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = await client.aio.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3
            )
        )
        raw_output = response.text.strip()
    except Exception as e:
        print("Gemini 2.5 failed completely. Falling back to Gemini 1.5...", str(e))
        try:
            raw_output = await _fallback_generate(full_prompt, is_raw_text=False)
        except Exception as fallback_e:
            print("Fallback also failed:", str(fallback_e))
            return _fallback_response()

    if raw_output.startswith("```"):
        raw_output = re.sub(r"^```json", "", raw_output)
        raw_output = re.sub(r"^```", "", raw_output)
        raw_output = re.sub(r"```$", "", raw_output)
        raw_output = raw_output.strip()

    try:
        structured_output = json.loads(raw_output)
    except json.JSONDecodeError:
        print("JSON parse failed. Raw output:", raw_output)
        structured_output = {
            "summary": raw_output,
            "reasoning_points": [],
            "risk_note": ""
        }

    structured_output.setdefault("summary", "")
    structured_output.setdefault("reasoning_points", [])
    structured_output.setdefault("risk_note", "")

    normalized_points = []
    for point in structured_output["reasoning_points"]:
        if isinstance(point, dict):
            key_point = point.get("key_point", "")
            context = point.get("context", "")
            combined = f"{key_point} {context}".strip()
            normalized_points.append(combined)
        else:
            normalized_points.append(str(point))

    structured_output["reasoning_points"] = normalized_points

    if isinstance(structured_output["risk_note"], dict):
        explanation = structured_output["risk_note"].get("explanation", "")
        suggested_action = structured_output["risk_note"].get("suggested_action", "")
        structured_output["risk_note"] = f"{explanation} {suggested_action}".strip()
    else:
        structured_output["risk_note"] = str(structured_output["risk_note"])

    final_output = {
        "summary": str(structured_output["summary"]),
        "reasoning_points": structured_output["reasoning_points"],
        "risk_note": structured_output["risk_note"]
    }

    LLM_CACHE[cache_key] = final_output
    return final_output


def _fallback_response():
    return {
        "summary": "AI explanation temporarily unavailable. Both Primary and Fallback AI models failed.",
        "reasoning_points": [],
        "risk_note": ""
    }


async def generate_raw_text(prompt: str) -> str:
    """
    Calls Gemini and returns raw text output for general Q&A.
    """
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = await client.aio.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print("Gemini 2.5 failed in raw text. Falling back to Gemini 1.5...", str(e))
        try:
            return await _fallback_generate(prompt, is_raw_text=True)
        except Exception as fallback_e:
            print("Fallback also failed:", str(fallback_e))
            return "Sorry, I'm having trouble analyzing the financial documents right now. Both primary and backup AI systems are unavailable."