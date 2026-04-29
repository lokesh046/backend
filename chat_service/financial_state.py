# chat_service/financial_state.py

from typing import Optional, Dict, Any, List
from datetime import datetime


class FinancialState:
    """
    Canonical financial memory container.
    Shared across all deterministic engines.
    """

    VERSION = "1.0"

    def __init__(self, user_id: Optional[str] = None):

        # ---- Identity ----
        self.user_id: Optional[str] = user_id
        self.created_at: str = datetime.utcnow().isoformat()
        self.updated_at: str = self.created_at

        # ---- Core Income Data ----
        self.monthly_income: Optional[float] = None
        self.living_expense: Optional[float] = None
        self.current_savings: Optional[float] = None

        # ---- Investment Parameters ----
        self.return_rate: Optional[float] = None
        self.inflation_rate: Optional[float] = None

        # ---- Loan Data ----
        self.has_loan: Optional[bool] = None
        self.loan_amount: Optional[float] = None
        self.loan_emi: Optional[float] = None
        self.loan_years: Optional[int] = None
        self.loan_interest_rate: Optional[float] = None

        # 🔥 ADD THIS
        self.has_insurance = "no"


        # ---- FIRE Results ----
        self.fire_number: Optional[float] = None
        self.fire_year: Optional[int] = None
        self.final_wealth: Optional[float] = None

        # ---- Health Score ----
        self.financial_health_score: Optional[float] = None

        # ---- Portfolio Module (Future) ----
        self.risk_score: Optional[float] = None
        self.asset_allocation: Optional[Dict[str, float]] = None
        self.monte_carlo_probability: Optional[float] = None

        # ---- Scenario Engine ----
        self.scenarios: List[Dict[str, Any]] = []

        # ---- Guardrail Flags ----
        self.flags: List[str] = []

    def invalidate_fire(self):
        print("🔥 FIRE invalidated")
        self.fire_number = None
        self.fire_year = None
        self.final_wealth = None

    def to_dict(self):
        return self.__dict__
    # ==============================
    # 🔁 Update State From Tool
    # ==============================

    def update_from_tool(self, tool_name: str, result: Dict[str, Any]):
        """
        Update financial state after deterministic tool execution.
        """

        if tool_name == "calculate_fire":
            self.fire_number = result.get("fire_number")
            self.fire_year = result.get("fire_year")
            self.final_wealth = result.get("final_wealth")

        elif tool_name == "optimize_loan":
            self.loan_emi = result.get("optimal_emi_suggestions", {}) \
                .get("recommended_option", {}) \
                .get("emi")

        elif tool_name in ("health_score", "calculate_health_score"):
            self.financial_health_score = result.get("financial_health_score")

        self.updated_at = datetime.utcnow().isoformat()

    # ==============================
    # 🧠 Scenario Storage
    # ==============================

    def add_scenario(self, label: str, data: Dict[str, Any]):
        self.scenarios.append({
            "label": label,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })

    # ==============================
    # ⚠️ Guardrail Flags
    # ==============================

    def add_flag(self, message: str):
        self.flags.append(message)

    # ==============================
    # 📦 Serialization
    # ==============================

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        obj = cls(user_id=data.get("user_id"))
        obj.__dict__.update(data)
        return obj