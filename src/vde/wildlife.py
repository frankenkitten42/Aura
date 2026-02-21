"""
VDE Phase 3: Wildlife System

Comprehensive wildlife behavior system with:
- Multi-tier creature sensitivity
- State machine with asymmetric transitions
- Per-creature spawn rate modulation
- Behavior modifications per state
- Recovery timing with "memory" effect
- UE5-ready spawn commands

Wildlife is the strongest visual signal - absence speaks louder than presence.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
import math


# =============================================================================
# Enums and Constants
# =============================================================================

class WildlifeState(Enum):
    """Wildlife behavior states."""
    THRIVING = "thriving"       # Full activity, birds land, insects hover
    WARY = "wary"               # Reduced landing, quicker flight
    RETREATING = "retreating"   # Animals at edges only, no landing
    ABSENT = "absent"           # No wildlife spawns


class CreatureTier(Enum):
    """Creature sensitivity tiers."""
    TIER_1 = 1  # Most sensitive: birds, deer, large fauna
    TIER_2 = 2  # Moderate: small mammals, reptiles
    TIER_3 = 3  # Least sensitive: insects, fish


class CreatureCategory(Enum):
    """Categories of wildlife."""
    # Tier 1 - Most Sensitive
    BIRDS_SMALL = "birds_small"           # Songbirds, sparrows
    BIRDS_LARGE = "birds_large"           # Crows, ravens, hawks
    DEER = "deer"                         # Deer, elk
    LARGE_FAUNA = "large_fauna"           # Bears, wolves (rare)
    
    # Tier 2 - Moderate
    SMALL_MAMMALS = "small_mammals"       # Rabbits, squirrels
    REPTILES = "reptiles"                 # Lizards, snakes
    AMPHIBIANS = "amphibians"             # Frogs, salamanders
    
    # Tier 3 - Least Sensitive
    INSECTS_FLYING = "insects_flying"     # Butterflies, dragonflies
    INSECTS_GROUND = "insects_ground"     # Beetles, ants
    FISH = "fish"                         # Fish in water
    AMBIENT_SOUNDS = "ambient_sounds"     # Creature sounds (not visual)


# Tier mapping
CREATURE_TIERS: Dict[CreatureCategory, CreatureTier] = {
    # Tier 1
    CreatureCategory.BIRDS_SMALL: CreatureTier.TIER_1,
    CreatureCategory.BIRDS_LARGE: CreatureTier.TIER_1,
    CreatureCategory.DEER: CreatureTier.TIER_1,
    CreatureCategory.LARGE_FAUNA: CreatureTier.TIER_1,
    # Tier 2
    CreatureCategory.SMALL_MAMMALS: CreatureTier.TIER_2,
    CreatureCategory.REPTILES: CreatureTier.TIER_2,
    CreatureCategory.AMPHIBIANS: CreatureTier.TIER_2,
    # Tier 3
    CreatureCategory.INSECTS_FLYING: CreatureTier.TIER_3,
    CreatureCategory.INSECTS_GROUND: CreatureTier.TIER_3,
    CreatureCategory.FISH: CreatureTier.TIER_3,
    CreatureCategory.AMBIENT_SOUNDS: CreatureTier.TIER_3,
}


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class WildlifeConfig:
    """Configuration for wildlife system."""
    
    # Population thresholds for state transitions
    thriving_max_pop: float = 0.15      # Below this = THRIVING
    wary_max_pop: float = 0.30          # Below this = WARY
    retreating_max_pop: float = 0.50    # Below this = RETREATING
    # Above retreating_max_pop = ABSENT
    
    # Tier sensitivity multipliers (how fast they react)
    tier_sensitivity: Dict[CreatureTier, float] = field(default_factory=lambda: {
        CreatureTier.TIER_1: 1.5,   # Most sensitive, react faster
        CreatureTier.TIER_2: 1.0,   # Normal
        CreatureTier.TIER_3: 0.6,   # Least sensitive, slower to react
    })
    
    # Recovery times (seconds) - wildlife returns slowly
    recovery_times: Dict[Tuple[WildlifeState, WildlifeState], float] = field(
        default_factory=lambda: {
            (WildlifeState.ABSENT, WildlifeState.RETREATING): 30.0,
            (WildlifeState.RETREATING, WildlifeState.WARY): 45.0,
            (WildlifeState.WARY, WildlifeState.THRIVING): 60.0,
        }
    )
    
    # Flee times (seconds) - wildlife leaves quickly
    flee_times: Dict[Tuple[WildlifeState, WildlifeState], float] = field(
        default_factory=lambda: {
            (WildlifeState.THRIVING, WildlifeState.WARY): 5.0,
            (WildlifeState.WARY, WildlifeState.RETREATING): 8.0,
            (WildlifeState.RETREATING, WildlifeState.ABSENT): 10.0,
        }
    )
    
    # Base spawn rates per category (spawns per minute at THRIVING)
    base_spawn_rates: Dict[CreatureCategory, float] = field(default_factory=lambda: {
        CreatureCategory.BIRDS_SMALL: 12.0,
        CreatureCategory.BIRDS_LARGE: 3.0,
        CreatureCategory.DEER: 1.0,
        CreatureCategory.LARGE_FAUNA: 0.2,
        CreatureCategory.SMALL_MAMMALS: 8.0,
        CreatureCategory.REPTILES: 4.0,
        CreatureCategory.AMPHIBIANS: 6.0,
        CreatureCategory.INSECTS_FLYING: 20.0,
        CreatureCategory.INSECTS_GROUND: 15.0,
        CreatureCategory.FISH: 10.0,
        CreatureCategory.AMBIENT_SOUNDS: 30.0,
    })
    
    # Spawn rate multipliers per state
    state_spawn_multipliers: Dict[WildlifeState, float] = field(default_factory=lambda: {
        WildlifeState.THRIVING: 1.0,
        WildlifeState.WARY: 0.5,
        WildlifeState.RETREATING: 0.15,
        WildlifeState.ABSENT: 0.0,
    })
    
    # Minimum spawn rate for Tier 3 (insects never fully disappear)
    tier3_minimum_rate: float = 0.20


# =============================================================================
# Creature State Tracking
# =============================================================================

@dataclass
class CreatureState:
    """State tracking for a single creature category."""
    category: CreatureCategory
    tier: CreatureTier
    
    # Current state
    state: WildlifeState = WildlifeState.THRIVING
    target_state: WildlifeState = WildlifeState.THRIVING
    
    # Transition progress (0.0 to 1.0)
    transition_progress: float = 0.0
    
    # Spawn rate
    current_spawn_rate: float = 0.0
    target_spawn_rate: float = 0.0
    
    # Behavior modifiers
    flee_distance_multiplier: float = 1.0
    activity_level: float = 1.0
    edge_preference: float = 0.0  # 0 = anywhere, 1 = edges only
    landing_allowed: bool = True
    
    # Time tracking
    time_in_state: float = 0.0
    last_spawn_time: float = 0.0


@dataclass
class WildlifeSnapshot:
    """Snapshot of wildlife state for a region."""
    # Overall state
    global_state: WildlifeState = WildlifeState.THRIVING
    population: float = 0.0
    
    # Per-category states
    creature_states: Dict[CreatureCategory, CreatureState] = field(default_factory=dict)
    
    # Aggregate metrics
    total_spawn_rate: float = 0.0
    average_activity: float = 1.0
    dominant_tier_state: Dict[CreatureTier, WildlifeState] = field(default_factory=dict)
    
    # Recovery info
    is_recovering: bool = False
    recovery_progress: float = 0.0  # 0 = just cleared, 1 = fully recovered
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'global_state': self.global_state.value,
            'population': self.population,
            'creature_states': {
                cat.value: {
                    'state': cs.state.value,
                    'spawn_rate': cs.current_spawn_rate,
                    'activity_level': cs.activity_level,
                    'edge_preference': cs.edge_preference,
                    'landing_allowed': cs.landing_allowed,
                } for cat, cs in self.creature_states.items()
            },
            'total_spawn_rate': self.total_spawn_rate,
            'average_activity': self.average_activity,
            'is_recovering': self.is_recovering,
            'recovery_progress': self.recovery_progress,
        }


# =============================================================================
# Wildlife Manager
# =============================================================================

class WildlifeManager:
    """
    Manages wildlife behavior for a region.
    
    Tracks per-creature states, handles transitions, and generates
    spawn commands for UE5.
    
    Example:
        >>> manager = WildlifeManager()
        >>> manager.set_population(0.45)
        >>> 
        >>> # Update each tick
        >>> snapshot = manager.update(delta_time=0.5)
        >>> 
        >>> # Get spawn commands for UE5
        >>> commands = manager.get_spawn_commands()
    """
    
    STATE_ORDER = [
        WildlifeState.THRIVING,
        WildlifeState.WARY,
        WildlifeState.RETREATING,
        WildlifeState.ABSENT,
    ]
    
    def __init__(self, config: Optional[WildlifeConfig] = None,
                 enabled_categories: Optional[Set[CreatureCategory]] = None):
        """
        Initialize wildlife manager.
        
        Args:
            config: Wildlife configuration
            enabled_categories: Which creature categories to track (None = all)
        """
        self.config = config or WildlifeConfig()
        self.enabled_categories = enabled_categories or set(CreatureCategory)
        
        # Initialize creature states
        self.creatures: Dict[CreatureCategory, CreatureState] = {}
        for category in self.enabled_categories:
            tier = CREATURE_TIERS[category]
            self.creatures[category] = CreatureState(
                category=category,
                tier=tier,
                current_spawn_rate=self.config.base_spawn_rates.get(category, 1.0),
                target_spawn_rate=self.config.base_spawn_rates.get(category, 1.0),
            )
        
        # Global state
        self._population = 0.0
        self._global_state = WildlifeState.THRIVING
        self._time = 0.0
        self._was_absent = False  # For recovery tracking
    
    def set_population(self, population: float) -> None:
        """Set current population ratio (0.0 to 1.0)."""
        self._population = max(0.0, min(1.0, population))
    
    def update(self, delta_time: float) -> WildlifeSnapshot:
        """
        Update wildlife state for one tick.
        
        Args:
            delta_time: Time since last update in seconds
            
        Returns:
            Current wildlife snapshot
        """
        self._time += delta_time
        
        # Determine target global state from population
        target_global = self._get_target_state(self._population)
        
        # Track if we were absent (for recovery)
        if self._global_state == WildlifeState.ABSENT:
            self._was_absent = True
        
        # Update each creature category
        for category, creature in self.creatures.items():
            self._update_creature(creature, target_global, delta_time)
        
        # Update global state (based on most sensitive creatures)
        self._update_global_state()
        
        # Generate snapshot
        return self._create_snapshot()
    
    def _get_target_state(self, population: float) -> WildlifeState:
        """Determine target state from population."""
        cfg = self.config
        
        if population < cfg.thriving_max_pop:
            return WildlifeState.THRIVING
        elif population < cfg.wary_max_pop:
            return WildlifeState.WARY
        elif population < cfg.retreating_max_pop:
            return WildlifeState.RETREATING
        else:
            return WildlifeState.ABSENT
    
    def _update_creature(self, creature: CreatureState, 
                         target_global: WildlifeState,
                         delta_time: float) -> None:
        """Update a single creature category."""
        cfg = self.config
        
        # Get tier sensitivity
        sensitivity = cfg.tier_sensitivity.get(creature.tier, 1.0)
        
        # Calculate tier-adjusted target state
        # More sensitive tiers transition at lower population
        tier_target = self._get_tier_adjusted_target(creature.tier, target_global)
        creature.target_state = tier_target
        
        # Handle state transitions
        if creature.state != tier_target:
            self._process_transition(creature, tier_target, sensitivity, delta_time)
        else:
            creature.transition_progress = 0.0
            creature.time_in_state += delta_time
        
        # Update spawn rate
        self._update_spawn_rate(creature, delta_time)
        
        # Update behavior modifiers
        self._update_behavior_modifiers(creature)
    
    def _get_tier_adjusted_target(self, tier: CreatureTier, 
                                   global_target: WildlifeState) -> WildlifeState:
        """
        Adjust target state based on tier sensitivity.
        
        Tier 1 creatures transition to worse states earlier.
        Tier 3 creatures stay in better states longer.
        
        Only applies adjustment when not at extremes (THRIVING or ABSENT).
        """
        state_idx = self.STATE_ORDER.index(global_target)
        
        # Only adjust in the middle states
        if global_target == WildlifeState.THRIVING:
            # At THRIVING, only Tier 1 might start getting wary at higher population
            if tier == CreatureTier.TIER_1 and self._population > 0.10:
                return WildlifeState.WARY
            return WildlifeState.THRIVING
        
        if global_target == WildlifeState.ABSENT:
            # At ABSENT, Tier 3 gets to be RETREATING instead
            if tier == CreatureTier.TIER_3:
                return WildlifeState.RETREATING
            return WildlifeState.ABSENT
        
        # In middle states, apply tier shifts
        if tier == CreatureTier.TIER_1:
            # More sensitive - shift toward worse state
            adjusted_idx = min(len(self.STATE_ORDER) - 1, state_idx + 1)
        elif tier == CreatureTier.TIER_3:
            # Less sensitive - shift toward better state
            adjusted_idx = max(0, state_idx - 1)
        else:
            adjusted_idx = state_idx
        
        return self.STATE_ORDER[adjusted_idx]
    
    def _process_transition(self, creature: CreatureState,
                            target: WildlifeState,
                            sensitivity: float,
                            delta_time: float) -> None:
        """Process state transition for a creature."""
        cfg = self.config
        current_idx = self.STATE_ORDER.index(creature.state)
        target_idx = self.STATE_ORDER.index(target)
        
        if target_idx > current_idx:
            # Fleeing (getting worse) - fast
            next_state = self.STATE_ORDER[current_idx + 1]
            transition_key = (creature.state, next_state)
            base_time = cfg.flee_times.get(transition_key, 5.0)
            
            # Sensitivity makes flee faster
            adjusted_time = base_time / sensitivity
            
        else:
            # Recovering (getting better) - slow
            next_state = self.STATE_ORDER[current_idx - 1]
            transition_key = (creature.state, next_state)
            base_time = cfg.recovery_times.get(transition_key, 30.0)
            
            # Sensitivity makes recovery slower for sensitive creatures
            adjusted_time = base_time * sensitivity
        
        # Progress transition
        creature.transition_progress += delta_time / adjusted_time
        
        if creature.transition_progress >= 1.0:
            creature.state = next_state
            creature.transition_progress = 0.0
            creature.time_in_state = 0.0
    
    def _update_spawn_rate(self, creature: CreatureState, delta_time: float) -> None:
        """Update spawn rate based on current state."""
        cfg = self.config
        
        # Base rate
        base_rate = cfg.base_spawn_rates.get(creature.category, 1.0)
        
        # State multiplier
        state_mult = cfg.state_spawn_multipliers.get(creature.state, 0.0)
        
        # Tier 3 never fully disappears
        if creature.tier == CreatureTier.TIER_3:
            state_mult = max(cfg.tier3_minimum_rate, state_mult)
        
        # Calculate target
        creature.target_spawn_rate = base_rate * state_mult
        
        # Smooth transition
        diff = creature.target_spawn_rate - creature.current_spawn_rate
        creature.current_spawn_rate += diff * min(1.0, delta_time * 2.0)
    
    def _update_behavior_modifiers(self, creature: CreatureState) -> None:
        """Update behavior modifiers based on state."""
        state = creature.state
        
        if state == WildlifeState.THRIVING:
            creature.flee_distance_multiplier = 1.0
            creature.activity_level = 1.0
            creature.edge_preference = 0.0
            creature.landing_allowed = True
            
        elif state == WildlifeState.WARY:
            creature.flee_distance_multiplier = 1.5
            creature.activity_level = 0.7
            creature.edge_preference = 0.3
            creature.landing_allowed = True  # But reduced duration
            
        elif state == WildlifeState.RETREATING:
            creature.flee_distance_multiplier = 2.5
            creature.activity_level = 0.3
            creature.edge_preference = 0.8
            creature.landing_allowed = False
            
        else:  # ABSENT
            creature.flee_distance_multiplier = 5.0
            creature.activity_level = 0.0
            creature.edge_preference = 1.0
            creature.landing_allowed = False
    
    def _update_global_state(self) -> None:
        """Update global state based on creature states."""
        # Global state is determined by Tier 1 creatures (most sensitive)
        tier1_states = [
            c.state for c in self.creatures.values() 
            if c.tier == CreatureTier.TIER_1
        ]
        
        if tier1_states:
            # Use the worst state among Tier 1
            worst_idx = max(self.STATE_ORDER.index(s) for s in tier1_states)
            self._global_state = self.STATE_ORDER[worst_idx]
        else:
            # Fall back to population-based
            self._global_state = self._get_target_state(self._population)
    
    def _create_snapshot(self) -> WildlifeSnapshot:
        """Create a snapshot of current wildlife state."""
        snapshot = WildlifeSnapshot()
        snapshot.global_state = self._global_state
        snapshot.population = self._population
        snapshot.creature_states = dict(self.creatures)
        
        # Calculate aggregates
        if self.creatures:
            snapshot.total_spawn_rate = sum(
                c.current_spawn_rate for c in self.creatures.values()
            )
            snapshot.average_activity = sum(
                c.activity_level for c in self.creatures.values()
            ) / len(self.creatures)
        
        # Per-tier dominant state
        for tier in CreatureTier:
            tier_creatures = [c for c in self.creatures.values() if c.tier == tier]
            if tier_creatures:
                worst_idx = max(
                    self.STATE_ORDER.index(c.state) for c in tier_creatures
                )
                snapshot.dominant_tier_state[tier] = self.STATE_ORDER[worst_idx]
        
        # Recovery tracking
        snapshot.is_recovering = (
            self._was_absent and 
            self._global_state != WildlifeState.ABSENT
        )
        
        if snapshot.is_recovering:
            # Calculate recovery progress
            state_idx = self.STATE_ORDER.index(self._global_state)
            # 0 = ABSENT (just started), 3 = THRIVING (fully recovered)
            # But we're recovering, so we're between RETREATING and THRIVING
            snapshot.recovery_progress = 1.0 - (state_idx / 3.0)
        elif self._global_state == WildlifeState.THRIVING:
            snapshot.recovery_progress = 1.0
            self._was_absent = False  # Reset recovery tracking
        
        return snapshot
    
    def get_spawn_commands(self) -> List[Dict[str, Any]]:
        """
        Generate spawn commands for UE5.
        
        Returns list of spawn command dictionaries.
        """
        commands = []
        
        for category, creature in self.creatures.items():
            if creature.current_spawn_rate > 0.01:
                commands.append({
                    'category': category.value,
                    'tier': creature.tier.value,
                    'spawn_rate_per_minute': creature.current_spawn_rate,
                    'spawn_rate_per_second': creature.current_spawn_rate / 60.0,
                    'state': creature.state.value,
                    'behavior': {
                        'flee_distance_multiplier': creature.flee_distance_multiplier,
                        'activity_level': creature.activity_level,
                        'edge_preference': creature.edge_preference,
                        'landing_allowed': creature.landing_allowed,
                    },
                    'transition': {
                        'target_state': creature.target_state.value,
                        'progress': creature.transition_progress,
                        'time_in_state': creature.time_in_state,
                    },
                })
        
        return commands
    
    def get_tier_summary(self) -> Dict[str, Any]:
        """Get summary by tier."""
        summary = {}
        
        for tier in CreatureTier:
            tier_creatures = [c for c in self.creatures.values() if c.tier == tier]
            if tier_creatures:
                summary[f'tier_{tier.value}'] = {
                    'count': len(tier_creatures),
                    'total_spawn_rate': sum(c.current_spawn_rate for c in tier_creatures),
                    'average_activity': sum(c.activity_level for c in tier_creatures) / len(tier_creatures),
                    'states': [c.state.value for c in tier_creatures],
                }
        
        return summary
    
    def reset(self) -> None:
        """Reset to initial state."""
        for creature in self.creatures.values():
            creature.state = WildlifeState.THRIVING
            creature.target_state = WildlifeState.THRIVING
            creature.transition_progress = 0.0
            creature.current_spawn_rate = self.config.base_spawn_rates.get(
                creature.category, 1.0
            )
            creature.target_spawn_rate = creature.current_spawn_rate
            creature.flee_distance_multiplier = 1.0
            creature.activity_level = 1.0
            creature.edge_preference = 0.0
            creature.landing_allowed = True
            creature.time_in_state = 0.0
        
        self._population = 0.0
        self._global_state = WildlifeState.THRIVING
        self._time = 0.0
        self._was_absent = False
    
    @property
    def global_state(self) -> WildlifeState:
        """Current global wildlife state."""
        return self._global_state
    
    @property
    def population(self) -> float:
        """Current population."""
        return self._population


# =============================================================================
# UE5 Spawn Command Generator
# =============================================================================

@dataclass
class FWildlifeSpawnCommand:
    """UE5-ready spawn command for wildlife."""
    # Identity
    category: str
    tier: int
    
    # Spawn timing
    spawn_rate_per_second: float
    spawn_burst_count: int = 1
    spawn_delay_variance: float = 0.2
    
    # Location
    spawn_radius_min: float = 500.0      # cm from region center
    spawn_radius_max: float = 2000.0     # cm
    edge_bias: float = 0.0               # 0 = uniform, 1 = edges only
    height_offset_min: float = 0.0       # cm above ground
    height_offset_max: float = 0.0       # cm
    
    # Behavior overrides
    flee_distance: float = 500.0         # cm
    activity_multiplier: float = 1.0
    landing_enabled: bool = True
    landing_duration_max: float = 10.0   # seconds
    
    # Visual
    scale_variance: float = 0.1          # Random scale variation
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export as JSON for UE5."""
        return {
            'Category': self.category,
            'Tier': self.tier,
            'SpawnRatePerSecond': self.spawn_rate_per_second,
            'SpawnBurstCount': self.spawn_burst_count,
            'SpawnDelayVariance': self.spawn_delay_variance,
            'SpawnRadiusMin': self.spawn_radius_min,
            'SpawnRadiusMax': self.spawn_radius_max,
            'EdgeBias': self.edge_bias,
            'HeightOffsetMin': self.height_offset_min,
            'HeightOffsetMax': self.height_offset_max,
            'FleeDistance': self.flee_distance,
            'ActivityMultiplier': self.activity_multiplier,
            'LandingEnabled': self.landing_enabled,
            'LandingDurationMax': self.landing_duration_max,
            'ScaleVariance': self.scale_variance,
        }


