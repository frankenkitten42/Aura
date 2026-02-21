"""
Population Pressure System for the Living Soundscape Engine.

Manages the progression of discomfort based on population density:
- 0-15%: Normal soundscape
- 15-25%: Silence phase (wildlife retreats)  
- 25-35%: Subtle discomfort sounds begin
- 35-50%: Increased discomfort sounds
- 50%+: Static/filtered discomfort layer, scaling with population

This creates a narratively coherent progression where crowding
directly drives uncomfortable audio, not just rhythm disruption.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class PressurePhase(Enum):
    """Population pressure phases."""
    NORMAL = "normal"           # 0-15%: Natural soundscape
    SILENCE = "silence"         # 15-25%: Wildlife retreats
    SUBTLE = "subtle"           # 25-35%: Subtle discomfort
    MODERATE = "moderate"       # 35-50%: Moderate discomfort
    INTENSE = "intense"         # 50-70%: Intense discomfort + static
    CRITICAL = "critical"       # 70%+: Maximum pressure


@dataclass
class PressureThresholds:
    """Configurable thresholds for pressure phases."""
    silence_start: float = 0.15      # 15%
    subtle_start: float = 0.25       # 25%
    moderate_start: float = 0.35     # 35%
    intense_start: float = 0.50      # 50%
    critical_start: float = 0.70     # 70%


@dataclass
class PressureState:
    """Current state of the pressure system."""
    phase: PressurePhase = PressurePhase.NORMAL
    population: float = 0.0
    
    # Modifiers applied to sound selection
    wildlife_suppression: float = 0.0     # 0-1, reduces natural sounds
    discomfort_boost: float = 0.0         # 0-1, increases discomfort sounds
    static_intensity: float = 0.0         # 0-1, static/drone layer intensity
    silence_enforcement: float = 0.0      # 0-1, forces gaps between sounds
    
    # Active discomfort sounds
    active_discomfort_sounds: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'phase': self.phase.value,
            'population': self.population,
            'wildlife_suppression': self.wildlife_suppression,
            'discomfort_boost': self.discomfort_boost,
            'static_intensity': self.static_intensity,
            'silence_enforcement': self.silence_enforcement,
        }


# Discomfort sound definitions
# These are designed to be subtly uncomfortable without being obviously unpleasant
DISCOMFORT_SOUNDS = {
    # Subtle phase (25-35%) - things that create unease
    "subtle": [
        {
            "id": "distant_unidentified",
            "name": "Distant Unidentified Sound",
            "description": "Vague, hard-to-place sound in the distance",
            "layer": "anomalous",
            "frequency_band": "low_mid",
            "base_probability": 0.3,
            "duration": {"min": 2.0, "max": 5.0},
            "intensity": {"min": 0.2, "max": 0.4},
            "cooldown": 15.0,
            "tags": ["discomfort", "subtle", "unidentified"],
            "sdi_contribution": 0.08,
        },
        {
            "id": "slight_rumble",
            "name": "Slight Rumble",
            "description": "Low, barely perceptible vibration",
            "layer": "background",
            "frequency_band": "low",
            "base_probability": 0.4,
            "duration": {"min": 5.0, "max": 15.0},
            "intensity": {"min": 0.15, "max": 0.3},
            "cooldown": 20.0,
            "tags": ["discomfort", "subtle", "rumble"],
            "sdi_contribution": 0.05,
        },
        {
            "id": "unnatural_silence",
            "name": "Unnatural Silence",
            "description": "Oppressive quiet that feels wrong",
            "layer": "background",
            "frequency_band": "full",
            "base_probability": 0.35,
            "duration": {"min": 8.0, "max": 20.0},
            "intensity": {"min": 0.05, "max": 0.1},
            "cooldown": 30.0,
            "tags": ["discomfort", "subtle", "silence"],
            "sdi_contribution": 0.06,
        },
    ],
    
    # Moderate phase (35-50%) - more noticeable discomfort
    "moderate": [
        {
            "id": "tonal_drone",
            "name": "Tonal Drone",
            "description": "Persistent low-frequency tone at edge of hearing",
            "layer": "background",
            "frequency_band": "low",
            "base_probability": 0.5,
            "duration": {"min": 15.0, "max": 45.0},
            "intensity": {"min": 0.2, "max": 0.4},
            "cooldown": 10.0,
            "tags": ["discomfort", "moderate", "drone"],
            "sdi_contribution": 0.12,
        },
        {
            "id": "discordant_tone",
            "name": "Discordant Tone",
            "description": "Brief dissonant frequency",
            "layer": "periodic",
            "frequency_band": "mid_high",
            "base_probability": 0.35,
            "duration": {"min": 1.0, "max": 3.0},
            "intensity": {"min": 0.25, "max": 0.45},
            "cooldown": 12.0,
            "tags": ["discomfort", "moderate", "discordant"],
            "sdi_contribution": 0.10,
        },
        {
            "id": "pressure_change",
            "name": "Pressure Change",
            "description": "Sensation of air pressure shifting",
            "layer": "background",
            "frequency_band": "low",
            "base_probability": 0.4,
            "duration": {"min": 5.0, "max": 12.0},
            "intensity": {"min": 0.3, "max": 0.5},
            "cooldown": 25.0,
            "tags": ["discomfort", "moderate", "pressure"],
            "sdi_contribution": 0.08,
        },
        {
            "id": "unsettling_harmonic",
            "name": "Unsettling Harmonic",
            "description": "Barely-there harmonic that creates unease",
            "layer": "periodic",
            "frequency_band": "mid",
            "base_probability": 0.3,
            "duration": {"min": 2.0, "max": 6.0},
            "intensity": {"min": 0.2, "max": 0.35},
            "cooldown": 18.0,
            "tags": ["discomfort", "moderate", "harmonic"],
            "sdi_contribution": 0.09,
        },
    ],
    
    # Intense phase (50-70%) - clear discomfort
    "intense": [
        {
            "id": "static_layer",
            "name": "Static Layer",
            "description": "Low-level static noise",
            "layer": "background",
            "frequency_band": "full",
            "base_probability": 0.6,
            "duration": {"min": 20.0, "max": 60.0},
            "intensity": {"min": 0.15, "max": 0.35},
            "cooldown": 5.0,
            "tags": ["discomfort", "intense", "static"],
            "sdi_contribution": 0.15,
        },
        {
            "id": "filtered_noise",
            "name": "Filtered Noise",
            "description": "Swept filtered noise, like distant machinery",
            "layer": "background",
            "frequency_band": "low_mid",
            "base_probability": 0.5,
            "duration": {"min": 10.0, "max": 30.0},
            "intensity": {"min": 0.25, "max": 0.45},
            "cooldown": 8.0,
            "tags": ["discomfort", "intense", "filtered"],
            "sdi_contribution": 0.12,
        },
        {
            "id": "oppressive_hum",
            "name": "Oppressive Hum",
            "description": "Heavy, oppressive background hum",
            "layer": "background",
            "frequency_band": "low",
            "base_probability": 0.55,
            "duration": {"min": 15.0, "max": 40.0},
            "intensity": {"min": 0.3, "max": 0.5},
            "cooldown": 10.0,
            "tags": ["discomfort", "intense", "hum"],
            "sdi_contribution": 0.14,
        },
        {
            "id": "tension_tone",
            "name": "Tension Tone",
            "description": "Rising tension frequency",
            "layer": "periodic",
            "frequency_band": "mid_high",
            "base_probability": 0.4,
            "duration": {"min": 3.0, "max": 8.0},
            "intensity": {"min": 0.3, "max": 0.5},
            "cooldown": 15.0,
            "tags": ["discomfort", "intense", "tension"],
            "sdi_contribution": 0.11,
        },
    ],
    
    # Critical phase (70%+) - maximum pressure
    "critical": [
        {
            "id": "heavy_static",
            "name": "Heavy Static",
            "description": "Prominent static interference",
            "layer": "background",
            "frequency_band": "full",
            "base_probability": 0.7,
            "duration": {"min": 30.0, "max": 90.0},
            "intensity": {"min": 0.3, "max": 0.5},
            "cooldown": 3.0,
            "tags": ["discomfort", "critical", "static"],
            "sdi_contribution": 0.20,
        },
        {
            "id": "subsonic_pulse",
            "name": "Subsonic Pulse",
            "description": "Deep subsonic pulsing felt more than heard",
            "layer": "background",
            "frequency_band": "low",
            "base_probability": 0.6,
            "duration": {"min": 10.0, "max": 25.0},
            "intensity": {"min": 0.4, "max": 0.6},
            "cooldown": 8.0,
            "tags": ["discomfort", "critical", "subsonic"],
            "sdi_contribution": 0.18,
        },
        {
            "id": "distortion_layer",
            "name": "Distortion Layer",
            "description": "Subtle distortion on all audio",
            "layer": "background",
            "frequency_band": "full",
            "base_probability": 0.65,
            "duration": {"min": 20.0, "max": 50.0},
            "intensity": {"min": 0.25, "max": 0.45},
            "cooldown": 5.0,
            "tags": ["discomfort", "critical", "distortion"],
            "sdi_contribution": 0.16,
        },
        {
            "id": "harsh_frequency",
            "name": "Harsh Frequency",
            "description": "Brief harsh frequency spike",
            "layer": "anomalous",
            "frequency_band": "high",
            "base_probability": 0.35,
            "duration": {"min": 0.5, "max": 2.0},
            "intensity": {"min": 0.35, "max": 0.55},
            "cooldown": 20.0,
            "tags": ["discomfort", "critical", "harsh"],
            "sdi_contribution": 0.15,
        },
    ],
}

# Wildlife sounds that should be suppressed during silence phase
WILDLIFE_TAGS = ["bird", "fauna", "insect", "animal", "organic"]


class PopulationPressure:
    """
    Manages population-based pressure on the soundscape.
    
    This system directly modifies sound selection based on population:
    1. Suppresses wildlife sounds as population increases
    2. Introduces discomfort sounds at thresholds
    3. Adds static/noise layer at high population
    4. Forces silence gaps at moderate population
    
    Example:
        >>> pressure = PopulationPressure()
        >>> pressure.update(population=0.45)
        >>> 
        >>> # Check modifiers
        >>> print(pressure.state.wildlife_suppression)  # 0.6
        >>> print(pressure.state.discomfort_boost)      # 0.5
        >>> 
        >>> # Get available discomfort sounds
        >>> sounds = pressure.get_discomfort_sounds()
    """
    
    def __init__(self, thresholds: Optional[PressureThresholds] = None):
        """
        Initialize the pressure system.
        
        Args:
            thresholds: Custom thresholds, or None for defaults
        """
        self.thresholds = thresholds or PressureThresholds()
        self.state = PressureState()
        
        # Build sound lookup
        self._discomfort_sounds = DISCOMFORT_SOUNDS
    
    def update(self, population: float) -> PressureState:
        """
        Update pressure state based on population.
        
        Args:
            population: Population ratio (0.0 to 1.0)
            
        Returns:
            Updated PressureState
        """
        self.state.population = population
        
        # Determine phase
        if population < self.thresholds.silence_start:
            self.state.phase = PressurePhase.NORMAL
        elif population < self.thresholds.subtle_start:
            self.state.phase = PressurePhase.SILENCE
        elif population < self.thresholds.moderate_start:
            self.state.phase = PressurePhase.SUBTLE
        elif population < self.thresholds.intense_start:
            self.state.phase = PressurePhase.MODERATE
        elif population < self.thresholds.critical_start:
            self.state.phase = PressurePhase.INTENSE
        else:
            self.state.phase = PressurePhase.CRITICAL
        
        # Calculate modifiers based on phase
        self._calculate_modifiers()
        
        return self.state
    
    def _calculate_modifiers(self) -> None:
        """Calculate pressure modifiers based on current phase and population."""
        pop = self.state.population
        phase = self.state.phase
        t = self.thresholds
        
        # Reset modifiers
        self.state.wildlife_suppression = 0.0
        self.state.discomfort_boost = 0.0
        self.state.static_intensity = 0.0
        self.state.silence_enforcement = 0.0
        
        if phase == PressurePhase.NORMAL:
            # No pressure effects
            pass
        
        elif phase == PressurePhase.SILENCE:
            # Wildlife begins retreating (15-25%)
            # Linear interpolation within phase
            progress = (pop - t.silence_start) / (t.subtle_start - t.silence_start)
            self.state.wildlife_suppression = progress * 0.5  # Up to 50% suppression
            self.state.silence_enforcement = progress * 0.3   # Some forced silence
        
        elif phase == PressurePhase.SUBTLE:
            # Subtle discomfort begins (25-35%)
            progress = (pop - t.subtle_start) / (t.moderate_start - t.subtle_start)
            self.state.wildlife_suppression = 0.5 + progress * 0.2  # 50-70%
            self.state.discomfort_boost = progress * 0.3  # Up to 30%
            self.state.silence_enforcement = 0.3 - progress * 0.1  # Reduce silence as discomfort increases
        
        elif phase == PressurePhase.MODERATE:
            # Moderate discomfort (35-50%)
            progress = (pop - t.moderate_start) / (t.intense_start - t.moderate_start)
            self.state.wildlife_suppression = 0.7 + progress * 0.2  # 70-90%
            self.state.discomfort_boost = 0.3 + progress * 0.3  # 30-60%
            self.state.silence_enforcement = 0.2 - progress * 0.2  # Less silence
        
        elif phase == PressurePhase.INTENSE:
            # Intense discomfort with static (50-70%)
            progress = (pop - t.intense_start) / (t.critical_start - t.intense_start)
            self.state.wildlife_suppression = 0.9 + progress * 0.1  # 90-100%
            self.state.discomfort_boost = 0.6 + progress * 0.2  # 60-80%
            self.state.static_intensity = progress * 0.4  # Static builds up to 40%
            self.state.silence_enforcement = 0.0  # No silence - constant pressure
        
        elif phase == PressurePhase.CRITICAL:
            # Maximum pressure (70%+)
            progress = min(1.0, (pop - t.critical_start) / (1.0 - t.critical_start))
            self.state.wildlife_suppression = 1.0  # Full suppression
            self.state.discomfort_boost = 0.8 + progress * 0.2  # 80-100%
            self.state.static_intensity = 0.4 + progress * 0.4  # 40-80% static
            self.state.silence_enforcement = 0.0
    
    def get_discomfort_sounds(self) -> List[Dict[str, Any]]:
        """
        Get discomfort sounds available for current phase.
        
        Returns:
            List of sound definitions appropriate for current pressure
        """
        sounds = []
        phase = self.state.phase
        
        if phase == PressurePhase.SUBTLE:
            sounds.extend(self._discomfort_sounds["subtle"])
        
        elif phase == PressurePhase.MODERATE:
            sounds.extend(self._discomfort_sounds["subtle"])
            sounds.extend(self._discomfort_sounds["moderate"])
        
        elif phase == PressurePhase.INTENSE:
            sounds.extend(self._discomfort_sounds["subtle"])
            sounds.extend(self._discomfort_sounds["moderate"])
            sounds.extend(self._discomfort_sounds["intense"])
        
        elif phase == PressurePhase.CRITICAL:
            sounds.extend(self._discomfort_sounds["subtle"])
            sounds.extend(self._discomfort_sounds["moderate"])
            sounds.extend(self._discomfort_sounds["intense"])
            sounds.extend(self._discomfort_sounds["critical"])
        
        return sounds
    
    def get_discomfort_sound_ids(self) -> List[str]:
        """Get IDs of available discomfort sounds."""
        return [s["id"] for s in self.get_discomfort_sounds()]
    
    def should_suppress_sound(self, sound_tags: List[str]) -> Tuple[bool, float]:
        """
        Check if a sound should be suppressed based on its tags.
        
        Args:
            sound_tags: Tags of the sound
            
        Returns:
            Tuple of (should_suppress, suppression_amount)
        """
        # Check if any wildlife tags present
        is_wildlife = any(tag in WILDLIFE_TAGS for tag in sound_tags)
        
        if is_wildlife and self.state.wildlife_suppression > 0:
            return True, self.state.wildlife_suppression
        
        return False, 0.0
    
    def modify_probability(self, sound_id: str, sound_tags: List[str], 
                           base_probability: float) -> float:
        """
        Modify a sound's selection probability based on pressure.
        
        Args:
            sound_id: The sound ID
            sound_tags: Tags of the sound
            base_probability: Original probability
            
        Returns:
            Modified probability
        """
        probability = base_probability
        
        # Suppress wildlife
        is_wildlife = any(tag in WILDLIFE_TAGS for tag in sound_tags)
        if is_wildlife:
            probability *= (1.0 - self.state.wildlife_suppression)
        
        # Boost discomfort sounds
        is_discomfort = "discomfort" in sound_tags
        if is_discomfort:
            boost = 1.0 + self.state.discomfort_boost * 2.0  # Up to 3x probability
            probability *= boost
        
        return min(1.0, probability)
    
    def get_static_event(self) -> Optional[Dict[str, Any]]:
        """
        Get a static/noise event if appropriate for current phase.
        
        Returns:
            Event dict or None
        """
        if self.state.static_intensity <= 0:
            return None
        
        # Select appropriate static sound based on intensity
        if self.state.static_intensity < 0.3:
            sound_id = "static_layer"
        elif self.state.static_intensity < 0.6:
            sound_id = "filtered_noise"
        else:
            sound_id = "heavy_static"
        
        return {
            "sound_id": sound_id,
            "intensity": self.state.static_intensity,
            "continuous": True,
        }
    
    def get_phase_description(self) -> str:
        """Get a human-readable description of current phase."""
        descriptions = {
            PressurePhase.NORMAL: "Normal - Natural soundscape",
            PressurePhase.SILENCE: "Silence - Wildlife retreating",
            PressurePhase.SUBTLE: "Subtle - Faint discomfort",
            PressurePhase.MODERATE: "Moderate - Noticeable unease",
            PressurePhase.INTENSE: "Intense - Strong discomfort",
            PressurePhase.CRITICAL: "Critical - Maximum pressure",
        }
        return descriptions.get(self.state.phase, "Unknown")
    
    def get_summary(self) -> str:
        """Get a summary of current pressure state."""
        lines = [
            f"Population Pressure: {self.state.population*100:.0f}%",
            f"Phase: {self.get_phase_description()}",
            f"Wildlife Suppression: {self.state.wildlife_suppression*100:.0f}%",
            f"Discomfort Boost: {self.state.discomfort_boost*100:.0f}%",
            f"Static Intensity: {self.state.static_intensity*100:.0f}%",
            f"Silence Enforcement: {self.state.silence_enforcement*100:.0f}%",
        ]
        return "\n".join(lines)
    
    def reset(self) -> None:
        """Reset pressure state."""
        self.state = PressureState()


def get_all_discomfort_sounds() -> Dict[str, List[Dict]]:
    """Get all discomfort sound definitions."""
    return DISCOMFORT_SOUNDS
