def build_chat_prompt(query, context, personal_data):

    return f"""
You are a financial assistant.

User Question:
{query}

Personal Data (if available):
{personal_data}

Knowledge Base Context:
{context}

Explain clearly in simple language.
Do not calculate new numbers.
Use only given deterministic data.
"""
