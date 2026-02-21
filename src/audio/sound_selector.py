"""
Sound selection for the Living Soundscape Engine.

Handles filtering, probability calculation, and selection of sounds
based on current context (biome, time, weather) and SDI adjustments.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
import uuid


@dataclass
class SoundCandidate:
    """
    A sound that has passed filtering and is a candidate for selection.
    
    Attributes:
        sound_id: The sound definition ID
        layer: Which layer this sound belongs to
        base_probability: Original probability from config
        adjusted_probability: Probability after SDI adjustments
        priority: Selection priority (higher = more likely when needed)
        tags: Sound tags
        duration_range: (min, max) duration
        intensity_range: (min, max) intensity
        is_continuous: Whether this is a looping sound
    """
    sound_id: str
    layer: str
    base_probability: float
    adjusted_probability: float
    priority: float = 1.0
    tags: List[str] = field(default_factory=list)
    duration_range: Tuple[float, float] = (1.0, 5.0)
    intensity_range: Tuple[float, float] = (0.3, 0.7)
    is_continuous: bool = False
    frequency_band: str = "mid"
    harmony_bonus: float = 0.0  # Bonus for harmonizing with active sounds
    conflict_penalty: float = 0.0  # Penalty for conflicting with active sounds


@dataclass
class SelectionResult:
    """
    Result of a sound selection attempt.
    
    Attributes:
        selected: Whether a sound was selected
        sound_id: The selected sound ID (if any)
        instance_id: Unique instance ID for this play
        layer: The layer of the selected sound
        duration: Calculated duration
        intensity: Calculated intensity
        reason: Why this sound was selected (or why none was)
    """
    selected: bool = False
    sound_id: Optional[str] = None
    instance_id: Optional[str] = None
    layer: Optional[str] = None
    duration: float = 0.0
    intensity: float = 0.5
    reason: str = ""
    candidates_considered: int = 0
    probability_roll: float = 0.0


class FilterReason(Enum):
    """Reasons a sound might be filtered out."""
    PASSED = "passed"
    WRONG_BIOME = "wrong_biome"
    WRONG_TIME = "wrong_time"
    WRONG_WEATHER = "wrong_weather"
    ON_COOLDOWN = "on_cooldown"
    LAYER_FULL = "layer_full"
    MISSING_FEATURE = "missing_feature"
    ALREADY_PLAYING = "already_playing"


class SoundSelector:
    """
    Selects sounds based on context, probability, and SDI adjustments.
    
    The selector:
    1. Filters sounds by current context (biome, time, weather)
    2. Checks cooldowns and layer capacity
    3. Applies SDI-based probability adjustments
    4. Applies harmony bonuses and conflict penalties
    5. Selects sounds via weighted random choice
    
    Example:
        >>> selector = SoundSelector(config, rng)
        >>> result = selector.select(
        ...     layer="periodic",
        ...     environment=env,
        ...     sound_memory=memory,
        ...     current_time=100.0,
        ...     sdi_delta=0.15
        ... )
        >>> if result.selected:
        ...     print(f"Play {result.sound_id} for {result.duration}s")
    """
    
    # SDI adjustment multipliers
    # When SDI needs to increase (delta > 0), reduce pleasant sound probability
    # When SDI needs to decrease (delta < 0), increase pleasant sound probability
    SDI_ADJUSTMENT_STRENGTH = 0.5  # How much SDI delta affects probability
    
    # Layer priorities (higher = more important to maintain)
    LAYER_PRIORITIES = {
        'background': 3,
        'periodic': 2,
        'reactive': 1,
        'anomalous': 0,
    }
    
    def __init__(self, config: Optional[Any] = None, rng: Optional[Any] = None):
        """
        Initialize the sound selector.
        
        Args:
            config: LSEConfig object
            rng: SeededRNG instance for reproducible selection
        """
        self.config = config
        self.rng = rng
        
        # Sound definitions
        self.sounds: Dict[str, Any] = {}
        
        # Biome sound pools
        self.biome_pools: Dict[str, Set[str]] = {}
        
        # Harmony/conflict definitions
        self.harmony_pairs: Dict[Tuple[str, str], float] = {}
        self.conflict_pairs: Dict[Tuple[str, str], float] = {}
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration data."""
        if self.config is None:
            return
        
        # Load sounds
        if hasattr(self.config, 'sounds'):
            self.sounds = self.config.sounds
        
        # Load biome pools
        if hasattr(self.config, 'biomes'):
            for biome_id, biome in self.config.biomes.items():
                self.biome_pools[biome_id] = set(biome.sound_pool)
        
        # Load harmony pairs
        if hasattr(self.config, 'conflicts'):
            for pair in self.config.conflicts.harmony_pairs:
                key = tuple(sorted([pair.sound_a, pair.sound_b]))
                strength = {'weak': 0.1, 'medium': 0.2, 'strong': 0.3}.get(pair.strength, 0.2)
                self.harmony_pairs[key] = strength
            
            for conflict in self.config.conflicts.sound_conflicts:
                key = tuple(sorted([conflict.sound_a, conflict.sound_b]))
                severity = {'low': 0.1, 'medium': 0.2, 'high': 0.3}.get(conflict.severity, 0.2)
                self.conflict_pairs[key] = severity
    
    def get_candidates(self,
                       layer: str,
                       environment: Any,
                       sound_memory: Any,
                       current_time: float) -> List[SoundCandidate]:
        """
        Get all valid sound candidates for a layer.
        
        Args:
            layer: The layer to select for
            environment: Current environment state
            sound_memory: Sound memory for cooldown checking
            current_time: Current simulation time
            
        Returns:
            List of valid SoundCandidate objects
        """
        candidates = []
        biome_id = getattr(environment, 'biome_id', 'forest')
        time_of_day = getattr(environment, 'time_of_day', 'day')
        weather = getattr(environment, 'weather', 'clear')
        features = getattr(environment, 'features', {})
        
        # Get biome sound pool
        pool = self.biome_pools.get(biome_id, set())
        
        # Get active sounds for harmony/conflict checking
        active_ids = set()
        if sound_memory:
            active_ids = sound_memory.get_active_ids()
        
        for sound_id, sound_config in self.sounds.items():
            # Check if in biome pool
            if pool and sound_id not in pool:
                continue
            
            # Check layer
            if sound_config.layer != layer:
                continue
            
            # Check time constraints
            time_constraints = sound_config.time_constraints
            if 'all' not in time_constraints and time_of_day not in time_constraints:
                continue
            
            # Check weather constraints
            weather_constraints = sound_config.weather_constraints
            if weather_constraints:
                excluded = getattr(weather_constraints, 'excluded', [])
                required = getattr(weather_constraints, 'required', [])
                
                if weather in excluded:
                    continue
                if required and weather not in required:
                    continue
            
            # Check feature requirements
            required_feature = sound_config.requires_feature
            if required_feature and not features.get(required_feature, False):
                continue
            
            # Check cooldown
            if sound_memory and sound_memory.is_on_cooldown(sound_id, current_time):
                continue
            
            # Check if already playing (for non-overlapping sounds)
            if sound_id in active_ids and not sound_config.is_rhythmic:
                continue
            
            # Calculate harmony bonus and conflict penalty
            harmony_bonus = 0.0
            conflict_penalty = 0.0
            
            for active_id in active_ids:
                pair_key = tuple(sorted([sound_id, active_id]))
                if pair_key in self.harmony_pairs:
                    harmony_bonus += self.harmony_pairs[pair_key]
                if pair_key in self.conflict_pairs:
                    conflict_penalty += self.conflict_pairs[pair_key]
            
            # Create candidate
            duration = sound_config.duration
            intensity = sound_config.intensity
            
            candidate = SoundCandidate(
                sound_id=sound_id,
                layer=layer,
                base_probability=sound_config.base_probability,
                adjusted_probability=sound_config.base_probability,
                priority=self.LAYER_PRIORITIES.get(layer, 1),
                tags=list(sound_config.tags),
                duration_range=(duration.min, duration.max),
                intensity_range=(intensity.min, intensity.max),
                is_continuous=(duration.type == "continuous"),
                frequency_band=sound_config.frequency_band,
                harmony_bonus=harmony_bonus,
                conflict_penalty=conflict_penalty,
            )
            
            candidates.append(candidate)
        
        return candidates
    
    def adjust_probabilities(self,
                             candidates: List[SoundCandidate],
                             sdi_delta: float,
                             delta_category: str) -> List[SoundCandidate]:
        """
        Adjust candidate probabilities based on SDI delta.
        
        When delta > 0 (need more discomfort):
        - Reduce probability of harmonious sounds
        - Increase probability of tension-building sounds
        
        When delta < 0 (need more comfort):
        - Increase probability of harmonious sounds
        - Reduce probability of tension sounds
        
        Args:
            candidates: List of sound candidates
            sdi_delta: Current SDI delta (target - current)
            delta_category: Delta category (none/small/medium/large/critical)
            
        Returns:
            Candidates with adjusted probabilities
        """
        if delta_category == 'none':
            # No adjustment needed, just apply harmony/conflict
            for c in candidates:
                c.adjusted_probability = c.base_probability + c.harmony_bonus - c.conflict_penalty
                c.adjusted_probability = max(0.0, min(1.0, c.adjusted_probability))
            return candidates
        
        # Adjustment strength based on category
        strength_mult = {
            'small': 0.5,
            'medium': 1.0,
            'large': 1.5,
            'critical': 2.0,
        }.get(delta_category, 1.0)
        
        adjustment = sdi_delta * self.SDI_ADJUSTMENT_STRENGTH * strength_mult
        
        for candidate in candidates:
            # Start with base probability
            prob = candidate.base_probability
            
            # Apply harmony/conflict bonuses
            prob += candidate.harmony_bonus - candidate.conflict_penalty
            
            # SDI adjustment
            # If delta > 0 (need more SDI), sounds with high harmony get reduced
            # If delta < 0 (need less SDI), sounds with high harmony get boosted
            if candidate.harmony_bonus > 0:
                prob -= adjustment * candidate.harmony_bonus * 2
            
            # Anomalous sounds get boosted when we need more SDI
            if candidate.layer == 'anomalous' and sdi_delta > 0:
                prob += abs(adjustment)
            
            # Clamp to valid range
            candidate.adjusted_probability = max(0.01, min(0.99, prob))
        
        return candidates
    
    def select(self,
               layer: str,
               environment: Any,
               sound_memory: Any,
               current_time: float,
               sdi_delta: float = 0.0,
               delta_category: str = "none",
               force_selection: bool = False) -> SelectionResult:
        """
        Attempt to select a sound for the given layer.
        
        Args:
            layer: The layer to select for
            environment: Current environment state
            sound_memory: Sound memory state
            current_time: Current simulation time
            sdi_delta: Current SDI delta
            delta_category: Delta category
            force_selection: If True, always select if candidates available
            
        Returns:
            SelectionResult with selected sound or reason for no selection
        """
        result = SelectionResult()
        
        # Get candidates
        candidates = self.get_candidates(layer, environment, sound_memory, current_time)
        result.candidates_considered = len(candidates)
        
        if not candidates:
            result.reason = f"No valid candidates for {layer} layer"
            return result
        
        # Adjust probabilities
        candidates = self.adjust_probabilities(candidates, sdi_delta, delta_category)
        
        # Calculate selection probability (should we play anything?)
        # Higher with more candidates, adjusted by SDI needs
        base_selection_chance = min(0.3 + len(candidates) * 0.05, 0.8)
        
        if sdi_delta > 0:  # Need more SDI, play more sounds
            base_selection_chance += abs(sdi_delta) * 0.3
        elif sdi_delta < 0:  # Need less SDI, play fewer sounds
            base_selection_chance -= abs(sdi_delta) * 0.2
        
        base_selection_chance = max(0.1, min(0.9, base_selection_chance))
        
        # Roll for selection
        if self.rng:
            result.probability_roll = self.rng.random()
        else:
            import random
            result.probability_roll = random.random()
        
        if not force_selection and result.probability_roll > base_selection_chance:
            result.reason = f"Selection roll failed ({result.probability_roll:.2f} > {base_selection_chance:.2f})"
            return result
        
        # Select from candidates using weighted choice
        selected = self._weighted_select(candidates)
        
        if selected is None:
            result.reason = "Weighted selection returned no result"
            return result
        
        # Calculate duration and intensity
        if self.rng:
            duration = self.rng.uniform(selected.duration_range[0], selected.duration_range[1])
            intensity = self.rng.uniform(selected.intensity_range[0], selected.intensity_range[1])
        else:
            import random
            duration = random.uniform(selected.duration_range[0], selected.duration_range[1])
            intensity = random.uniform(selected.intensity_range[0], selected.intensity_range[1])
        
        # Build result
        result.selected = True
        result.sound_id = selected.sound_id
        result.instance_id = str(uuid.uuid4())
        result.layer = selected.layer
        result.duration = duration
        result.intensity = intensity
        result.reason = f"Selected with probability {selected.adjusted_probability:.2f}"
        
        return result
    
    def _weighted_select(self, candidates: List[SoundCandidate]) -> Optional[SoundCandidate]:
        """Select a candidate using weighted random choice."""
        if not candidates:
            return None
        
        weights = [c.adjusted_probability for c in candidates]
        total = sum(weights)
        
        if total == 0:
            return candidates[0] if candidates else None
        
        if self.rng:
            r = self.rng.random() * total
        else:
            import random
            r = random.random() * total
        
        cumulative = 0.0
        for candidate, weight in zip(candidates, weights):
            cumulative += weight
            if r < cumulative:
                return candidate
        
        return candidates[-1]
    
    def select_multiple(self,
                        layers: List[str],
                        environment: Any,
                        sound_memory: Any,
                        current_time: float,
                        sdi_delta: float = 0.0,
                        delta_category: str = "none",
                        max_per_layer: Dict[str, int] = None) -> List[SelectionResult]:
        """
        Attempt to select sounds for multiple layers.
        
        Args:
            layers: List of layers to select for
            environment: Current environment state
            sound_memory: Sound memory state
            current_time: Current simulation time
            sdi_delta: Current SDI delta
            delta_category: Delta category
            max_per_layer: Maximum selections per layer
            
        Returns:
            List of SelectionResults
        """
        if max_per_layer is None:
            max_per_layer = {'background': 1, 'periodic': 2, 'reactive': 1, 'anomalous': 1}
        
        results = []
        
        for layer in layers:
            max_count = max_per_layer.get(layer, 1)
            
            for _ in range(max_count):
                result = self.select(
                    layer=layer,
                    environment=environment,
                    sound_memory=sound_memory,
                    current_time=current_time,
                    sdi_delta=sdi_delta,
                    delta_category=delta_category,
                )
                results.append(result)
                
                if not result.selected:
                    break
        
        return results
    
    def get_sound_config(self, sound_id: str) -> Optional[Any]:
        """Get the configuration for a sound."""
        return self.sounds.get(sound_id)
