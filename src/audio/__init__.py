"""
Living Soundscape Engine (LSE) sound selection and management.

This module handles:
- Sound selection based on context and probability
- Layer management and capacity enforcement
- Soundscape orchestration based on SDI targets
"""

from .sound_selector import SoundSelector, SoundCandidate, SelectionResult
from .layer_manager import LayerManager, LayerState
from .soundscape import Soundscape, SoundscapeEvent, EventType

__all__ = [
    'SoundSelector',
    'SoundCandidate',
    'SelectionResult',
    'LayerManager',
    'LayerState',
    'Soundscape',
    'SoundscapeEvent',
    'EventType',
]
