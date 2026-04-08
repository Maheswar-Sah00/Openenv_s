"""Rule-based baseline policy for smoke tests and judge reference."""

from __future__ import annotations

from typing import Any


class BaselineAgent:
    def reset(self) -> None:
        pass

    def act(self, observation: dict[str, Any], trace: list[str] | None = None) -> str:
        tr = trace or []
        text = (observation.get("message_text") or "").lower()
        hist = " ".join(observation.get("conversation_history") or []).lower()
        blob = f"{text} {hist}"
        sender = observation.get("sender_type", "unknown")
        verified = observation.get("sender_verified")
        urgency = float(observation.get("urgency_score") or 0.0)
        link = bool(observation.get("link_present"))
        channel = observation.get("channel", "sms")
        n_hist = len(observation.get("conversation_history") or [])

        trusted_transactional = {
            "bank_official",
            "delivery_partner",
            "service_provider",
            "government_notice",
            "telco_official",
            "pension_authority",
        }

        otp_pressure = any(
            p in blob
            for p in (
                "send otp",
                "share otp",
                "enter otp",
                "reply with otp",
                "otp immediately",
                "otp now",
                "confirm otp",
                "otp to complete",
                "otp forward",
            )
        )

        scam_kw = otp_pressure or any(
            k in blob
            for k in (
                "kyc",
                "support regarding",
                "fraud desk",
                "suspicious",
                "unusual transaction",
                "unverified device",
                "phishing attempt",
                "sim swap",
                "credit card used",
                "location shows",
                "beneficiary added",
                "demat",
                "customs fee",
                "payroll sync",
                "employee id",
                "cvv",
                "mpin",
                "bit.ly",
                "click http",
                "verify account",
                "blocked",
                "expired",
                "processing fee",
                "double",
                "eth",
                "wallet will be closed",
                "wrong number",
                "forward kar",
                "disburse",
                "customs fee",
            )
        )

        if sender in trusted_transactional and not scam_kw:
            return "ignore"

        if not tr and sender == "unknown":
            return "verify_sender"

        if verified is False:
            if "warn_user" not in tr:
                return "warn_user"
            return "flag_scam"

        if verified is True:
            return "ignore"

        if scam_kw and verified is None:
            if urgency > 0.85 and link:
                return "flag_scam"
            return "verify_sender"

        if urgency > 0.88 and link and sender == "unknown":
            return "flag_scam"

        if n_hist >= 3 and scam_kw:
            return "escalate_to_bank"

        return "ignore"
