"""
Sensory Discomfort Index (SDI) calculation for the Living Soundscape Engine.

The SDI system evaluates the current soundscape and produces a value from
-1.0 (very comfortable) to +1.0 (very uncomfortable), with an operational
maximum of 0.8 to stay below conscious awareness.
"""

from .factors import DiscomfortCalculator
from .comfort import ComfortCalculator
from .calculator import SDICalculator, SDIResult

__all__ = [
    'DiscomfortCalculator',
    'ComfortCalculator',
    'SDICalculator',
    'SDIResult',
]
