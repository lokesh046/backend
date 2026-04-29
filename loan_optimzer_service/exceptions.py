class InvalidLoanInputError(ValueError):
    """Exception raised for invalid loan inputs such as negative amounts or tenure out of bounds."""
    pass

class InvalidInterestRateError(ValueError):
    """Exception raised when the interest rate is not within valid bounds."""
    pass

class EMIValidationError(ValueError):
    """Exception raised when EMI is too low to cover interest or unrealistically high."""
    pass
 