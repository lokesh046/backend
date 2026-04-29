import math
from typing import List, Dict, Any, Union
from .exceptions import InvalidLoanInputError, InvalidInterestRateError, EMIValidationError

def validate_loan_inputs(loan_amount: float, annual_interest_rate: float, tenure_years: int) -> None:

    if loan_amount <= 0:
        raise InvalidLoanInputError("Loan amount must be greater than 0.")

    # Accept both decimal (0.085) and percentage (8.5) formats
    # Convert percentage to decimal if needed
    rate = annual_interest_rate
    if rate > 1:  # Likely in percentage format (e.g., 8.5%)
        rate = rate / 100
    
    if rate <= 0 or rate > 1:  # Allow up to 100%
        raise InvalidInterestRateError("Interest rate must be between 0 and 100%.")

    if tenure_years <= 0 or tenure_years > 40:
        raise InvalidLoanInputError("Tenure must be between 1 and 40 years.")

def normalize_interest_rate(rate_value: float, rate_type: str) -> float:
    """
    Converts interest rate to annual rate.
    Accepts both decimal (0.085) and percentage (8.5) formats.
    """

    if rate_type == "annual":
        annual_rate = rate_value
    elif rate_type == "monthly":
        annual_rate = rate_value * 12
    else:
        raise InvalidInterestRateError("rate_type must be 'annual' or 'monthly'.")

    # Convert percentage to decimal if needed (e.g., 8.5 -> 0.085)
    if annual_rate > 1:
        annual_rate = annual_rate / 100
    
    # Safety check - allow up to 100%
    if annual_rate <= 0 or annual_rate > 1:
        raise InvalidInterestRateError("Annual interest must be between 0% and 100%.")

    return annual_rate


# EMI calculating 
def calculate_emi(loan_amount: float, annual_interest_rate: float, tenure_years: int) -> float:
    validate_loan_inputs(loan_amount, annual_interest_rate, tenure_years)

    monthly_rate = annual_interest_rate / 12
    months = tenure_years * 12

    # EMI formula
    emi = (
        loan_amount * monthly_rate * (1 + monthly_rate) ** months
    ) / ((1 + monthly_rate) ** months - 1)

    return round(emi, 2)


## calculating the interest their paid 

def generate_amortization_schedule(loan_amount: float, annual_interest_rate: float, emi: float) -> Dict[str, Any]:

    monthly_rate = annual_interest_rate / 12

    if emi <= 0:
        raise EMIValidationError("EMI must be greater than 0.")

    min_emi_required = loan_amount * monthly_rate

    if emi <= min_emi_required:
        raise EMIValidationError(
            f"EMI too low. Minimum EMI must be greater than {round(min_emi_required,2)}"
        )

    if emi > loan_amount:
        raise EMIValidationError("EMI is unrealistically high compared to loan amount.")


    monthly_rate = annual_interest_rate / 12
    balance = loan_amount
    month = 0
    total_interest = 0

    max_month_limit = 1000  # safety guard

    schedule: List[Dict[str, Union[int, float]]] = []

    while balance > 0 and month < max_month_limit:

        month += 1

        interest = balance * monthly_rate
        principal = emi - interest

        # Prevent negative principal case
        if principal <= 0:
            raise EMIValidationError("EMI too low. Loan will never be repaid.")

        # Final month adjustment
        if principal > balance:
            principal = balance
            emi = interest + principal

        balance -= principal
        total_interest += interest

        schedule.append({
            "month": month,
            "principal_paid": round(principal, 2),
            "interest_paid": round(interest, 2),
            "remaining_balance": round(balance, 2)
        })

    if month >= max_month_limit:
        raise EMIValidationError("Loan repayment exceeds safe simulation limit.")

    return {
        "months_to_payoff": month,
        "total_interest_paid": round(total_interest, 2),
        "schedule": schedule
    }

def suggest_optimal_emi(loan_amount: float, annual_interest_rate: float, tenure_years: int) -> Dict[str, Any]:

    base_emi = calculate_emi(
        loan_amount,
        annual_interest_rate,
        tenure_years
    )

    increments = [0, 0.1, 0.2, 0.3]  # include base EMI
    results: List[Dict[str, Union[float, int]]] = []

    for inc in increments:

        test_emi = base_emi * (1 + inc)

        schedule_data = generate_amortization_schedule(
            loan_amount,
            annual_interest_rate,
            test_emi
        )

        results.append({
            "emi": round(test_emi, 2),
            "months_to_payoff": schedule_data["months_to_payoff"],
            "total_interest_paid": schedule_data["total_interest_paid"]
        })

    # Optimization criteria:
    # Always recommend the base EMI if +20% is too aggressive, or just return the +20% as an 'aggressive' option.
    # We will pick the +20% increment as the recommended "optimized" path by default.
    recommended = results[2] # 20% increment

    return {
        "emi_options": results,
        "recommended_option": recommended
    }