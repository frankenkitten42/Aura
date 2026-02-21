"""
Configuration data models for the Living Soundscape Engine.

These dataclasses represent the structure of configuration loaded from
JSON files. They provide type safety and easy access to config values.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class Layer(Enum):
    """Sound layer types."""
    BACKGROUND = "background"
    PERIODIC = "periodic"
    REACTIVE = "reactive"
    ANOMALOUS = "anomalous"


class FrequencyBand(Enum):
    """Audio frequency bands."""
    LOW = "low"
    LOW_MID = "low_mid"
    MID = "mid"
    MID_HIGH = "mid_high"
    HIGH = "high"
    FULL = "full"


class TimeOfDay(Enum):
    """Time of day periods."""
    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"
    MIDNIGHT = "midnight"
    ALL = "all"


class Weather(Enum):
    """Weather states."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    FOG = "fog"
    WIND = "wind"


class Severity(Enum):
    """Conflict severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DeltaCategory(Enum):
    """SDI delta categories for adjustment decisions."""
    NONE = "none"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    CRITICAL = "critical"


# =============================================================================
# Biome Configuration
# =============================================================================

@dataclass
class BiomeParameters:
    """Quantifiable parameters for a biome."""
    baseline_density: float  # Events per minute at rest
    silence_tolerance: float  # Max seconds before silence feels wrong
    sdi_baseline: float  # Natural comfort level (-1.0 to 1.0)
    frequency_band: str  # Primary audio range
    layer_capacity: int  # Max concurrent layers
    
    def __post_init__(self):
        # Convert string to enum if needed, but store as string for simplicity
        pass


@dataclass
class BiomeBlend:
    """Blend configuration for transition zones."""
    primary: str  # Primary biome ID
    primary_weight: float
    secondary: Optional[str]  # Secondary biome ID (or None)
    secondary_weight: float
    secondary_from_adjacent: bool = False  # Inherit from adjacent biome


@dataclass
class BiomeConfig:
    """Configuration for a single biome."""
    id: str
    name: str
    description: str
    parameters: BiomeParameters
    sound_pool: List[str]  # List of valid sound IDs
    tags: List[str] = field(default_factory=list)
    blend: Optional[BiomeBlend] = None  # For transition zones
    
    def is_transition_zone(self) -> bool:
        """Check if this biome is a transition zone."""
        return self.blend is not None


# =============================================================================
# Sound Configuration
# =============================================================================

@dataclass
class DurationConfig:
    """Duration settings for a sound."""
    min: float
    max: float
    type: str  # "single" or "continuous"


@dataclass
class IntensityConfig:
    """Intensity range for a sound."""
    min: float
    max: float


@dataclass
class WeatherConstraints:
    """Weather constraints for sound playback."""
    required: List[str] = field(default_factory=list)
    excluded: List[str] = field(default_factory=list)
    amplified_by: List[str] = field(default_factory=list)


@dataclass
class RhythmInterval:
    """Rhythm interval settings for rhythmic sounds."""
    min: float
    max: float


@dataclass
class SoundConfig:
    """Configuration for a single sound."""
    id: str
    name: str
    layer: str  # Layer type
    frequency_band: str
    base_probability: float
    time_constraints: List[str]
    weather_constraints: WeatherConstraints
    duration: DurationConfig
    intensity: IntensityConfig
    cooldown: float
    natural_duration: Optional[float]  # Expected duration before it feels "too long"
    tags: List[str] = field(default_factory=list)
    rhythm_capable: bool = False
    is_rhythmic: bool = False
    is_silence: bool = False
    reverb: bool = False
    harmony_pairs: List[str] = field(default_factory=list)
    conflict_pairs: List[str] = field(default_factory=list)
    rhythm_interval: Optional[RhythmInterval] = None
    requires_feature: Optional[str] = None


# =============================================================================
# SDI Configuration
# =============================================================================

@dataclass
class SDIGlobalSettings:
    """Global SDI calculation settings."""
    sdi_min: float = -1.0
    sdi_max: float = 1.0
    operational_max: float = 0.8
    smoothing_factor: float = 0.2
    tick_rate: float = 1.0


@dataclass
class SDIFactorConfig:
    """Configuration for a single SDI factor."""
    id: str
    name: str
    description: str
    base_weight: float
    calculation: str
    cap: Optional[float] = None
    modifiers: Dict[str, float] = field(default_factory=dict)
    detection: Dict[str, Any] = field(default_factory=dict)
    formula: Optional[str] = None
    decay_time: Optional[float] = None


@dataclass 
class SDIConfig:
    """Full SDI configuration."""
    global_settings: SDIGlobalSettings
    discomfort_factors: Dict[str, SDIFactorConfig]
    comfort_factors: Dict[str, SDIFactorConfig]
    biome_adjustments: Dict[str, Dict[str, float]]


# =============================================================================
# Population Configuration
# =============================================================================

@dataclass
class PopulationPoint:
    """A point on the population-to-SDI curve."""
    population: float
    target_sdi: float


@dataclass
class PopulationCurve:
    """Population to target SDI mapping curve."""
    type: str  # "piecewise_linear" or "formula"
    points: List[PopulationPoint]


@dataclass
class DeltaThresholds:
    """Thresholds for SDI delta categories."""
    small: float = 0.1
    medium: float = 0.2
    large: float = 0.3
    critical: float = 0.4


@dataclass
class HysteresisConfig:
    """Hysteresis settings to prevent oscillation."""
    enabled: bool = True
    dead_zone: float = 0.05
    ramp_up_speed: float = 0.1
    ramp_down_speed: float = 0.15
    min_hold_time: float = 5.0


@dataclass
class RegionOverride:
    """Override settings for specific region types."""
    curve_modifier: float = 0.0
    min_sdi: float = -1.0
    max_sdi: float = 1.0
    fixed_sdi: Optional[float] = None
    ignore_population: bool = False
    reason: str = ""


@dataclass
class PopulationConfig:
    """Full population configuration."""
    curve: PopulationCurve
    delta_thresholds: DeltaThresholds
    hysteresis: HysteresisConfig
    region_overrides: Dict[str, RegionOverride]
    increase_actions: Dict[str, List[str]]
    decrease_actions: Dict[str, List[str]]


# =============================================================================
# Weather & Time Modifiers
# =============================================================================

@dataclass
class WeatherModifier:
    """Weather state modifier."""
    id: str
    density_modifier: float = 1.0
    silence_modifier: float = 1.0
    sdi_modifier: float = 0.0
    adds_sounds: List[str] = field(default_factory=list)
    removes_sounds: List[str] = field(default_factory=list)
    amplifies_sounds: List[str] = field(default_factory=list)


@dataclass
class TimeOfDayModifier:
    """Time of day modifier."""
    id: str
    hour_range: tuple  # (start_hour, end_hour)
    density_modifier: float = 1.0
    sdi_modifier: float = 0.0
    active_tags: List[str] = field(default_factory=list)
    transitions_from: Optional[str] = None
    transitions_to: Optional[str] = None


# =============================================================================
# Conflict & Harmony Configuration
# =============================================================================

@dataclass
class ConflictPair:
    """A pair of sounds that conflict."""
    sound_a: str
    sound_b: str
    severity: str  # "low", "medium", "high"
    reason: str = ""


@dataclass
class TagConflict:
    """A conflict based on tags."""
    tag_a: str
    tag_b: str
    severity: str
    reason: str = ""


@dataclass
class HarmonyPair:
    """A pair of sounds that harmonize."""
    sound_a: str
    sound_b: str
    strength: str  # "medium", "strong"
    context: str = ""


@dataclass
class ConflictConfig:
    """Full conflict and harmony configuration."""
    sound_conflicts: List[ConflictPair]
    tag_conflicts: List[TagConflict]
    harmony_pairs: List[HarmonyPair]
    time_violations: List[Dict[str, Any]]
    weather_violations: List[Dict[str, Any]]


# =============================================================================
# Master Configuration
# =============================================================================

@dataclass
class LSEConfig:
    """
    Master configuration container for the Living Soundscape Engine.
    
    This holds all loaded configuration data from the various JSON files.
    """
    biomes: Dict[str, BiomeConfig]
    sounds: Dict[str, SoundConfig]
    sdi: SDIConfig
    population: PopulationConfig
    conflicts: ConflictConfig
    weather_modifiers: Dict[str, WeatherModifier]
    time_modifiers: Dict[str, TimeOfDayModifier]
    
    # Derived lookups (populated after loading)
    _sounds_by_layer: Dict[str, List[str]] = field(default_factory=dict)
    _sounds_by_tag: Dict[str, List[str]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Build derived lookup tables."""
        self._build_lookups()
    
    def _build_lookups(self):
        """Build lookup tables for efficient access."""
        # Sounds by layer
        self._sounds_by_layer = {}
        for sound_id, sound in self.sounds.items():
            layer = sound.layer
            if layer not in self._sounds_by_layer:
                self._sounds_by_layer[layer] = []
            self._sounds_by_layer[layer].append(sound_id)
        
        # Sounds by tag
        self._sounds_by_tag = {}
        for sound_id, sound in self.sounds.items():
            for tag in sound.tags:
                if tag not in self._sounds_by_tag:
                    self._sounds_by_tag[tag] = []
                self._sounds_by_tag[tag].append(sound_id)
    
    def get_sounds_by_layer(self, layer: str) -> List[str]:
        """Get all sound IDs for a given layer."""
        return self._sounds_by_layer.get(layer, [])
    
    def get_sounds_by_tag(self, tag: str) -> List[str]:
        """Get all sound IDs with a given tag."""
        return self._sounds_by_tag.get(tag, [])
    
    def get_biome_sounds(self, biome_id: str) -> List[SoundConfig]:
        """Get all sound configs for a biome."""
        biome = self.biomes.get(biome_id)
        if not biome:
            return []
        return [self.sounds[sid] for sid in biome.sound_pool if sid in self.sounds]
    
    def get_valid_sound_ids(self) -> set:
        """Get set of all valid sound IDs."""
        return set(self.sounds.keys())
    
    def get_valid_biome_ids(self) -> set:
        """Get set of all valid biome IDs."""
        return set(self.biomes.keys())
