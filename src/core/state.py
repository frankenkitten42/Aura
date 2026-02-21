"""
State management for the Living Soundscape Engine.

This module defines all runtime state containers that track the current
state of the simulation. These are separate from configuration (which is
static) and change every tick during execution.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from enum import Enum

# Use forward reference to avoid circular import
if TYPE_CHECKING:
    from ..config.models import BiomeParameters


class EndType(Enum):
    """How a sound ended."""
    NATURAL = "natural"
    FADE_OUT = "fade_out"
    INTERRUPTED = "interrupted"
    FORCED = "forced"


class DeltaCategory(Enum):
    """SDI delta categories for adjustment decisions."""
    NONE = "none"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    CRITICAL = "critical"


# =============================================================================
# Sound Event State
# =============================================================================

@dataclass
class SoundEvent:
    """A record of a sound that has played."""
    sound_id: str
    timestamp: float
    duration: float
    intensity: float
    layer: str
    ended: bool = False
    end_type: Optional[EndType] = None
    end_time: Optional[float] = None


@dataclass
class PatternState:
    """Tracks pattern state for a specific sound."""
    sound_id: str
    occurrences: List[float] = field(default_factory=list)
    intervals: List[float] = field(default_factory=list)
    avg_interval: float = 0.0
    variance: float = 0.0
    is_rhythmic: bool = False
    drift_detected: bool = False
    
    def add_occurrence(self, timestamp: float) -> None:
        """Add a new occurrence and recalculate stats."""
        if self.occurrences:
            interval = timestamp - self.occurrences[-1]
            self.intervals.append(interval)
            
            # Recalculate stats
            if len(self.intervals) >= 2:
                self.avg_interval = sum(self.intervals) / len(self.intervals)
                mean = self.avg_interval
                self.variance = sum((i - mean) ** 2 for i in self.intervals) / len(self.intervals)
                
                # Check for rhythm vs drift
                cv = (self.variance ** 0.5) / mean if mean > 0 else 0
                self.is_rhythmic = cv < 0.10  # Less than 10% variance
                self.drift_detected = 0.15 < cv < 0.40  # 15-40% variance = drift
        
        self.occurrences.append(timestamp)
    
    def clear_old(self, current_time: float, retention: float) -> None:
        """Remove occurrences older than retention window."""
        cutoff = current_time - retention
        while self.occurrences and self.occurrences[0] < cutoff:
            self.occurrences.pop(0)
            if self.intervals:
                self.intervals.pop(0)


@dataclass
class ActiveSound:
    """A currently playing sound instance."""
    instance_id: str
    sound_id: str
    layer: str
    start_time: float
    intensity: float
    frequency_band: str
    is_continuous: bool
    expected_end_time: Optional[float] = None
    cooldown_until: Optional[float] = None
    sdi_contribution: float = 0.0
    tags: List[str] = field(default_factory=list)
    
    def is_expired(self, current_time: float) -> bool:
        """Check if this sound should have ended."""
        if self.is_continuous:
            return False
        if self.expected_end_time is None:
            return False
        return current_time >= self.expected_end_time
    
    def is_on_cooldown(self, current_time: float) -> bool:
        """Check if this sound is still on cooldown."""
        if self.cooldown_until is None:
            return False
        return current_time < self.cooldown_until


# =============================================================================
# Memory State
# =============================================================================

@dataclass
class SilenceTracker:
    """Tracks silence gaps for SDI calculation."""
    last_silence_start: Optional[float] = None
    last_silence_end: Optional[float] = None
    last_silence_duration: float = 0.0
    current_silence_start: Optional[float] = None
    in_silence: bool = True
    
    def start_silence(self, timestamp: float) -> None:
        """Mark the start of a silence period."""
        if not self.in_silence:
            self.current_silence_start = timestamp
            self.in_silence = True
    
    def end_silence(self, timestamp: float) -> None:
        """Mark the end of a silence period."""
        if self.in_silence and self.current_silence_start is not None:
            self.last_silence_start = self.current_silence_start
            self.last_silence_end = timestamp
            self.last_silence_duration = timestamp - self.current_silence_start
            self.current_silence_start = None
            self.in_silence = False
    
    def time_since_silence(self, current_time: float) -> float:
        """Get time since last silence ended."""
        if self.in_silence:
            return 0.0
        if self.last_silence_end is None:
            return current_time  # Never had silence
        return current_time - self.last_silence_end


@dataclass
class SoundMemory:
    """Tracks recent sound events and patterns."""
    recent_events: List[SoundEvent] = field(default_factory=list)
    patterns: Dict[str, PatternState] = field(default_factory=dict)
    silence_tracker: SilenceTracker = field(default_factory=SilenceTracker)
    cooldowns: Dict[str, float] = field(default_factory=dict)  # sound_id -> cooldown_until
    
    # Counts
    layer_counts: Dict[str, int] = field(default_factory=lambda: {
        'background': 0, 'periodic': 0, 'reactive': 0, 'anomalous': 0
    })
    frequency_counts: Dict[str, int] = field(default_factory=lambda: {
        'low': 0, 'low_mid': 0, 'mid': 0, 'mid_high': 0, 'high': 0, 'full': 0
    })
    
    retention_window: float = 60.0
    max_events: int = 100
    
    def add_event(self, event: SoundEvent) -> None:
        """Add a new sound event to memory."""
        self.recent_events.append(event)
        
        # Update pattern tracking
        if event.sound_id not in self.patterns:
            self.patterns[event.sound_id] = PatternState(event.sound_id)
        self.patterns[event.sound_id].add_occurrence(event.timestamp)
        
        # Update layer count
        if event.layer in self.layer_counts:
            self.layer_counts[event.layer] += 1
        
        # Trim if too many events
        if len(self.recent_events) > self.max_events:
            self.recent_events.pop(0)
    
    def end_event(self, sound_id: str, timestamp: float, 
                  end_type: EndType = EndType.NATURAL) -> None:
        """Mark a sound event as ended."""
        # Find the most recent matching event
        for event in reversed(self.recent_events):
            if event.sound_id == sound_id and not event.ended:
                event.ended = True
                event.end_type = end_type
                event.end_time = timestamp
                
                # Update layer count
                if event.layer in self.layer_counts:
                    self.layer_counts[event.layer] = max(0, self.layer_counts[event.layer] - 1)
                break
    
    def cleanup(self, current_time: float) -> None:
        """Remove old events and update patterns."""
        cutoff = current_time - self.retention_window
        
        # Remove old events
        self.recent_events = [e for e in self.recent_events if e.timestamp > cutoff]
        
        # Clean up patterns
        for pattern in self.patterns.values():
            pattern.clear_old(current_time, self.retention_window)
    
    def get_pattern(self, sound_id: str) -> Optional[PatternState]:
        """Get pattern state for a sound."""
        return self.patterns.get(sound_id)
    
    def is_on_cooldown(self, sound_id: str, current_time: float) -> bool:
        """Check if a sound is on cooldown."""
        if sound_id not in self.cooldowns:
            return False
        return current_time < self.cooldowns[sound_id]
    
    def set_cooldown(self, sound_id: str, until: float) -> None:
        """Set cooldown for a sound."""
        self.cooldowns[sound_id] = until
    
    def get_active_layer_count(self) -> int:
        """Get total number of active layers."""
        return sum(self.layer_counts.values())


# =============================================================================
# Environment State
# =============================================================================

@dataclass
class PopulationState:
    """Current population state for a region."""
    current_ratio: float = 0.0  # 0.0 to 1.0
    smoothed_ratio: float = 0.0
    target_sdi: float = 0.0
    region_type: Optional[str] = None  # For region overrides


@dataclass
class EnvironmentState:
    """Current environment state."""
    biome_id: str = "forest"
    biome_parameters: Optional[Any] = None  # BiomeParameters from config
    
    time_of_day: str = "day"
    hour: float = 12.0  # 0-24
    
    weather: str = "clear"
    weather_transition: Optional[float] = None  # Progress of weather change
    
    population: PopulationState = field(default_factory=PopulationState)
    
    # Optional features for specific biomes
    features: Dict[str, bool] = field(default_factory=lambda: {
        'water_present': False,
        'enclosed_space': False,
        'elevated': False,
    })
    
    def get_effective_density(self, base_density: float, 
                               weather_mod: float = 1.0,
                               time_mod: float = 1.0) -> float:
        """Calculate effective sound density with modifiers."""
        return base_density * weather_mod * time_mod


# =============================================================================
# SDI State
# =============================================================================

@dataclass
class SDIContributions:
    """Individual SDI factor contributions."""
    # Environmental
    biome_baseline: float = 0.0
    time_modifier: float = 0.0
    weather_modifier: float = 0.0
    
    # Discomfort
    density_overload: float = 0.0
    layer_conflict: float = 0.0
    rhythm_instability: float = 0.0
    silence_deprivation: float = 0.0
    contextual_mismatch: float = 0.0
    persistence: float = 0.0
    absence_after_pattern: float = 0.0
    
    # Comfort
    predictable_rhythm: float = 0.0
    appropriate_silence: float = 0.0
    layer_harmony: float = 0.0
    gradual_transition: float = 0.0
    resolution: float = 0.0
    environmental_coherence: float = 0.0
    
    def total(self) -> float:
        """Calculate total SDI from all contributions."""
        return (
            self.biome_baseline +
            self.time_modifier +
            self.weather_modifier +
            self.density_overload +
            self.layer_conflict +
            self.rhythm_instability +
            self.silence_deprivation +
            self.contextual_mismatch +
            self.persistence +
            self.absence_after_pattern +
            self.predictable_rhythm +
            self.appropriate_silence +
            self.layer_harmony +
            self.gradual_transition +
            self.resolution +
            self.environmental_coherence
        )
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for logging."""
        return {
            'biome_baseline': self.biome_baseline,
            'time_modifier': self.time_modifier,
            'weather_modifier': self.weather_modifier,
            'density_overload': self.density_overload,
            'layer_conflict': self.layer_conflict,
            'rhythm_instability': self.rhythm_instability,
            'silence_deprivation': self.silence_deprivation,
            'contextual_mismatch': self.contextual_mismatch,
            'persistence': self.persistence,
            'absence_after_pattern': self.absence_after_pattern,
            'predictable_rhythm': self.predictable_rhythm,
            'appropriate_silence': self.appropriate_silence,
            'layer_harmony': self.layer_harmony,
            'gradual_transition': self.gradual_transition,
            'resolution': self.resolution,
            'environmental_coherence': self.environmental_coherence,
        }
    
    def get_top_positive(self) -> tuple:
        """Get the highest positive contributor."""
        discomfort = {
            'density_overload': self.density_overload,
            'layer_conflict': self.layer_conflict,
            'rhythm_instability': self.rhythm_instability,
            'silence_deprivation': self.silence_deprivation,
            'contextual_mismatch': self.contextual_mismatch,
            'persistence': self.persistence,
            'absence_after_pattern': self.absence_after_pattern,
        }
        if not discomfort:
            return ('none', 0.0)
        top = max(discomfort.items(), key=lambda x: x[1])
        return top if top[1] > 0 else ('none', 0.0)
    
    def get_top_negative(self) -> tuple:
        """Get the most negative (comforting) contributor."""
        comfort = {
            'predictable_rhythm': self.predictable_rhythm,
            'appropriate_silence': self.appropriate_silence,
            'layer_harmony': self.layer_harmony,
            'gradual_transition': self.gradual_transition,
            'resolution': self.resolution,
            'environmental_coherence': self.environmental_coherence,
        }
        if not comfort:
            return ('none', 0.0)
        top = min(comfort.items(), key=lambda x: x[1])
        return top if top[1] < 0 else ('none', 0.0)


