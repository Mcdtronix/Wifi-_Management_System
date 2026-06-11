"""
apps/bandwidth/models.py
------------------------
Bandwidth profiles define upload/download speed caps.
Each profile maps to a FreeRADIUS reply attribute pair
(WISPr-Bandwidth-Max-Up / WISPr-Bandwidth-Max-Down).
Plans reference a BandwidthProfile; FreeRADIUS returns the attributes on auth.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from utils.mixins import BaseModel
from utils.validators import validate_bandwidth_mbps


class BandwidthProfile(BaseModel):
    """
    Named speed tier used by plans and enforced at the access point level.

    Predefined tiers (as per spec):
    - Bronze:   2 Mbps ↓ / 1 Mbps ↑
    - Silver:   5 Mbps ↓ / 2 Mbps ↑
    - Gold:    10 Mbps ↓ / 5 Mbps ↑
    - Platinum: 20 Mbps ↓ / 10 Mbps ↑
    Admins may create custom profiles beyond these.
    """

    class TierLabel(models.TextChoices):
        BRONZE = "bronze", _("Bronze")
        SILVER = "silver", _("Silver")
        GOLD = "gold", _("Gold")
        PLATINUM = "platinum", _("Platinum")
        CUSTOM = "custom", _("Custom")

    name = models.CharField(
        max_length=80,
        unique=True,
        verbose_name=_("Profile Name"),
        help_text=_("E.g. 'Gold 10Mbps'."),
    )
    tier = models.CharField(
        max_length=20,
        choices=TierLabel.choices,
        default=TierLabel.CUSTOM,
        verbose_name=_("Tier"),
    )
    download_mbps = models.PositiveSmallIntegerField(
        validators=[validate_bandwidth_mbps],
        verbose_name=_("Download Speed (Mbps)"),
    )
    upload_mbps = models.PositiveSmallIntegerField(
        validators=[validate_bandwidth_mbps],
        verbose_name=_("Upload Speed (Mbps)"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Inactive profiles cannot be assigned to new plans."),
    )

    # RADIUS attribute values (computed; surfaced here for visibility)
    # WISPr speeds are stored in bps (bits per second)
    @property
    def download_bps(self) -> int:
        return (self.download_mbps or 0) * 1_000_000

    @property
    def upload_bps(self) -> int:
        return (self.upload_mbps or 0) * 1_000_000

    class Meta:
        db_table = "bandwidth_profile"
        ordering = ["download_mbps"]
        verbose_name = _("Bandwidth Profile")
        verbose_name_plural = _("Bandwidth Profiles")

    def __str__(self):
        return f"{self.name} — ↓{self.download_mbps}Mbps / ↑{self.upload_mbps}Mbps"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        self.name = self.name.strip()

        if not self.name:
            raise ValidationError({"name": _("Profile name cannot be blank.")})

        # Upload should not exceed download (common ISP convention)
        if self.upload_mbps and self.download_mbps:
            if self.upload_mbps > self.download_mbps:
                raise ValidationError(
                    _(
                        "Upload speed should not exceed download speed. "
                        "If intentional, contact your system administrator."
                    )
                )

        # Enforce tier speed constraints
        tier_constraints = {
            self.TierLabel.BRONZE:   {"download": 2,  "upload": 1},
            self.TierLabel.SILVER:   {"download": 5,  "upload": 2},
            self.TierLabel.GOLD:     {"download": 10, "upload": 5},
            self.TierLabel.PLATINUM: {"download": 20, "upload": 10},
        }
        if self.tier in tier_constraints:
            expected = tier_constraints[self.tier]
            if (
                self.download_mbps != expected["download"]
                or self.upload_mbps != expected["upload"]
            ):
                raise ValidationError(
                    _(
                        f"The '{self.get_tier_display()}' tier must have "
                        f"exactly {expected['download']}Mbps download and "
                        f"{expected['upload']}Mbps upload. "
                        f"Use 'Custom' tier for non-standard speeds."
                    )
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Helper: build RADIUS reply attributes dict
    # ------------------------------------------------------------------

    def to_radius_attributes(self) -> dict:
        """Return the RADIUS attributes this profile should inject on auth."""
        return {
            "WISPr-Bandwidth-Max-Down": str(self.download_bps),
            "WISPr-Bandwidth-Max-Up": str(self.upload_bps),
        }