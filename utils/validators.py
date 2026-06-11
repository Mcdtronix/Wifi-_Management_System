"""
utils/validators.py
-------------------
Reusable Django field validators for TengarakoData.
All validators raise ValidationError with explicit, user-facing messages.
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Phone / Contact
# ---------------------------------------------------------------------------

def validate_zimbabwe_phone(value: str) -> None:
    """
    Accept Zimbabwean mobile numbers in international (+263) or local (07x) format.
    Valid examples: +263771234567, 0771234567, 263771234567
    """
    cleaned = re.sub(r"[\s\-()]", "", value)
    pattern = r"^(?:\+?263|0)[789]\d{8}$"
    if not re.fullmatch(pattern, cleaned):
        raise ValidationError(
            _("Enter a valid Zimbabwean phone number (e.g. +263771234567 or 0771234567).")
        )


# ---------------------------------------------------------------------------
# MAC Address
# ---------------------------------------------------------------------------

def validate_mac_address(value: str) -> None:
    """
    Validate MAC address in colon-separated or hyphen-separated format.
    Accepted: AA:BB:CC:DD:EE:FF or AA-BB-CC-DD-EE-FF (case-insensitive).
    Rejects broadcast (FF:FF:FF:FF:FF:FF) and all-zero addresses.
    """
    cleaned = value.upper().replace("-", ":")
    pattern = r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$"
    if not re.fullmatch(pattern, cleaned):
        raise ValidationError(
            _("Enter a valid MAC address (e.g. AA:BB:CC:DD:EE:FF).")
        )
    if cleaned in ("FF:FF:FF:FF:FF:FF", "00:00:00:00:00:00"):
        raise ValidationError(
            _("Broadcast and null MAC addresses are not permitted.")
        )


# ---------------------------------------------------------------------------
# Voucher Code
# ---------------------------------------------------------------------------

def validate_voucher_code(value: str) -> None:
    """
    TengarakoData voucher format: TGD-XXXX-XXXX
    where X is an uppercase alphanumeric character.
    """
    pattern = r"^TGD-[A-Z0-9]{4}-[A-Z0-9]{4}$"
    if not re.fullmatch(pattern, value):
        raise ValidationError(
            _("Invalid voucher code format. Expected: TGD-XXXX-XXXX.")
        )


# ---------------------------------------------------------------------------
# Bandwidth
# ---------------------------------------------------------------------------

def validate_bandwidth_mbps(value: int) -> None:
    """Speed must be between 1 Mbps and 1000 Mbps (1 Gbps)."""
    if not (1 <= value <= 1000):
        raise ValidationError(
            _("Bandwidth must be between 1 Mbps and 1,000 Mbps.")
        )


# ---------------------------------------------------------------------------
# Quota
# ---------------------------------------------------------------------------

def validate_quota_gb(value: float) -> None:
    """Daily quota must be between 0.5 GB and 1,000 GB."""
    if not (0.5 <= value <= 1000):
        raise ValidationError(
            _("Data quota must be between 0.5 GB and 1,000 GB.")
        )


# ---------------------------------------------------------------------------
# National ID (Zimbabwe)
# ---------------------------------------------------------------------------

def validate_zimbabwe_national_id(value: str) -> None:
    """
    Zimbabwean National ID format: ##-######-X-##
    Example: 63-123456-A-75
    """
    pattern = r"^\d{2}-\d{6}-[A-Z]-\d{2}$"
    if not re.fullmatch(pattern, value.upper()):
        raise ValidationError(
            _("Enter a valid Zimbabwean National ID (e.g. 63-123456-A-75).")
        )


# ---------------------------------------------------------------------------
# Username
# ---------------------------------------------------------------------------

def validate_subscriber_username(value: str) -> None:
    """
    Subscriber username: 4–32 chars, lowercase alphanumeric and underscores/hyphens/@/. only.
    Must start with a letter.
    """
    if not re.fullmatch(r"^[a-z][a-z0-9_\-\.@]{3,31}$", value):
        raise ValidationError(
            _(
                "Username must be 4–32 characters, start with a letter, "
                "and contain only lowercase letters, digits, underscores, hyphens, @, or dots."
            )
        )


# ---------------------------------------------------------------------------
# Positive money / duration
# ---------------------------------------------------------------------------

def validate_positive_decimal(value) -> None:
    if value <= 0:
        raise ValidationError(_("This value must be greater than zero."))


def validate_positive_integer(value: int) -> None:
    if value <= 0:
        raise ValidationError(_("This value must be a positive integer."))