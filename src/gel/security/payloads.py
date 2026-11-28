from enum import Enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator, model_validator


def get_utc_datetime() -> datetime:
    return datetime.now(timezone.utc)


class PayloadCategory(str, Enum):
    """Category of adversarial security test payload."""

    DIRECT_INJECTION = "direct_injection"
    INDIRECT_INJECTION = "indirect_injection"


class SecurityPayload(BaseModel):
    """Adversarial payload with a deterministic marker for detecting instruction obedience."""

    payload_id: str
    category: PayloadCategory
    text: str
    canary: str
    owasp_ref: str | None = None
    description: str

    @model_validator(mode="after")
    def validate_canary(self) -> "SecurityPayload":
        if not self.canary.strip():
            raise ValueError(f"canary must not be empty for payload '{self.payload_id}'")
        if self.canary not in self.text:
            raise ValueError(
                f"canary must be a substring of text for payload '{self.payload_id}'"
            )
        return self


class PayloadRegistry(BaseModel):
    """Versioned collection of security test payloads."""

    registry_id: str
    registry_version: str
    description: str = ""
    created_at: datetime = Field(default_factory=get_utc_datetime)
    payloads: list[SecurityPayload]

    @field_validator("payloads")
    @classmethod
    def validate_payloads(cls, payloads: list[SecurityPayload]) -> list[SecurityPayload]:
        if not payloads:
            raise ValueError("payloads must contain at least one payload")

        payload_ids = [payload.payload_id for payload in payloads]
        duplicate_payload_ids = list(dict.fromkeys(
            payload_id
            for payload_id in payload_ids
            if payload_ids.count(payload_id) > 1
        ))
        if duplicate_payload_ids:
            raise ValueError(
                f"payload_id values must be unique; duplicates: {duplicate_payload_ids}"
            )

        canaries = [payload.canary for payload in payloads]
        duplicate_canaries = list(dict.fromkeys(
            canary
            for canary in canaries
            if canaries.count(canary) > 1
        ))
        if duplicate_canaries:
            raise ValueError(
                "canary values must be unique; shared canary values make detection "
                f"ambiguous: {duplicate_canaries}"
            )

        return payloads
