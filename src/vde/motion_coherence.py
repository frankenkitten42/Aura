"""
VDE Phase 6: Motion Coherence System

The most powerful and least obvious lever.

Motion coherence creates comfort through synchronized, predictable movement.
Motion incoherence creates subtle unease through desynchronized, unpredictable motion.

This module handles:
- Wind direction and variance control
- Foliage animation synchronization
- Cloth/banner behavior
- Prop micro-movement
- Phase relationship management
- UE5-ready motion parameters

Key insight: Humans are extremely sensitive to motion patterns. Synchronized
motion feels natural and calming. Desynchronized motion triggers low-level
anxiety without conscious awareness.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import math
import random


# =============================================================================
# Enums and Constants
# =============================================================================

class MotionCategory(Enum):
    """Categories of motion-affected elements."""
    FOLIAGE = "foliage"         # Trees, bushes, grass
    CLOTH = "cloth"             # Banners, flags, awnings
    PROPS = "props"             # Small objects, hanging items
    WATER = "water"             # Water surfaces, ripples
    PARTICLES = "particles"     # Dust, leaves, debris
    NPCS = "npcs"               # NPC idle animations


class CoherenceLevel(Enum):
    """Motion coherence levels."""
    UNIFIED = "unified"         # Perfect synchronization
    NATURAL = "natural"         # Natural variation (comfortable)
    VARIED = "varied"           # Noticeable variation
    CHAOTIC = "chaotic"         # Desynchronized (uncomfortable)


class WindPattern(Enum):
    """Wind behavior patterns."""
    STEADY = "steady"           # Consistent direction and strength
    GUSTING = "gusting"         # Periodic gusts
    SWIRLING = "swirling"       # Chaotic direction changes
    CALM = "calm"               # Minimal wind


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class MotionConfig:
    """Configuration for motion coherence system."""
    
    # Population thresholds for coherence levels
    unified_max_pop: float = 0.15       # Below this = UNIFIED
    natural_max_pop: float = 0.35       # Below this = NATURAL
    varied_max_pop: float = 0.60        # Below this = VARIED
    # Above varied_max_pop = CHAOTIC
    
    # Wind parameters
    base_wind_direction: float = 0.0    # Degrees (0 = North)
    base_wind_strength: float = 0.5     # 0-1
    
    # Phase offset ranges per coherence level (radians)
    phase_variance: Dict[CoherenceLevel, float] = field(default_factory=lambda: {
        CoherenceLevel.UNIFIED: 0.1,     # Nearly synchronized
        CoherenceLevel.NATURAL: 0.3,     # Natural variation
        CoherenceLevel.VARIED: 0.8,      # Noticeable desync
        CoherenceLevel.CHAOTIC: math.pi, # Full desync
    })
    
    # Wind direction variance per coherence level (degrees)
    direction_variance: Dict[CoherenceLevel, float] = field(default_factory=lambda: {
        CoherenceLevel.UNIFIED: 5.0,
        CoherenceLevel.NATURAL: 15.0,
        CoherenceLevel.VARIED: 45.0,
        CoherenceLevel.CHAOTIC: 180.0,
    })
    
    # Animation speed variance per coherence level
    speed_variance: Dict[CoherenceLevel, float] = field(default_factory=lambda: {
        CoherenceLevel.UNIFIED: 0.05,
        CoherenceLevel.NATURAL: 0.10,
        CoherenceLevel.VARIED: 0.25,
        CoherenceLevel.CHAOTIC: 0.50,
    })
    
    # Settling behavior (how well things come to rest)
    settling_rate: Dict[CoherenceLevel, float] = field(default_factory=lambda: {
        CoherenceLevel.UNIFIED: 1.0,     # Perfect settling
        CoherenceLevel.NATURAL: 0.9,
        CoherenceLevel.VARIED: 0.6,
        CoherenceLevel.CHAOTIC: 0.2,     # Never fully settles
    })
    
    # Smoothing rate for transitions
    coherence_smoothing: float = 0.05


# =============================================================================
# Motion Element State
# =============================================================================

@dataclass
class ElementMotionState:
    """Motion state for a single animated element."""
    element_id: str
    category: MotionCategory
    
    # Phase
    base_phase: float = 0.0         # Base animation phase (radians)
    phase_offset: float = 0.0       # Coherence-based offset
    current_phase: float = 0.0      # Actual current phase
    
    # Speed
    base_speed: float = 1.0         # Base animation speed
    speed_multiplier: float = 1.0   # Coherence-based multiplier
    current_speed: float = 1.0      # Actual speed
    
    # Direction (for wind-affected elements)
    local_wind_direction: float = 0.0   # Degrees
    local_wind_strength: float = 0.5
    
    # Settling
    is_settled: bool = False
    settling_progress: float = 0.0   # 0 = active, 1 = settled
    residual_motion: float = 0.0     # Persistent micro-motion
    
    # Jitter (for props)
    jitter_amount: float = 0.0
    jitter_frequency: float = 0.0


@dataclass
class CategoryState:
    """Aggregate state for a motion category."""
    category: MotionCategory
    
    # Global parameters for this category
    phase_coherence: float = 1.0     # 0 = chaotic, 1 = unified
    speed_coherence: float = 1.0
    direction_coherence: float = 1.0
    
    # Wind
    wind_direction: float = 0.0
    wind_strength: float = 0.5
    wind_variance: float = 0.0
    
    # Animation
    base_animation_speed: float = 1.0
    animation_speed_variance: float = 0.0
    
    # Settling
    can_settle: bool = True
    settling_threshold: float = 0.3   # Wind strength below which settling occurs
    
    # Elements in this category
    elements: Dict[str, ElementMotionState] = field(default_factory=dict)


# =============================================================================
# Motion Snapshot
# =============================================================================

@dataclass
class MotionSnapshot:
    """Snapshot of motion coherence state."""
    population: float = 0.0
    coherence_level: CoherenceLevel = CoherenceLevel.NATURAL
    coherence_value: float = 1.0  # 0-1, smoothed
    
    # Global wind
    global_wind_direction: float = 0.0
    global_wind_strength: float = 0.5
    
    # Per-category states
    category_states: Dict[MotionCategory, CategoryState] = field(default_factory=dict)
    
    # Aggregate metrics
    average_phase_coherence: float = 1.0
    average_speed_coherence: float = 1.0
    settling_elements_ratio: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'population': self.population,
            'coherence_level': self.coherence_level.value,
            'coherence_value': self.coherence_value,
            'global_wind_direction': self.global_wind_direction,
            'global_wind_strength': self.global_wind_strength,
            'average_phase_coherence': self.average_phase_coherence,
            'average_speed_coherence': self.average_speed_coherence,
            'settling_elements_ratio': self.settling_elements_ratio,
            'categories': {
                cat.value: {
                    'phase_coherence': state.phase_coherence,
                    'speed_coherence': state.speed_coherence,
                    'wind_direction': state.wind_direction,
                    'wind_variance': state.wind_variance,
                } for cat, state in self.category_states.items()
            },
        }


# =============================================================================
# Motion Manager
# =============================================================================

class MotionManager:
    """
    Manages motion coherence for a region.
    
    Controls synchronization of environmental animations based on
    population pressure.
    
    Example:
        >>> manager = MotionManager()
        >>> manager.register_element("tree_01", MotionCategory.FOLIAGE)
        >>> manager.register_element("banner_01", MotionCategory.CLOTH)
        >>> manager.set_population(0.65)
        >>> 
        >>> snapshot = manager.update(delta_time=0.5)
        >>> params = manager.get_ue5_parameters()
    """
    
    COHERENCE_ORDER = [
        CoherenceLevel.UNIFIED,
        CoherenceLevel.NATURAL,
        CoherenceLevel.VARIED,
        CoherenceLevel.CHAOTIC,
    ]
    
    def __init__(self, config: Optional[MotionConfig] = None):
        """
        Initialize motion manager.
        
        Args:
            config: Motion configuration
        """
        self.config = config or MotionConfig()
        
        # Initialize category states
        self.categories: Dict[MotionCategory, CategoryState] = {}
        for category in MotionCategory:
            self.categories[category] = CategoryState(category=category)
        
        # Configure category-specific defaults
        self._configure_categories()
        
        # Global state
        self._population = 0.0
        self._coherence_level = CoherenceLevel.NATURAL
        self._coherence_value = 1.0  # Smoothed 0-1 value
        self._target_coherence = 1.0
        self._time = 0.0
        
        # Wind state
        self._wind_direction = self.config.base_wind_direction
        self._wind_strength = self.config.base_wind_strength
        self._wind_time = 0.0
        
        # RNG for variation
        self._rng = random.Random(42)
    
    def _configure_categories(self) -> None:
        """Configure category-specific defaults."""
        # Foliage - most affected by wind
        self.categories[MotionCategory.FOLIAGE].base_animation_speed = 1.0
        self.categories[MotionCategory.FOLIAGE].settling_threshold = 0.2
        
        # Cloth - very responsive to wind
        self.categories[MotionCategory.CLOTH].base_animation_speed = 1.2
        self.categories[MotionCategory.CLOTH].settling_threshold = 0.15
        
        # Props - subtle movement
        self.categories[MotionCategory.PROPS].base_animation_speed = 0.5
        self.categories[MotionCategory.PROPS].settling_threshold = 0.1
        
        # Water - persistent motion
        self.categories[MotionCategory.WATER].base_animation_speed = 0.8
        self.categories[MotionCategory.WATER].can_settle = False
        
        # Particles - very responsive
        self.categories[MotionCategory.PARTICLES].base_animation_speed = 1.5
        self.categories[MotionCategory.PARTICLES].can_settle = False
        
        # NPCs - subtle idle variation
        self.categories[MotionCategory.NPCS].base_animation_speed = 1.0
        self.categories[MotionCategory.NPCS].settling_threshold = 0.0
    
    def register_element(self, element_id: str, category: MotionCategory,
                         base_phase: Optional[float] = None,
                         base_speed: Optional[float] = None) -> None:
        """Register an animated element."""
        if base_phase is None:
            base_phase = self._rng.random() * 2 * math.pi
        
        if base_speed is None:
            base_speed = self.categories[category].base_animation_speed
        
        element = ElementMotionState(
            element_id=element_id,
            category=category,
            base_phase=base_phase,
            base_speed=base_speed,
            current_phase=base_phase,
            current_speed=base_speed,
        )
        
        self.categories[category].elements[element_id] = element
    
    def unregister_element(self, element_id: str, category: MotionCategory) -> None:
        """Remove an element from tracking."""
        if element_id in self.categories[category].elements:
            del self.categories[category].elements[element_id]
    
    def set_population(self, population: float) -> None:
        """Set current population ratio (0.0 to 1.0)."""
        self._population = max(0.0, min(1.0, population))
    
    def update(self, delta_time: float) -> MotionSnapshot:
        """
        Update motion coherence for one tick.
        
        Args:
            delta_time: Time since last update in seconds
            
        Returns:
            Current motion snapshot
        """
        self._time += delta_time
        self._wind_time += delta_time
        cfg = self.config
        
        # Determine coherence level from population
        self._coherence_level = self._get_coherence_level(self._population)
        
        # Calculate target coherence value (0 = chaotic, 1 = unified)
        coherence_idx = self.COHERENCE_ORDER.index(self._coherence_level)
        self._target_coherence = 1.0 - (coherence_idx / (len(self.COHERENCE_ORDER) - 1))
        
        # Smooth coherence transition
        diff = self._target_coherence - self._coherence_value
        self._coherence_value += diff * min(1.0, delta_time * cfg.coherence_smoothing * 10)
        
        # Update wind
        self._update_wind(delta_time)
        
        # Update each category
        for category, state in self.categories.items():
            self._update_category(state, delta_time)
        
        return self._create_snapshot()
    
    def _get_coherence_level(self, population: float) -> CoherenceLevel:
        """Determine coherence level from population."""
        cfg = self.config
        
        if population < cfg.unified_max_pop:
            return CoherenceLevel.UNIFIED
        elif population < cfg.natural_max_pop:
            return CoherenceLevel.NATURAL
        elif population < cfg.varied_max_pop:
            return CoherenceLevel.VARIED
        else:
            return CoherenceLevel.CHAOTIC
    
    def _update_wind(self, delta_time: float) -> None:
        """Update wind state."""
        cfg = self.config
        
        # Base wind with time-based variation
        base_dir = cfg.base_wind_direction
        
        # Add variance based on coherence
        dir_variance = cfg.direction_variance.get(self._coherence_level, 15.0)
        
        # Perlin-like smooth variation
        time_factor = math.sin(self._wind_time * 0.1) * 0.5 + 0.5
        dir_offset = (time_factor - 0.5) * dir_variance * 2
        
        self._wind_direction = (base_dir + dir_offset) % 360
        
        # Wind strength varies with coherence
        if self._coherence_level == CoherenceLevel.CHAOTIC:
            # Gusty, unpredictable
            gust = math.sin(self._wind_time * 2.0) * 0.3
            self._wind_strength = cfg.base_wind_strength + gust
        else:
            self._wind_strength = cfg.base_wind_strength
        
        self._wind_strength = max(0.0, min(1.0, self._wind_strength))
    
    def _update_category(self, state: CategoryState, delta_time: float) -> None:
        """Update a motion category."""
        cfg = self.config
        
        # Get coherence parameters
        phase_var = cfg.phase_variance.get(self._coherence_level, 0.3)
        speed_var = cfg.speed_variance.get(self._coherence_level, 0.1)
        dir_var = cfg.direction_variance.get(self._coherence_level, 15.0)
        settling = cfg.settling_rate.get(self._coherence_level, 0.9)
        
        # Update category-level parameters
        state.phase_coherence = self._coherence_value
        state.speed_coherence = self._coherence_value
        state.direction_coherence = self._coherence_value
        
        state.wind_direction = self._wind_direction
        state.wind_strength = self._wind_strength
        state.wind_variance = dir_var
        
        state.animation_speed_variance = speed_var
        
        # Update each element
        for element in state.elements.values():
            self._update_element(element, state, phase_var, speed_var, 
                                dir_var, settling, delta_time)
    
    def _update_element(self, element: ElementMotionState, state: CategoryState,
                        phase_var: float, speed_var: float, dir_var: float,
                        settling: float, delta_time: float) -> None:
        """Update a single element's motion state."""
        # Phase offset varies with coherence
        target_offset = (self._rng.random() - 0.5) * phase_var * 2
        element.phase_offset += (target_offset - element.phase_offset) * delta_time * 0.5
        element.current_phase = element.base_phase + element.phase_offset
        
        # Speed varies with coherence
        target_speed_mult = 1.0 + (self._rng.random() - 0.5) * speed_var * 2
        element.speed_multiplier += (target_speed_mult - element.speed_multiplier) * delta_time * 0.5
        element.current_speed = element.base_speed * element.speed_multiplier
        
        # Local wind direction
        dir_offset = (self._rng.random() - 0.5) * dir_var * 2
        element.local_wind_direction = (state.wind_direction + dir_offset) % 360
        element.local_wind_strength = state.wind_strength * (0.8 + self._rng.random() * 0.4)
        
        # Settling behavior
        if state.can_settle and state.wind_strength < state.settling_threshold:
            element.settling_progress += settling * delta_time
            element.settling_progress = min(1.0, element.settling_progress)
            element.is_settled = element.settling_progress > 0.9
            
            # Residual motion based on coherence (chaotic = never still)
            element.residual_motion = (1.0 - settling) * 0.1
        else:
            element.settling_progress = 0.0
            element.is_settled = False
            element.residual_motion = 0.0
        
        # Jitter for props
        if element.category == MotionCategory.PROPS:
            element.jitter_amount = (1.0 - self._coherence_value) * 0.02
            element.jitter_frequency = 5.0 + (1.0 - self._coherence_value) * 10.0
    
    def _create_snapshot(self) -> MotionSnapshot:
        """Create a snapshot of current motion state."""
        snapshot = MotionSnapshot()
        snapshot.population = self._population
        snapshot.coherence_level = self._coherence_level
        snapshot.coherence_value = self._coherence_value
        snapshot.global_wind_direction = self._wind_direction
        snapshot.global_wind_strength = self._wind_strength
        snapshot.category_states = dict(self.categories)
        
        # Calculate aggregates
        total_phase_coherence = 0.0
        total_speed_coherence = 0.0
        total_elements = 0
        settled_elements = 0
        
        for state in self.categories.values():
            total_phase_coherence += state.phase_coherence
            total_speed_coherence += state.speed_coherence
            
            for element in state.elements.values():
                total_elements += 1
                if element.is_settled:
                    settled_elements += 1
        
        if len(self.categories) > 0:
            snapshot.average_phase_coherence = total_phase_coherence / len(self.categories)
            snapshot.average_speed_coherence = total_speed_coherence / len(self.categories)
        
        if total_elements > 0:
            snapshot.settling_elements_ratio = settled_elements / total_elements
        
        return snapshot
    
    def get_ue5_parameters(self) -> 'FMotionParameters':
        """Generate UE5-ready motion parameters."""
        return FMotionParameters.from_manager(self)
    
    def reset(self) -> None:
        """Reset motion state."""
        self._population = 0.0
        self._coherence_level = CoherenceLevel.NATURAL
        self._coherence_value = 1.0
        self._target_coherence = 1.0
        self._time = 0.0
        self._wind_time = 0.0
        self._wind_direction = self.config.base_wind_direction
        self._wind_strength = self.config.base_wind_strength
        
        for state in self.categories.values():
            state.phase_coherence = 1.0
            state.speed_coherence = 1.0
            state.direction_coherence = 1.0
            
            for element in state.elements.values():
                element.phase_offset = 0.0
                element.current_phase = element.base_phase
                element.speed_multiplier = 1.0
                element.current_speed = element.base_speed
                element.is_settled = False
                element.settling_progress = 0.0
                element.residual_motion = 0.0
                element.jitter_amount = 0.0
    
    @property
    def coherence_level(self) -> CoherenceLevel:
        """Current coherence level."""
        return self._coherence_level
    
    @property
    def coherence_value(self) -> float:
        """Current coherence value (0-1)."""
        return self._coherence_value
    
    @property
    def population(self) -> float:
        """Current population."""
        return self._population


