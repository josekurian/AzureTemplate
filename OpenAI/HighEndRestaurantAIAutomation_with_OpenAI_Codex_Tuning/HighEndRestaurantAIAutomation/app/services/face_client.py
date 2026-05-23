class FaceClient:
    """Optional consent-based VIP check-in demo.

    Important: Face recognition requires careful responsible AI review, consent, data minimization,
    and may require gated Azure access depending on region and capability.
    """
    async def verify_vip_guest(self, image_bytes: bytes, consent_id: str) -> dict:
        return {"enabled": False, "reason": "Optional responsible-use gated demo; implement only with consent and policy approval."}