@dataclass
class SDIState:
    """Current SDI calculation state."""
    raw_sdi: float = 0.0
    smoothed_sdi: float = 0.0
    target_sdi: float = 0.0
    delta: float = 0.0
    delta_category: DeltaCategory = DeltaCategory.NONE
    
    contributions: SDIContributions = field(default_factory=SDIContributions)
    
    active_adjustments: List[str] = field(default_factory=list)
    adjustment_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def update(self, raw: float, smoothing_factor: float) -> None:
        """Update SDI with new raw value and smoothing."""
        self.raw_sdi = raw
        self.smoothed_sdi = self.smoothed_sdi + (raw - self.smoothed_sdi) * smoothing_factor
        self.delta = self.target_sdi - self.smoothed_sdi
    
    def categorize_delta(self, thresholds: Dict[str, float]) -> None:
        """Categorize the current delta."""
        abs_delta = abs(self.delta)
        
        if abs_delta < thresholds.get('small', 0.1):
            self.delta_category = DeltaCategory.NONE
        elif abs_delta < thresholds.get('medium', 0.2):
            self.delta_category = DeltaCategory.SMALL
        elif abs_delta < thresholds.get('large', 0.3):
            self.delta_category = DeltaCategory.MEDIUM
        elif abs_delta < thresholds.get('critical', 0.4):
            self.delta_category = DeltaCategory.LARGE
        else:
            self.delta_category = DeltaCategory.CRITICAL


