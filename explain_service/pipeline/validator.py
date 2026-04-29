def validate_text(text):
    if not text or len(text.strip()) < 10:
        raise ValueError("Knowledge text too short")

    return text.strip()

    