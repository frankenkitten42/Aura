"""
Comfort factor calculations for the Living Soundscape Engine.

Calculates negative SDI contributions from:
- Predictable rhythm (stable, consistent patterns)
- Appropriate silence (well-timed silence gaps)
- Layer harmony (complementary sounds playing together)
- Gradual transition (smooth crossfades between sounds)
- Resolution (tension resolving naturally)
- Environmental coherence (soundscape matches biome)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any

# Types imported implicitly via Any to avoid circular imports


@dataclass
class ComfortResult:
    """Result of comfort calculation with breakdown."""
    total: float = 0.0
    predictable_rhythm: float = 0.0
    appropriate_silence: float = 0.0
    layer_harmony: float = 0.0
    gradual_transition: float = 0.0
    resolution: float = 0.0
    environmental_coherence: float = 0.0
    
    # Details for debugging
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'total': self.total,
            'predictable_rhythm': self.predictable_rhythm,
            'appropriate_silence': self.appropriate_silence,
            'layer_harmony': self.layer_harmony,
            'gradual_transition': self.gradual_transition,
            'resolution': self.resolution,
            'environmental_coherence': self.environmental_coherence,
        }


class ComfortCalculator:
    """
    Calculates comfort (negative SDI) factors.
    
    Comfort factors reduce the SDI, making the soundscape more pleasant.
    All values are negative (or zero).
    
    Example:
        >>> calc = ComfortCalculator(config)
        >>> result = calc.calculate(
        ...     sound_memory=memory,
        ...     silence_tracker=silence,
        ...     pattern_memory=patterns,
        ...     environment=env,
        ...     current_time=100.0
        ... )
        >>> result.total
        -0.25
    """
    
    # Default weights (negative values)
    DEFAULT_WEIGHTS = {
        'predictable_rhythm': -0.10,
        'appropriate_silence': -0.05,
        'layer_harmony': -0.08,
        'gradual_transition': -0.10,
        'resolution': -0.15,
        'environmental_coherence': -0.05,
    }
    
    # Default caps (minimum values, more negative = more comfort)
    DEFAULT_CAPS = {
        'predictable_rhythm': -0.30,
        'appropriate_silence': -0.20,
        'layer_harmony': -0.30,
        'gradual_transition': -0.20,
        'resolution': -0.25,
        'environmental_coherence': -0.10,
    }
    
    # Harmony strength multipliers
    HARMONY_MULTIPLIERS = {
        'weak': 0.5,
        'medium': 1.0,
        'strong': 1.5,
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
        
        # Harmony pair definitions
        self.harmony_pairs: List[Any] = []
        self.tag_harmonies: Dict[str, List[str]] = {}
        
        # Biome sound pools for coherence checking
        self.biome_sounds: Dict[str, Set[str]] = {}
        
        if self.config is not None:
            # Load from SDI config
            if hasattr(self.config, 'sdi'):
                sdi = self.config.sdi
                
                # Load comfort factor weights
                for factor_id, factor in sdi.comfort_factors.items():
                    if factor_id in self.weights:
                        self.weights[factor_id] = -abs(factor.base_weight)  # Ensure negative
                    if factor.cap is not None and factor_id in self.caps:
                        self.caps[factor_id] = -abs(factor.cap)  # Ensure negative
            
            # Load harmony definitions
            if hasattr(self.config, 'conflicts'):
                self.harmony_pairs = self.config.conflicts.harmony_pairs
            
            # Load biome sound pools
            if hasattr(self.config, 'biomes'):
                for biome_id, biome in self.config.biomes.items():
                    self.biome_sounds[biome_id] = set(biome.sound_pool)
        
        # Build tag harmony lookup
        self._build_tag_harmonies()
    
    def _build_tag_harmonies(self) -> None:
        """Build lookup for tag-based harmonies."""
        # Common tag harmonies (sounds with these tags complement each other)
        self.tag_harmonies = {
            'water': ['water', 'coastal'],
            'wind': ['foliage', 'weather'],
            'organic': ['organic', 'animal'],
            'night': ['night', 'nocturnal'],
        }
    
    def calculate(self,
                  sound_memory: Any,
                  silence_tracker: Any,
                  pattern_memory: Any,
                  environment: Any,
                  current_time: float,
                  recent_transitions: int = 0,
                  recent_resolutions: int = 0) -> ComfortResult:
        """
        Calculate all comfort factors.
        
        Args:
            sound_memory: Current sound memory state
            silence_tracker: Current silence tracking state
            pattern_memory: Current pattern memory state
            environment: Current environment state
            current_time: Current simulation time
            recent_transitions: Number of smooth transitions in recent window
            recent_resolutions: Number of tension resolutions in recent window
            
        Returns:
            ComfortResult with all factor contributions (all <= 0)
        """
        result = ComfortResult()
        biome_id = getattr(environment, 'biome_id', 'forest')
        
        # Calculate each factor
        result.predictable_rhythm = self._calc_predictable_rhythm(
            pattern_memory
        )
        
        result.appropriate_silence = self._calc_appropriate_silence(
            silence_tracker, environment, current_time
        )
        
        result.layer_harmony = self._calc_layer_harmony(
            sound_memory
        )
        
        result.gradual_transition = self._calc_gradual_transition(
            recent_transitions
        )
        
        result.resolution = self._calc_resolution(
            recent_resolutions
        )
        
        result.environmental_coherence = self._calc_environmental_coherence(
            sound_memory, biome_id
        )
        
        # Sum total (all values should be <= 0)
        result.total = (
            result.predictable_rhythm +
            result.appropriate_silence +
            result.layer_harmony +
            result.gradual_transition +
            result.resolution +
            result.environmental_coherence
        )
        
        return result
    
    def _apply_cap(self, value: float, factor: str) -> float:
        """Apply cap to a factor value (more negative caps)."""
        cap = self.caps.get(factor, -1.0)
        # value is negative, cap is negative
        # We want max(value, cap) since both are negative
        return max(value, cap)
    
    # =========================================================================
    # Factor Calculations
    # =========================================================================
    
    def _calc_predictable_rhythm(self, pattern_memory: Any) -> float:
        """
        Calculate predictable rhythm comfort factor.
        
        Triggered by stable, rhythmic patterns.
        Weight: -0.10 per stable pattern
        """
        rhythmic = pattern_memory.get_rhythmic_patterns()
        
        if not rhythmic:
            return 0.0
        
        total = 0.0
        for pattern in rhythmic:
            # Very stable patterns (low CV) contribute more
            stability_bonus = 1.0
            if pattern.cv < 0.05:  # Very stable
                stability_bonus = 1.3
            elif pattern.cv < 0.08:  # Quite stable
                stability_bonus = 1.15
            
            total += self.weights['predictable_rhythm'] * stability_bonus
        
        return self._apply_cap(total, 'predictable_rhythm')
    
    def _calc_appropriate_silence(self, silence_tracker: Any,
                                   environment: Any,
                                   current_time: float) -> float:
        """
        Calculate appropriate silence comfort factor.
        
        Triggered by well-timed silence gaps (50-150% of biome tolerance).
        Weight: -0.05 per appropriate gap in recent window
        """
        # Get silence tolerance from environment
        tolerance = 5.0
        if hasattr(environment, 'biome_parameters') and environment.biome_parameters:
            tolerance = getattr(environment.biome_parameters, 'silence_tolerance', 5.0)
        
        # Count appropriate gaps in last 60 seconds
        window = 60.0
        count = silence_tracker.count_appropriate_recent(window, current_time)
        
        if count == 0:
            return 0.0
        
        total = self.weights['appropriate_silence'] * count
        return self._apply_cap(total, 'appropriate_silence')
    
    def _calc_layer_harmony(self, sound_memory: Any) -> float:
        """
        Calculate layer harmony comfort factor.
        
        Triggered by complementary sounds playing together.
        Weight: -0.08 per harmony pair active
        """
        total = 0.0
        found_pairs: Set[tuple] = set()
        
        # Check explicit harmony pairs
        for pair in self.harmony_pairs:
            if sound_memory.check_sound_pair_active(pair.sound_a, pair.sound_b):
                # Avoid double counting
                pair_key = tuple(sorted([pair.sound_a, pair.sound_b]))
                if pair_key not in found_pairs:
                    found_pairs.add(pair_key)
                    strength_mult = self.HARMONY_MULTIPLIERS.get(pair.strength, 1.0)
                    total += self.weights['layer_harmony'] * strength_mult
        
        # Check tag-based harmonies
        active_tags = sound_memory.get_active_tags()
        for base_tag, harmonious_tags in self.tag_harmonies.items():
            if base_tag in active_tags:
                for other_tag in harmonious_tags:
                    if other_tag in active_tags and other_tag != base_tag:
                        # Check if we actually have sounds with both tags
                        pairs = sound_memory.get_active_with_tag_pair(base_tag, other_tag)
                        if pairs:
                            tag_key = tuple(sorted([base_tag, other_tag]))
                            if tag_key not in found_pairs:
                                found_pairs.add(tag_key)
                                total += self.weights['layer_harmony'] * 0.7  # Weaker than explicit
        
        return self._apply_cap(total, 'layer_harmony')
    
    def _calc_gradual_transition(self, recent_transitions: int) -> float:
        """
        Calculate gradual transition comfort factor.
        
        Triggered by smooth crossfades (not abrupt starts/stops).
        Weight: -0.10 per smooth transition
        
        Note: Transition tracking must be done externally and passed in,
        as this requires audio playback awareness.
        """
        if recent_transitions == 0:
            return 0.0
        
        total = self.weights['gradual_transition'] * recent_transitions
        return self._apply_cap(total, 'gradual_transition')
    
    def _calc_resolution(self, recent_resolutions: int) -> float:
        """
        Calculate resolution comfort factor.
        
        Triggered when tension resolves (e.g., storm ending, threat passing).
        Weight: -0.15 per resolution
        
        Note: Resolution tracking must be done externally and passed in,
        as this requires context awareness.
        """
        if recent_resolutions == 0:
            return 0.0
        
        total = self.weights['resolution'] * recent_resolutions
        return self._apply_cap(total, 'resolution')
    
    def _calc_environmental_coherence(self, sound_memory: Any,
                                       biome_id: str) -> float:
        """
        Calculate environmental coherence comfort factor.
        
        Triggered when all active sounds belong to the current biome's
        sound pool. Constant comfort while maintained.
        Weight: -0.05 (constant, not per-sound)
        """
        biome_sounds = self.biome_sounds.get(biome_id, set())
        
        if not biome_sounds:
            # No biome definition, assume coherent
            return self.weights['environmental_coherence']
        
        active_sounds = sound_memory.get_active_sounds()
        
        if not active_sounds:
            # No sounds = coherent (silence is always coherent)
            return self.weights['environmental_coherence']
        
        # Check if all active sounds belong to biome
        for event in active_sounds:
            if event.sound_id not in biome_sounds:
                # Found a sound that doesn't belong
                return 0.0
        
        # All sounds are coherent
        return self._apply_cap(
            self.weights['environmental_coherence'],
            'environmental_coherence'
        )