# =============================================================================
# Master Simulation State
# =============================================================================

@dataclass
class SimulationState:
    """
    Top-level state container for the entire simulation.
    
    This is the main state object that gets passed around and updated
    each tick of the simulation.
    """
    tick: int = 0
    timestamp: float = 0.0
    running: bool = False
    
    environment: EnvironmentState = field(default_factory=EnvironmentState)
    sound_memory: SoundMemory = field(default_factory=SoundMemory)
    active_sounds: List[ActiveSound] = field(default_factory=list)
    sdi: SDIState = field(default_factory=SDIState)
    
    # Statistics
    total_sounds_played: int = 0
    sounds_by_layer: Dict[str, int] = field(default_factory=lambda: {
        'background': 0, 'periodic': 0, 'reactive': 0, 'anomalous': 0
    })
    
    def advance_tick(self, delta_time: float = 1.0) -> None:
        """Advance the simulation by one tick."""
        self.tick += 1
        self.timestamp += delta_time
    
    def add_active_sound(self, sound: ActiveSound) -> None:
        """Add a new active sound."""
        self.active_sounds.append(sound)
        self.total_sounds_played += 1
        if sound.layer in self.sounds_by_layer:
            self.sounds_by_layer[sound.layer] += 1
    
    def remove_active_sound(self, instance_id: str) -> Optional[ActiveSound]:
        """Remove an active sound by instance ID."""
        for i, sound in enumerate(self.active_sounds):
            if sound.instance_id == instance_id:
                return self.active_sounds.pop(i)
        return None
    
    def get_active_sound(self, instance_id: str) -> Optional[ActiveSound]:
        """Get an active sound by instance ID."""
        for sound in self.active_sounds:
            if sound.instance_id == instance_id:
                return sound
        return None
    
    def get_active_by_layer(self, layer: str) -> List[ActiveSound]:
        """Get all active sounds in a layer."""
        return [s for s in self.active_sounds if s.layer == layer]
    
    def get_active_count_by_layer(self) -> Dict[str, int]:
        """Get count of active sounds per layer."""
        counts = {'background': 0, 'periodic': 0, 'reactive': 0, 'anomalous': 0}
        for sound in self.active_sounds:
            if sound.layer in counts:
                counts[sound.layer] += 1
        return counts
    
    def cleanup_expired_sounds(self) -> List[ActiveSound]:
        """Remove and return all expired sounds."""
        expired = []
        remaining = []
        
        for sound in self.active_sounds:
            if sound.is_expired(self.timestamp):
                expired.append(sound)
            else:
                remaining.append(sound)
        
        self.active_sounds = remaining
        return expired
    
    def reset(self) -> None:
        """Reset state to initial values."""
        self.tick = 0
        self.timestamp = 0.0
        self.running = False
        self.environment = EnvironmentState()
        self.sound_memory = SoundMemory()
        self.active_sounds = []
        self.sdi = SDIState()
        self.total_sounds_played = 0
        self.sounds_by_layer = {
            'background': 0, 'periodic': 0, 'reactive': 0, 'anomalous': 0
        }
    
    def to_snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of current state for logging."""
        return {
            'tick': self.tick,
            'timestamp': self.timestamp,
            'biome': self.environment.biome_id,
            'time_of_day': self.environment.time_of_day,
            'weather': self.environment.weather,
            'population': self.environment.population.current_ratio,
            'active_sounds': len(self.active_sounds),
            'raw_sdi': self.sdi.raw_sdi,
            'smoothed_sdi': self.sdi.smoothed_sdi,
            'target_sdi': self.sdi.target_sdi,
            'delta': self.sdi.delta,
        }
