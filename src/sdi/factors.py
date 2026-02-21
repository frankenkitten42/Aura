"""
Discomfort factor calculations for the Living Soundscape Engine.

Calculates positive SDI contributions from:
- Density overload (too many sounds)
- Layer conflicts (incompatible sounds playing together)
- Rhythm instability (drifting patterns)
- Silence deprivation (too long without silence)
- Contextual mismatch (wrong sounds for time/weather/biome)
- Persistence (sounds playing too long)
- Absence after pattern (broken rhythmic expectations)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any

# Import types for type hints only - actual instances passed in
# This avoids circular imports


@dataclass
class DiscomfortResult:
    """Result of discomfort calculation with breakdown."""
    total: float = 0.0
    density_overload: float = 0.0
    layer_conflict: float = 0.0
    rhythm_instability: float = 0.0
    silence_deprivation: float = 0.0
    contextual_mismatch: float = 0.0
    persistence: float = 0.0
    absence_after_pattern: float = 0.0
    
    # Details for debugging
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'total': self.total,
            'density_overload': self.density_overload,
            'layer_conflict': self.layer_conflict,
            'rhythm_instability': self.rhythm_instability,
            'silence_deprivation': self.silence_deprivation,
            'contextual_mismatch': self.contextual_mismatch,
            'persistence': self.persistence,
            'absence_after_pattern': self.absence_after_pattern,
        }


class DiscomfortCalculator:
    """
    Calculates discomfort (positive SDI) factors.
    
    Each factor has:
    - A base weight (contribution per occurrence)
    - Optional modifiers (biome-specific adjustments)
    - Optional caps (maximum contribution)
    
    Example:
        >>> calc = DiscomfortCalculator(config)
        >>> result = calc.calculate(
        ...     sound_memory=memory,
        ...     silence_tracker=silence,
        ...     pattern_memory=patterns,
        ...     environment=env,
        ...     current_time=100.0
        ... )
        >>> result.total
        0.35
    """
    
    # Default weights (can be overridden by config)
    DEFAULT_WEIGHTS = {
        'density_overload': 0.15,
        'layer_conflict': 0.25,
        'rhythm_instability': 0.10,
        'silence_deprivation': 0.08,
        'contextual_mismatch': 0.20,
        'persistence': 0.05,
        'absence_after_pattern': 0.15,
    }
    
    # Default caps
    DEFAULT_CAPS = {
        'density_overload': 0.45,
        'layer_conflict': 0.50,
        'rhythm_instability': 0.30,
        'silence_deprivation': 0.40,
        'contextual_mismatch': 0.40,
        'persistence': 0.30,
        'absence_after_pattern': 0.30,
    }
    
    # Conflict severity multipliers
    SEVERITY_MULTIPLIERS = {
        'low': 0.5,
        'medium': 1.0,
        'high': 1.5,
    }
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize the calculator.
        
        Args:
            config: LSEConfig object (optional, uses defaults if not provided)
        """
        self.config = config
        self._load_config()
    
    def _load_config(self) -> None:
        """Load weights and caps from config or use defaults."""
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self.caps = self.DEFAULT_CAPS.copy()
        self.biome_adjustments: Dict[str, Dict[str, float]] = {}
        
        # Sound configs for persistence checking
        self.sound_configs: Dict[str, Any] = {}
        
        # Conflict definitions
        self.sound_conflicts: List[Any] = []
        self.tag_conflicts: List[Any] = []
        
        if self.config is not None:
            # Load from SDI config
            if hasattr(self.config, 'sdi'):
                sdi = self.config.sdi
                
                # Load discomfort factor weights
                for factor_id, factor in sdi.discomfort_factors.items():
                    if factor_id in self.weights:
                        self.weights[factor_id] = factor.base_weight
                    if factor.cap is not None and factor_id in self.caps:
                        self.caps[factor_id] = factor.cap
                
                # Load biome adjustments
                self.biome_adjustments = sdi.biome_adjustments
            
            # Load sound configs
            if hasattr(self.config, 'sounds'):
                self.sound_configs = self.config.sounds
            
            # Load conflict definitions
            if hasattr(self.config, 'conflicts'):
                self.sound_conflicts = self.config.conflicts.sound_conflicts
                self.tag_conflicts = self.config.conflicts.tag_conflicts
    
    def calculate(self,
                  sound_memory: Any,
                  silence_tracker: Any,
                  pattern_memory: Any,
                  environment: Any,
                  current_time: float) -> DiscomfortResult:
        """
        Calculate all discomfort factors.
        
        Args:
            sound_memory: Current sound memory state
            silence_tracker: Current silence tracking state
            pattern_memory: Current pattern memory state
            environment: Current environment state
            current_time: Current simulation time
            
        Returns:
            DiscomfortResult with all factor contributions
        """
        result = DiscomfortResult()
        biome_id = getattr(environment, 'biome_id', 'forest')
        
        # Calculate each factor
        result.density_overload = self._calc_density_overload(
            sound_memory, environment, biome_id
        )
        
        result.layer_conflict = self._calc_layer_conflict(
            sound_memory, biome_id
        )
        
        result.rhythm_instability = self._calc_rhythm_instability(
            pattern_memory, biome_id
        )
        
        result.silence_deprivation = self._calc_silence_deprivation(
            silence_tracker, environment, current_time, biome_id
        )
        
        result.contextual_mismatch = self._calc_contextual_mismatch(
            sound_memory, environment, biome_id
        )
        
        result.persistence = self._calc_persistence(
            sound_memory, current_time, biome_id
        )
        
        result.absence_after_pattern = self._calc_absence_after_pattern(
            pattern_memory, current_time, biome_id
        )
        
        # Sum total
        result.total = (
            result.density_overload +
            result.layer_conflict +
            result.rhythm_instability +
            result.silence_deprivation +
            result.contextual_mismatch +
            result.persistence +
            result.absence_after_pattern
        )
        
        return result
    
    def _get_biome_modifier(self, factor: str, biome_id: str) -> float:
        """Get biome-specific modifier for a factor."""
        if biome_id in self.biome_adjustments:
            return self.biome_adjustments[biome_id].get(factor, 1.0)
        return 1.0
    
    def _apply_cap(self, value: float, factor: str) -> float:
        """Apply cap to a factor value."""
        cap = self.caps.get(factor, 1.0)
        return min(value, cap)
    
    # =========================================================================
    # Factor Calculations
    # =========================================================================
    
    def _calc_density_overload(self, sound_memory: Any,
                                environment: Any, biome_id: str) -> float:
        """
        Calculate density overload factor.
        
        Triggered when active sounds exceed biome's layer capacity.
        Weight: 0.15 per excess layer
        """
        # Get layer capacity from environment/biome
        capacity = 4  # Default
        if hasattr(environment, 'biome_parameters') and environment.biome_parameters:
            capacity = getattr(environment.biome_parameters, 'layer_capacity', 4)
        
        active_count = sound_memory.active_count
        excess = max(0, active_count - capacity)
        
        if excess == 0:
            return 0.0
        
        base = self.weights['density_overload'] * excess
        modified = base * self._get_biome_modifier('density_overload', biome_id)
        
        return self._apply_cap(modified, 'density_overload')
    
    def _calc_layer_conflict(self, sound_memory: Any,
                              biome_id: str) -> float:
        """
        Calculate layer conflict factor.
        
        Triggered when conflicting sounds play simultaneously.
        Weight: 0.25 per conflict (with severity multiplier)
        """
        total = 0.0
        active_sounds = sound_memory.get_active_sounds()
        active_ids = {s.sound_id for s in active_sounds}
        active_tags = sound_memory.get_active_tags()
        
        # Check sound ID conflicts
        for conflict in self.sound_conflicts:
            if conflict.sound_a in active_ids and conflict.sound_b in active_ids:
                severity_mult = self.SEVERITY_MULTIPLIERS.get(conflict.severity, 1.0)
                total += self.weights['layer_conflict'] * severity_mult
        
        # Check tag conflicts
        for conflict in self.tag_conflicts:
            if conflict.tag_a in active_tags and conflict.tag_b in active_tags:
                # Count actual conflicting pairs
                pairs = sound_memory.get_active_with_tag_pair(
                    conflict.tag_a, conflict.tag_b
                )
                if pairs:
                    severity_mult = self.SEVERITY_MULTIPLIERS.get(conflict.severity, 1.0)
                    total += self.weights['layer_conflict'] * severity_mult
        
        modified = total * self._get_biome_modifier('layer_conflict', biome_id)
        return self._apply_cap(modified, 'layer_conflict')
    
    def _calc_rhythm_instability(self, pattern_memory: Any,
                                  biome_id: str) -> float:
        """
        Calculate rhythm instability factor.
        
        Triggered by drifting patterns (CV between 0.15 and 0.40).
        Weight: 0.10 per drifting pattern
        """
        drifting = pattern_memory.get_drifting_patterns()
        
        if not drifting:
            return 0.0
        
        total = 0.0
        for pattern in drifting:
            # Scale by how much drift
            drift_amount = pattern.get_drift_amount()
            # More drift = more discomfort (up to 1.5x)
            drift_mult = 1.0 + min(drift_amount, 0.5)
            total += self.weights['rhythm_instability'] * drift_mult
        
        modified = total * self._get_biome_modifier('rhythm_instability', biome_id)
        return self._apply_cap(modified, 'rhythm_instability')
    
    def _calc_silence_deprivation(self, silence_tracker: Any,
                                   environment: Any, current_time: float,
                                   biome_id: str) -> float:
        """
        Calculate silence deprivation factor.
        
        Triggered when time since silence exceeds biome's tolerance.
        Weight: 0.08 per tolerance-length exceeded
        """
        # Get silence tolerance from environment
        tolerance = 5.0  # Default
        if hasattr(environment, 'biome_parameters') and environment.biome_parameters:
            tolerance = getattr(environment.biome_parameters, 'silence_tolerance', 5.0)
        
        deprivation_factor = silence_tracker.get_deprivation_factor(
            current_time, tolerance
        )
        
        if deprivation_factor <= 0:
            return 0.0
        
        base = self.weights['silence_deprivation'] * deprivation_factor
        modified = base * self._get_biome_modifier('silence_deprivation', biome_id)
        
        return self._apply_cap(modified, 'silence_deprivation')
    
    def _calc_contextual_mismatch(self, sound_memory: Any,
                                   environment: Any, biome_id: str) -> float:
        """
        Calculate contextual mismatch factor.
        
        Triggered by sounds that don't belong in current context
        (wrong time of day, weather, or biome).
        Weight: 0.20 per mismatch
        """
        total = 0.0
        active_sounds = sound_memory.get_active_sounds()
        
        time_of_day = getattr(environment, 'time_of_day', 'day')
        weather = getattr(environment, 'weather', 'clear')
        
        for event in active_sounds:
            sound_config = self.sound_configs.get(event.sound_id)
            if sound_config is None:
                continue
            
            mismatches = 0
            
            # Check time constraints
            time_constraints = getattr(sound_config, 'time_constraints', ['all'])
            if 'all' not in time_constraints and time_of_day not in time_constraints:
                mismatches += 1
            
            # Check weather constraints
            weather_constraints = getattr(sound_config, 'weather_constraints', None)
            if weather_constraints:
                excluded = getattr(weather_constraints, 'excluded', [])
                required = getattr(weather_constraints, 'required', [])
                
                if weather in excluded:
                    mismatches += 1
                elif required and weather not in required:
                    mismatches += 1
            
            total += self.weights['contextual_mismatch'] * mismatches
        
        modified = total * self._get_biome_modifier('contextual_mismatch', biome_id)
        return self._apply_cap(modified, 'contextual_mismatch')
    
    def _calc_persistence(self, sound_memory: Any,
                          current_time: float, biome_id: str) -> float:
        """
        Calculate persistence factor.
        
        Triggered when sounds play longer than their natural duration.
        Weight: 0.05 per 10 seconds of overstay
        """
        total = 0.0
        active_sounds = sound_memory.get_active_sounds()
        
        for event in active_sounds:
            sound_config = self.sound_configs.get(event.sound_id)
            if sound_config is None:
                continue
            
            natural_duration = getattr(sound_config, 'natural_duration', None)
            if natural_duration is None:
                continue
            
            overstay = event.overstayed(current_time, natural_duration)
            if overstay > 0:
                # 0.05 per 10 seconds
                overstay_units = overstay / 10.0
                total += self.weights['persistence'] * overstay_units
        
        modified = total * self._get_biome_modifier('persistence', biome_id)
        return self._apply_cap(modified, 'persistence')
    
    def _calc_absence_after_pattern(self, pattern_memory: Any,
                                     current_time: float, biome_id: str) -> float:
        """
        Calculate absence after pattern factor.
        
        Triggered when an expected rhythmic sound doesn't occur.
        Weight: 0.15 per broken pattern (decays over 30 seconds)
        """
        decay_time = 30.0  # Seconds until contribution fades
        
        contributions = pattern_memory.get_break_contributions(
            current_time, decay_time
        )
        
        if not contributions:
            return 0.0
        
        total = 0.0
        for sound_id, factor in contributions:
            total += self.weights['absence_after_pattern'] * factor
        
        modified = total * self._get_biome_modifier('absence_after_pattern', biome_id)
        return self._apply_cap(modified, 'absence_after_pattern')
