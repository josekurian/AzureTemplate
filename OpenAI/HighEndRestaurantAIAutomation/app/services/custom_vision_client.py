class CustomVisionClient:
    """Optional custom plate classifier.

    Use only when Azure AI Vision prebuilt tags are insufficient and you have labeled images of
    restaurant-specific plating standards.
    """

    async def classify_plate_style(self, image_bytes: bytes) -> dict:
        return {
            "style": "mock-modern-tasting-menu",
            "confidence": 0.91,
            "notes": "Optional demo capability. Promote to production only with labeled restaurant-specific data.",
        }
