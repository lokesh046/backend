# chat_service/financial_interpreter.py

import re
import json


class FinancialInterpreter:

    def __init__(self, llm_client):
        self.llm = llm_client

    # -------------------------------------------------
    # WORD → NUMBER CONVERTER (SAFE VERSION)
    # -------------------------------------------------
    def word_to_number(self, text: str):

        number_words = {
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
            "ten": 10, "eleven": 11, "twelve": 12,
            "twenty": 20, "thirty": 30, "forty": 40,
            "fifty": 50, "sixty": 60, "seventy": 70,
            "eighty": 80, "ninety": 90
        }

        multipliers = {
            "hundred": 100,
            "thousand": 1000,
            "lakh": 100000,
            "lakhs": 100000
        }

        words = text.lower().split()

        total = 0
        current = 0

        for word in words:
            if word in number_words:
                current += number_words[word]
            elif word in multipliers:
                current = max(1, current) * multipliers[word]
                total += current
                current = 0
            else:
                # stop at unrelated words
                break

        total += current
        return total if total > 0 else None

    # -------------------------------------------------
    # SAFE NUMBER EXTRACTION
    # -------------------------------------------------
    def extract_number_phrase(self, pattern, message):
        match = re.search(pattern, message, re.IGNORECASE)
        if not match:
            return None

        value = match.group(1).strip()

        # If numeric
        if re.fullmatch(r"\d+", value):
            return float(value)

        # If word-number
        return self.word_to_number(value)

    # -------------------------------------------------
    # MAIN EXTRACTION
    # -------------------------------------------------
    async def extract(self, message: str, history: list = None):

        # -----------------------------
        # Improved patterns
        # -----------------------------

        income_pattern = r"(?:earn|salary|take home|income).*?([a-zA-Z\s]+?\s?(?:thousand|lakh|lakhs|\d+))"
        expense_pattern = r"(?:spend|expense|bills|goes for|expenses).*?([a-zA-Z\s]+?\s?(?:thousand|lakh|lakhs|\d+))"
        savings_pattern = r"(?:saving|savings|put aside|aside).*?([a-zA-Z\s]+?\s?(?:thousand|lakh|lakhs|\d+))"
        emi_pattern = r"(?:emi|loan payment|installment).*?([a-zA-Z\s]+?\s?(?:thousand|lakh|lakhs|\d+))"
        years_pattern = r"(?:for|another).*?([a-zA-Z\s]+?)\s+(?:years|yrs)"

        data = {
            "monthly_income": self.extract_number_phrase(income_pattern, message),
            "living_expense": self.extract_number_phrase(expense_pattern, message),
            "current_savings": self.extract_number_phrase(savings_pattern, message),
            "loan_emi": self.extract_number_phrase(emi_pattern, message),
            "loan_years": self.extract_number_phrase(years_pattern, message),
            "loan_amount": None,
            "loan_interest_rate": None,
            "return_rate": None,
            "inflation_rate": None,
        }
        
        # Check loan negations
        if re.search(r"(no loan|0 loan|zero loan|don't have a loan)", message, re.IGNORECASE):
            data["has_loan"] = "no"

        # -----------------------------
        # LLM fallback if needed
        # -----------------------------
        missing = [k for k, v in data.items() if v is None]

        if len(missing) >= 2:
            
            history_context = ""
            if history:
                # Include the last 4 exchanges to give the LLM context of what was just asked
                recent_history = history[-4:]
                history_context = "Recent Conversation Context:\n" + "\n".join([f"{h.get('role', 'unknown')}: {h.get('content', '')}" for h in recent_history])

            prompt = f"""
            Extract structured financial data from the user's latest message. Use the Conversation Context to understand what they are answering if their latest message is just a number.

            Convert words to numbers:
            - sixty thousand → 60000
            - two lakhs → 200000
            - five years → 5

            Return STRICT JSON only.
            
            {history_context}

            Latest Message:
            {message}

            {{
                "monthly_income": number or null,
                "living_expense": number or null,
                "current_savings": number or null,
                "has_loan": "yes" or "no" or null,
                "loan_amount": number or null,
                "loan_emi": number or null,
                "loan_years": number or null,
                "loan_interest_rate": number or null (e.g., 0.10 for 10%),
                "return_rate": number or null (e.g., 0.12 for 12%),
                "inflation_rate": number or null (e.g., 0.06 for 6%),
                "has_insurance": "yes" or "no" or null
            }}
            """

            llm_data = await self.llm.extract_json(prompt)

            if isinstance(llm_data, str):
                llm_data = json.loads(llm_data)

            if isinstance(llm_data, dict):
                data.update(llm_data)

        # -----------------------------
        # Normalization
        # -----------------------------
        
        # Auto-calculate EMI if loan amount and interest are provided but EMI is not
        if data.get("loan_amount") and data.get("loan_years") and data.get("loan_interest_rate") and not data.get("loan_emi"):
            p = float(data["loan_amount"])
            r = float(data["loan_interest_rate"]) / 12.0
            n = float(data["loan_years"]) * 12.0
            if r > 0 and n > 0:
                emi = p * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
                data["loan_emi"] = round(emi, 2)
        
        data["has_loan"] = True if data.get("loan_emi") or data.get("loan_amount") else False
        data["has_insurance"] = data.get("has_insurance", "no")

        return data