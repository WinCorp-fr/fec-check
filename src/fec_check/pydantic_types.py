"""
Types Pydantic annotés : Decimal et datetime sérialisés en texte JSON.
"""

# Fichier généré, ne pas modifier à la main.
# empreinte-source: e5529977171b415be291c7169d0969037975269b269ba9e07b5399e9929ef0a6

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

DecimalStr = Annotated[
    Decimal,
    PlainSerializer(lambda v: str(v), return_type=str, when_used="json"),
]
"""Decimal sérialisé en string JSON (préserve la précision, évite les pertes float)."""

DatetimeIso = Annotated[
    datetime,
    PlainSerializer(lambda v: v.isoformat(), return_type=str, when_used="json"),
]
"""datetime sérialisé au format ISO 8601 en JSON."""

__all__ = ["DecimalStr", "DatetimeIso"]
