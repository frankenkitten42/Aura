"""
Main SDI Calculator for the Living Soundscape Engine.

Combines discomfort and comfort factors, applies smoothing, and
determines the target SDI based on population.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

from .factors import DiscomfortCalculator, DiscomfortResult
from .comfort import ComfortCalculator, ComfortResult

# Memory types imported implicitly via Any to avoid circular imports


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """Constrain a value to a range."""
    return max(min_val, min(max_val, value))


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + (b - a) * t


@dataclass
class SDIResult:
    """
    Complete SDI calculation result.
    
    Contains raw and smoothed SDI values, target SDI, delta,
    and full breakdown of contributing factors.
    """
    # Core values
    raw_sdi: float = 0.0
    smoothed_sdi: float = 0.0
    target_sdi: float = 0.0
    delta: float = 0.0  # target - smoothed
    
    # Environmental baselines
    biome_baseline: float = 0.0
    time_modifier: float = 0.0
    weather_modifier: float = 0.0
    
    # Factor breakdowns
    discomfort: DiscomfortResult = field(default_factory=DiscomfortResult)
    comfort: ComfortResult = field(default_factory=ComfortResult)
    
    # Delta categorization
    delta_category: str = "none"  # none, small, medium, large, critical
    
    # Top contributors
    top_positive: Tuple[str, float] = ("none", 0.0)
    top_negative: Tuple[str, float] = ("none", 0.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'raw_sdi': self.raw_sdi,
            'smoothed_sdi': self.smoothed_sdi,
            'target_sdi': self.target_sdi,
            'delta': self.delta,
            'delta_category': self.delta_category,
            'biome_baseline': self.biome_baseline,
            'time_modifier': self.time_modifier,
            'weather_modifier': self.weather_modifier,
            'discomfort': self.discomfort.to_dict(),
            'comfort': self.comfort.to_dict(),
            'top_positive': self.top_positive,
            'top_negative': self.top_negative,
        }
    
    def to_csv_row(self) -> Dict[str, float]:
        """Get values for CSV logging."""
        return {
            'raw_sdi': self.raw_sdi,
            'smoothed_sdi': self.smoothed_sdi,
            'target_sdi': self.target_sdi,
            'delta': self.delta,
            'biome_baseline': self.biome_baseline,
            'discomfort_total': self.discomfort.total,
            'comfort_total': self.comfort.total,
            'density_overload': self.discomfort.density_overload,
            'layer_conflict': self.discomfort.layer_conflict,
            'rhythm_instability': self.discomfort.rhythm_instability,
            'silence_deprivation': self.discomfort.silence_deprivation,
            'contextual_mismatch': self.discomfort.contextual_mismatch,
            'persistence': self.discomfort.persistence,
            'absence_after_pattern': self.discomfort.absence_after_pattern,
            'predictable_rhythm': self.comfort.predictable_rhythm,
            'appropriate_silence': self.comfort.appropriate_silence,
            'layer_harmony': self.comfort.layer_harmony,
            'gradual_transition': self.comfort.gradual_transition,
            'resolution': self.comfort.resolution,
            'environmental_coherence': self.comfort.environmental_coherence,
        }


class SDICalculator:
    """
    Main SDI calculator that orchestrates all factor calculations.
    
    Responsibilities:
    - Calculate discomfort factors (positive SDI)
    - Calculate comfort factors (negative SDI)
    - Apply environmental baselines and modifiers
    - Calculate target SDI from population
    - Apply smoothing to prevent jarring changes
    - Categorize delta for adjustment decisions
    
    Example:
        >>> calc = SDICalculator(config)
        >>> result = calc.calculate(
        ...     sound_memory=memory,
        ...     silence_tracker=silence,
        ...     pattern_memory=patterns,
        ...     environment=env,
        ...     current_time=100.0,
        ...     population_ratio=0.5
        ... )
        >>> result.smoothed_sdi
        0.15
    """
    
    # SDI range
    SDI_MIN = -1.0
    SDI_MAX = 1.0
    OPERATIONAL_MAX = 0.8  # Stay below conscious awareness
    
    # Delta thresholds
    DELTA_THRESHOLDS = {
        'small': 0.1,
        'medium': 0.2,
        'large': 0.3,
        'critical': 0.4,
    }
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize the SDI calculator.
        
        Args:
            config: LSEConfig object (optional)
        """
        self.config = config
        
        # Create sub-calculators
        self.discomfort_calc = DiscomfortCalculator(config)
        self.comfort_calc = ComfortCalculator(config)
        
        # Smoothing state
        self._previous_smoothed: float = 0.0
        self._smoothing_factor: float = 0.2
        
        # Population curve
        self._population_points: List[Tuple[float, float]] = [
            (0.0, -0.30),
            (0.2, 0.00),
            (0.5, 0.20),
            (0.8, 0.50),
            (1.0, 0.80),
        ]
        
        # Weather/time modifiers
        self._weather_sdi_mods: Dict[str, float] = {}
        self._time_sdi_mods: Dict[str, float] = {}
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration."""
        if self.config is None:
            return
        
        # Load SDI settings
        if hasattr(self.config, 'sdi'):
            sdi = self.config.sdi
            settings = sdi.global_settings
            self._smoothing_factor = settings.smoothing_factor
        
        # Load population curve
        if hasattr(self.config, 'population'):
            pop = self.config.population
            if pop.curve.points:
                self._population_points = [
                    (p.population, p.target_sdi) for p in pop.curve.points
                ]
            
            # Load delta thresholds
            self.DELTA_THRESHOLDS = {
                'small': pop.delta_thresholds.small,
                'medium': pop.delta_thresholds.medium,
                'large': pop.delta_thresholds.large,
                'critical': pop.delta_thresholds.critical,
            }
        
        # Load weather modifiers
        if hasattr(self.config, 'weather_modifiers'):
            for mod_id, mod in self.config.weather_modifiers.items():
                self._weather_sdi_mods[mod_id] = mod.sdi_modifier
        
        # Load time modifiers
        if hasattr(self.config, 'time_modifiers'):
            for mod_id, mod in self.config.time_modifiers.items():
                self._time_sdi_mods[mod_id] = mod.sdi_modifier
    
    def calculate(self,
                  sound_memory: Any,
                  silence_tracker: Any,
                  pattern_memory: Any,
                  environment: Any,
                  current_time: float,
                  population_ratio: float = 0.0,
                  recent_transitions: int = 0,
                  recent_resolutions: int = 0,
                  pressure_state: Any = None) -> SDIResult:
        """
        Perform complete SDI calculation.
        
        Args:
            sound_memory: Current sound memory state
            silence_tracker: Current silence tracking state
            pattern_memory: Current pattern memory state
            environment: Current environment state
            current_time: Current simulation time
            population_ratio: Current population as ratio (0.0-1.0)
            recent_transitions: Number of smooth transitions recently
            recent_resolutions: Number of tension resolutions recently
            pressure_state: Population pressure state (optional)
            
        Returns:
            Complete SDIResult with all calculations
        """
        result = SDIResult()
        
        # Get environment values
        biome_id = getattr(environment, 'biome_id', 'forest')
        time_of_day = getattr(environment, 'time_of_day', 'day')
        weather = getattr(environment, 'weather', 'clear')
        
        # Calculate baselines
        result.biome_baseline = self._get_biome_baseline(environment)
        result.time_modifier = self._time_sdi_mods.get(time_of_day, 0.0)
        result.weather_modifier = self._weather_sdi_mods.get(weather, 0.0)
        
        # Calculate discomfort factors
        result.discomfort = self.discomfort_calc.calculate(
            sound_memory=sound_memory,
            silence_tracker=silence_tracker,
            pattern_memory=pattern_memory,
            environment=environment,
            current_time=current_time,
        )
        
        # Calculate comfort factors
        result.comfort = self.comfort_calc.calculate(
            sound_memory=sound_memory,
            silence_tracker=silence_tracker,
            pattern_memory=pattern_memory,
            environment=environment,
            current_time=current_time,
            recent_transitions=recent_transitions,
            recent_resolutions=recent_resolutions,
        )
        
        # Calculate pressure-based discomfort
        pressure_discomfort = 0.0
        if pressure_state is not None:
            # Direct discomfort from pressure system
            # This scales with the discomfort boost and static intensity
            pressure_discomfort = (
                pressure_state.discomfort_boost * 0.3 +    # Up to +0.30 from boost
                pressure_state.static_intensity * 0.4 +     # Up to +0.40 from static
                pressure_state.wildlife_suppression * 0.1   # Up to +0.10 from silence
            )
        
        # Combine all factors into raw SDI
        result.raw_sdi = (
            result.biome_baseline +
            result.time_modifier +
            result.weather_modifier +
            result.discomfort.total +
            result.comfort.total +
            pressure_discomfort
        )
        
        # Clamp to valid range
        result.raw_sdi = _clamp(result.raw_sdi, self.SDI_MIN, self.OPERATIONAL_MAX)
        
        # Apply smoothing
        result.smoothed_sdi = self._apply_smoothing(result.raw_sdi)
        
        # Calculate target from population
        result.target_sdi = self._calculate_target_sdi(population_ratio)
        
        # Calculate delta
        result.delta = result.target_sdi - result.smoothed_sdi
        
        # Categorize delta
        result.delta_category = self._categorize_delta(result.delta)
        
        # Find top contributors
        result.top_positive = self._find_top_positive(result)
        result.top_negative = self._find_top_negative(result)
        
        return result
    
    def _get_biome_baseline(self, environment: Any) -> float:
        """Get SDI baseline from biome parameters."""
        if hasattr(environment, 'biome_parameters') and environment.biome_parameters:
            return getattr(environment.biome_parameters, 'sdi_baseline', 0.0)
        return 0.0
    
    def _apply_smoothing(self, raw_sdi: float) -> float:
        """Apply exponential smoothing to prevent jarring changes."""
        smoothed = self._previous_smoothed + (raw_sdi - self._previous_smoothed) * self._smoothing_factor
        self._previous_smoothed = smoothed
        return smoothed
    
    def _calculate_target_sdi(self, population_ratio: float) -> float:
        """
        Calculate target SDI from population using piecewise linear interpolation.
        
        Args:
            population_ratio: Current population as ratio (0.0-1.0)
            
        Returns:
            Target SDI value
        """
        population_ratio = _clamp(population_ratio, 0.0, 1.0)
        
        # Find the two points to interpolate between
        for i in range(len(self._population_points) - 1):
            p1_pop, p1_sdi = self._population_points[i]
            p2_pop, p2_sdi = self._population_points[i + 1]
            
            if p1_pop <= population_ratio <= p2_pop:
                # Interpolate
                if p2_pop == p1_pop:
                    return p1_sdi
                t = (population_ratio - p1_pop) / (p2_pop - p1_pop)
                return _lerp(p1_sdi, p2_sdi, t)
        
        # Fallback to last point
        return self._population_points[-1][1]
    
    def _categorize_delta(self, delta: float) -> str:
        """Categorize the SDI delta magnitude."""
        abs_delta = abs(delta)
        
        if abs_delta < self.DELTA_THRESHOLDS['small']:
            return 'none'
        elif abs_delta < self.DELTA_THRESHOLDS['medium']:
            return 'small'
        elif abs_delta < self.DELTA_THRESHOLDS['large']:
            return 'medium'
        elif abs_delta < self.DELTA_THRESHOLDS['critical']:
            return 'large'
        else:
            return 'critical'
    
    def _find_top_positive(self, result: SDIResult) -> Tuple[str, float]:
        """Find the largest positive (discomfort) contributor."""
        discomfort = result.discomfort
        candidates = [
            ('density_overload', discomfort.density_overload),
            ('layer_conflict', discomfort.layer_conflict),
            ('rhythm_instability', discomfort.rhythm_instability),
            ('silence_deprivation', discomfort.silence_deprivation),
            ('contextual_mismatch', discomfort.contextual_mismatch),
            ('persistence', discomfort.persistence),
            ('absence_after_pattern', discomfort.absence_after_pattern),
        ]
        
        # Find max positive value
        top = max(candidates, key=lambda x: x[1])
        if top[1] > 0:
            return top
        return ('none', 0.0)
    
    def _find_top_negative(self, result: SDIResult) -> Tuple[str, float]:
        """Find the largest negative (comfort) contributor."""
        comfort = result.comfort
        candidates = [
            ('predictable_rhythm', comfort.predictable_rhythm),
            ('appropriate_silence', comfort.appropriate_silence),
            ('layer_harmony', comfort.layer_harmony),
            ('gradual_transition', comfort.gradual_transition),
            ('resolution', comfort.resolution),
            ('environmental_coherence', comfort.environmental_coherence),
        ]
        
        # Find min (most negative) value
        top = min(candidates, key=lambda x: x[1])
        if top[1] < 0:
            return top
        return ('none', 0.0)
    
    def reset(self) -> None:
        """Reset calculator state."""
        self._previous_smoothed = 0.0
    
    def set_smoothed_sdi(self, value: float) -> None:
        """Set the smoothed SDI value (for state restoration)."""
        self._previous_smoothed = value
    
    def get_population_target(self, population_ratio: float) -> float:
        """Public method to get target SDI for a population ratio."""
        return self._calculate_target_sdi(population_ratio)
    
    def get_delta_thresholds(self) -> Dict[str, float]:
        """Get the delta category thresholds."""
        return self.DELTA_THRESHOLDS.copy()