class WildlifeSpawnGenerator:
    """
    Generates UE5 spawn commands from wildlife manager state.
    
    Converts abstract wildlife state into concrete spawn parameters.
    """
    
    # Base parameters per category
    CATEGORY_PARAMS = {
        CreatureCategory.BIRDS_SMALL: {
            'spawn_radius': (800, 2500),
            'height_offset': (50, 300),
            'base_flee_distance': 400,
            'landing_duration': 8.0,
        },
        CreatureCategory.BIRDS_LARGE: {
            'spawn_radius': (1000, 3000),
            'height_offset': (100, 500),
            'base_flee_distance': 600,
            'landing_duration': 15.0,
        },
        CreatureCategory.DEER: {
            'spawn_radius': (1500, 4000),
            'height_offset': (0, 0),
            'base_flee_distance': 800,
            'landing_duration': 0,  # N/A
        },
        CreatureCategory.LARGE_FAUNA: {
            'spawn_radius': (2000, 5000),
            'height_offset': (0, 0),
            'base_flee_distance': 1000,
            'landing_duration': 0,
        },
        CreatureCategory.SMALL_MAMMALS: {
            'spawn_radius': (500, 2000),
            'height_offset': (0, 50),
            'base_flee_distance': 300,
            'landing_duration': 0,
        },
        CreatureCategory.REPTILES: {
            'spawn_radius': (300, 1500),
            'height_offset': (0, 20),
            'base_flee_distance': 200,
            'landing_duration': 0,
        },
        CreatureCategory.AMPHIBIANS: {
            'spawn_radius': (200, 1000),
            'height_offset': (0, 10),
            'base_flee_distance': 150,
            'landing_duration': 0,
        },
        CreatureCategory.INSECTS_FLYING: {
            'spawn_radius': (100, 800),
            'height_offset': (20, 200),
            'base_flee_distance': 100,
            'landing_duration': 3.0,
        },
        CreatureCategory.INSECTS_GROUND: {
            'spawn_radius': (50, 500),
            'height_offset': (0, 5),
            'base_flee_distance': 50,
            'landing_duration': 0,
        },
        CreatureCategory.FISH: {
            'spawn_radius': (100, 600),
            'height_offset': (-100, -20),  # Below water surface
            'base_flee_distance': 150,
            'landing_duration': 0,
        },
        CreatureCategory.AMBIENT_SOUNDS: {
            'spawn_radius': (500, 3000),
            'height_offset': (0, 200),
            'base_flee_distance': 0,  # N/A - audio only
            'landing_duration': 0,
        },
    }
    
    def generate_commands(self, manager: WildlifeManager) -> List[FWildlifeSpawnCommand]:
        """Generate spawn commands from wildlife manager."""
        commands = []
        
        for category, creature in manager.creatures.items():
            if creature.current_spawn_rate < 0.01:
                continue
            
            params = self.CATEGORY_PARAMS.get(category, {})
            
            cmd = FWildlifeSpawnCommand(
                category=category.value,
                tier=creature.tier.value,
                spawn_rate_per_second=creature.current_spawn_rate / 60.0,
            )
            
            # Location params
            radius = params.get('spawn_radius', (500, 2000))
            cmd.spawn_radius_min = radius[0]
            cmd.spawn_radius_max = radius[1]
            cmd.edge_bias = creature.edge_preference
            
            height = params.get('height_offset', (0, 0))
            cmd.height_offset_min = height[0]
            cmd.height_offset_max = height[1]
            
            # Behavior params
            base_flee = params.get('base_flee_distance', 500)
            cmd.flee_distance = base_flee * creature.flee_distance_multiplier
            cmd.activity_multiplier = creature.activity_level
            cmd.landing_enabled = creature.landing_allowed
            
            landing_dur = params.get('landing_duration', 0)
            if creature.state == WildlifeState.WARY:
                landing_dur *= 0.5  # Shorter landings when wary
            cmd.landing_duration_max = landing_dur
            
            commands.append(cmd)
        
        return commands
    
    def to_ue5_json(self, manager: WildlifeManager) -> Dict[str, Any]:
        """Generate complete UE5 JSON payload."""
        snapshot = manager.update(0.0)  # Get current state without advancing time
        commands = self.generate_commands(manager)
        
        return {
            'GlobalState': snapshot.global_state.value,
            'Population': snapshot.population,
            'TotalSpawnRate': snapshot.total_spawn_rate,
            'AverageActivity': snapshot.average_activity,
            'IsRecovering': snapshot.is_recovering,
            'RecoveryProgress': snapshot.recovery_progress,
            'TierStates': {
                f'Tier{k.value}': v.value 
                for k, v in snapshot.dominant_tier_state.items()
            },
            'SpawnCommands': [cmd.to_ue5_json() for cmd in commands],
        }
