# financial health score

def calculate_savings_score(monthly_income: float,living_expense: float) -> float:
    """
    calculates savings score out of 40
    
    """

    base_monthly_savings = monthly_income - living_expense

    #savings rate
    savings_rate = base_monthly_savings / monthly_income

    #score out of 40

    savings_score =savings_rate * 40

    return savings_score


#step 2: DEBT LOAD SCORE

def calculate_debt_score(monthly_income: float,loan_emi: float) -> float:
    """
    calculates debt load score out of 30

    """

    if  loan_emi == 0:
        return 30.0
    
    #if no loan -> full score
    debt_ratio = loan_emi / monthly_income

    #score out of 30
    debt_score = (1 - debt_ratio) * 30

    #prevent negative values
    if debt_score < 0 :
        debt_score = 0
    
    return debt_score


def calculate_insurance_score(has_insurance: str):
    """
    calculate the insurance score
    
    """

    if has_insurance == "yes":
        return 10.0
    else: return 0.0

def calculate_fire_progress_score(current_savings:float,fire_number: float) -> float:

    """
    calculates fire progress score out of 30

    """

    if fire_number == 0:
        return 0.0
    
    #progress ratio
    fire_progress = current_savings / fire_number

    #score out of 30
    fire_score = fire_progress * 30

    if fire_score > 30:
        fire_score = 30
    
    return fire_score


def calculate_financial_health_score(

    monthly_income: float,
    living_expense: float,
    loan_emi: float,
    current_savings: float,
    fire_number: float,
    has_insurance: str
) -> float:
    """

    combines all scores into  a final 0 -100 financial health score

    """

    savings_score = calculate_savings_score(monthly_income, living_expense)
    debt_score = calculate_debt_score(monthly_income,loan_emi)
    fire_score = calculate_fire_progress_score(current_savings,fire_number)
    insurance_score = calculate_insurance_score(has_insurance)

    final_score =savings_score + debt_score + fire_score + insurance_score

    if final_score > 100:
        final_score = 100
    elif final_score < 0:
        final_score = 0

    return final_score

