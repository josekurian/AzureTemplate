async def detect_intent(text: str):
    # Mock intent detection
    if 'reservation' in text.lower():
        return {'intent': 'reservation', 'confidence': 0.98}
    return {'intent': 'unknown', 'confidence': 0.5}
