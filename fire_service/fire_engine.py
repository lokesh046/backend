# -------- fire_engine.py --------

def calculate_fire_plan(
    monthly_income: float,
    living_expense: float,
    current_savings: float,
    return_rate: float,
    inflation_rate: float,
    has_loan: bool,
    loan_emi: float = 0.0,
    loan_years: int = 0
):
    """
    Clean FIRE Calculator
    - Real return adjusted
    - Loan phase supported
    - Bankruptcy detection
    """

    real_return_rate = ((1 + return_rate) / (1 + inflation_rate)) - 1

  
    annual_expense = living_expense * 12
    fire_number = annual_expense * 25

    net_monthly_cashflow = monthly_income - living_expense - (loan_emi if has_loan else 0)

    # If negative cashflow → FIRE not possible
    if net_monthly_cashflow <= 0:
        return {
            "fire_number": fire_number,
            "fire_year": "Not Achievable - Negative Cashflow",
            "final_wealth": round(current_savings, 2)
        }

    wealth = current_savings
    year = 0
    max_year_limit = 100

    # FIRE SIMULATION LOOP
    while wealth < fire_number and year <= max_year_limit:

        year += 1

        # During loan years
        if has_loan and year <= loan_years:
            annual_savings = net_monthly_cashflow * 12
        else:
            annual_savings = (monthly_income - living_expense) * 12

        wealth = (wealth + annual_savings) * (1 + real_return_rate)

        # Bankruptcy protection
        if wealth <= 0:
            return {
                "fire_number": fire_number,
                "fire_year": "Bankrupt before FIRE",
                "final_wealth": 0
            }

    if year >= max_year_limit:
        fire_year = "Beyond 100 years"
    else:
        fire_year = year

    return {
        "fire_number": fire_number,
        "fire_year": fire_year,
        "final_wealth": round(wealth, 2)
    }