# =============================================================================
# UE5 Parameters
# =============================================================================

@dataclass
class FMotionParameters:
    """UE5-ready motion coherence parameters."""
    
    # Global coherence
    coherence_level: str = "natural"
    coherence_value: float = 1.0
    
    # Wind
    wind_direction: float = 0.0          # Degrees
    wind_strength: float = 0.5           # 0-1
    wind_direction_variance: float = 15.0  # Degrees
    wind_gusting: float = 0.0            # 0-1
    
    # Foliage parameters
    foliage_phase_offset_max: float = 0.3    # Radians
    foliage_speed_variance: float = 0.1      # Multiplier range
    foliage_wave_coherence: float = 1.0      # 0 = chaotic, 1 = unified
    foliage_turbulence: float = 0.0          # 0-1
    
    # Cloth parameters
    cloth_phase_offset_max: float = 0.3
    cloth_speed_variance: float = 0.1
    cloth_settling_rate: float = 0.9         # How fast it settles
    cloth_residual_motion: float = 0.0       # Micro-movement when "still"
    cloth_damping: float = 0.9               # Higher = more stable
    
    # Prop parameters
    prop_jitter_amount: float = 0.0          # World units
    prop_jitter_frequency: float = 5.0       # Hz
    prop_sway_coherence: float = 1.0         # Hanging objects
    prop_micro_movement: float = 0.0         # Subtle motion
    
    # Water parameters
    water_wave_coherence: float = 1.0
    water_ripple_variance: float = 0.0
    water_turbulence: float = 0.0
    
    # Particle parameters
    particle_direction_variance: float = 15.0
    particle_speed_variance: float = 0.1
    particle_coherence: float = 1.0
    
    # NPC idle parameters
    npc_idle_phase_variance: float = 0.1
    npc_idle_speed_variance: float = 0.05
    npc_breathing_sync: float = 1.0          # 1 = all in sync (eerie)
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export as JSON for UE5."""
        return {
            'Motion_CoherenceLevel': self.coherence_level,
            'Motion_CoherenceValue': self.coherence_value,
            'Wind_Direction': self.wind_direction,
            'Wind_Strength': self.wind_strength,
            'Wind_DirectionVariance': self.wind_direction_variance,
            'Wind_Gusting': self.wind_gusting,
            'Foliage_PhaseOffsetMax': self.foliage_phase_offset_max,
            'Foliage_SpeedVariance': self.foliage_speed_variance,
            'Foliage_WaveCoherence': self.foliage_wave_coherence,
            'Foliage_Turbulence': self.foliage_turbulence,
            'Cloth_PhaseOffsetMax': self.cloth_phase_offset_max,
            'Cloth_SpeedVariance': self.cloth_speed_variance,
            'Cloth_SettlingRate': self.cloth_settling_rate,
            'Cloth_ResidualMotion': self.cloth_residual_motion,
            'Cloth_Damping': self.cloth_damping,
            'Prop_JitterAmount': self.prop_jitter_amount,
            'Prop_JitterFrequency': self.prop_jitter_frequency,
            'Prop_SwayCoherence': self.prop_sway_coherence,
            'Prop_MicroMovement': self.prop_micro_movement,
            'Water_WaveCoherence': self.water_wave_coherence,
            'Water_RippleVariance': self.water_ripple_variance,
            'Water_Turbulence': self.water_turbulence,
            'Particle_DirectionVariance': self.particle_direction_variance,
            'Particle_SpeedVariance': self.particle_speed_variance,
            'Particle_Coherence': self.particle_coherence,
            'NPC_IdlePhaseVariance': self.npc_idle_phase_variance,
            'NPC_IdleSpeedVariance': self.npc_idle_speed_variance,
            'NPC_BreathingSync': self.npc_breathing_sync,
        }
    
    @classmethod
    def from_manager(cls, manager: MotionManager) -> 'FMotionParameters':
        """Create parameters from motion manager state."""
        params = cls()
        cfg = manager.config
        
        params.coherence_level = manager.coherence_level.value
        params.coherence_value = manager.coherence_value
        
        # Wind
        params.wind_direction = manager._wind_direction
        params.wind_strength = manager._wind_strength
        params.wind_direction_variance = cfg.direction_variance.get(
            manager.coherence_level, 15.0
        )
        params.wind_gusting = 0.0 if manager.coherence_level != CoherenceLevel.CHAOTIC else 0.5
        
        # Get variance values
        phase_var = cfg.phase_variance.get(manager.coherence_level, 0.3)
        speed_var = cfg.speed_variance.get(manager.coherence_level, 0.1)
        settling = cfg.settling_rate.get(manager.coherence_level, 0.9)
        
        # Foliage
        params.foliage_phase_offset_max = phase_var
        params.foliage_speed_variance = speed_var
        params.foliage_wave_coherence = manager.coherence_value
        params.foliage_turbulence = 1.0 - manager.coherence_value
        
        # Cloth
        params.cloth_phase_offset_max = phase_var
        params.cloth_speed_variance = speed_var
        params.cloth_settling_rate = settling
        params.cloth_residual_motion = (1.0 - settling) * 0.1
        params.cloth_damping = 0.5 + manager.coherence_value * 0.5
        
        # Props
        params.prop_jitter_amount = (1.0 - manager.coherence_value) * 0.02
        params.prop_jitter_frequency = 5.0 + (1.0 - manager.coherence_value) * 10.0
        params.prop_sway_coherence = manager.coherence_value
        params.prop_micro_movement = (1.0 - settling) * 0.05
        
        # Water
        params.water_wave_coherence = manager.coherence_value
        params.water_ripple_variance = (1.0 - manager.coherence_value) * 0.5
        params.water_turbulence = (1.0 - manager.coherence_value) * 0.3
        
        # Particles
        params.particle_direction_variance = cfg.direction_variance.get(
            manager.coherence_level, 15.0
        )
        params.particle_speed_variance = speed_var
        params.particle_coherence = manager.coherence_value
        
        # NPCs
        params.npc_idle_phase_variance = phase_var * 0.5
        params.npc_idle_speed_variance = speed_var * 0.5
        # Breathing sync: too perfect sync is eerie, too much variance is chaotic
        # Optimal is NATURAL level
        if manager.coherence_level == CoherenceLevel.UNIFIED:
            params.npc_breathing_sync = 0.95  # Almost too perfect
        elif manager.coherence_level == CoherenceLevel.NATURAL:
            params.npc_breathing_sync = 0.7   # Natural variation
        elif manager.coherence_level == CoherenceLevel.VARIED:
            params.npc_breathing_sync = 0.4
        else:
            params.npc_breathing_sync = 0.1   # Very desynchronized
        
        return params


# =============================================================================
# Wind Pattern Generator
# =============================================================================

class WindPatternGenerator:
    """
    Generates wind patterns for environmental motion.
    
    Provides time-varying wind direction and strength based on
    configured patterns and coherence level.
    """
    
    def __init__(self, base_direction: float = 0.0, base_strength: float = 0.5):
        """Initialize wind generator."""
        self.base_direction = base_direction
        self.base_strength = base_strength
        self._time = 0.0
        self._pattern = WindPattern.STEADY
    
    def set_pattern(self, pattern: WindPattern) -> None:
        """Set wind pattern."""
        self._pattern = pattern
    
    def update(self, delta_time: float, coherence: float) -> Tuple[float, float]:
        """
        Update and return current wind state.
        
        Returns:
            Tuple of (direction_degrees, strength_0_to_1)
        """
        self._time += delta_time
        
        if self._pattern == WindPattern.CALM:
            return self.base_direction, 0.1
        
        elif self._pattern == WindPattern.STEADY:
            # Minimal variation
            dir_var = math.sin(self._time * 0.05) * 5.0
            str_var = math.sin(self._time * 0.1) * 0.05
            return (
                (self.base_direction + dir_var) % 360,
                max(0.1, min(1.0, self.base_strength + str_var))
            )
        
        elif self._pattern == WindPattern.GUSTING:
            # Periodic strong gusts
            gust_cycle = math.sin(self._time * 0.3)
            gust = max(0, gust_cycle) ** 2 * 0.4
            dir_var = math.sin(self._time * 0.2) * 20.0
            return (
                (self.base_direction + dir_var) % 360,
                max(0.1, min(1.0, self.base_strength + gust))
            )
        
        else:  # SWIRLING
            # Chaotic direction changes
            dir_var = math.sin(self._time * 0.5) * 60.0 + math.sin(self._time * 1.3) * 30.0
            str_var = math.sin(self._time * 0.7) * 0.2
            return (
                (self.base_direction + dir_var) % 360,
                max(0.1, min(1.0, self.base_strength + str_var))
            )
    
    def get_pattern_for_coherence(self, coherence_level: CoherenceLevel) -> WindPattern:
        """Get appropriate wind pattern for coherence level."""
        if coherence_level == CoherenceLevel.UNIFIED:
            return WindPattern.CALM
        elif coherence_level == CoherenceLevel.NATURAL:
            return WindPattern.STEADY
        elif coherence_level == CoherenceLevel.VARIED:
            return WindPattern.GUSTING
        else:
            return WindPattern.SWIRLING
