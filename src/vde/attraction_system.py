"""
VDE Phase 7: Attraction System

Pulling is harder than pushing. This system makes other places appealing.

When a region broadcasts high pressure, neighboring low-population regions
receive attraction signals that make them more appealing without obvious
game mechanics.

This module handles:
- Cross-region attraction signaling
- Distant visual cues (light, birds, smoke, movement)
- Attraction boost calculations
- Visual breadcrumb generation
- UE5-ready attraction parameters

Key insight: Players should feel drawn to quieter areas without understanding
why. The attraction must be subtle, plausible, and never feel like a game
mechanic pushing them around.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
import math


# =============================================================================
# Enums and Constants
# =============================================================================

class AttractionSignal(Enum):
    """Types of attraction signals that can be broadcast."""
    LIGHT_QUALITY = "light_quality"       # Better lighting in quiet areas
    WILDLIFE_SURGE = "wildlife_surge"     # More wildlife activity
    VISUAL_CLARITY = "visual_clarity"     # Less haze, more contrast
    MOTION_COHERENCE = "motion_coherence" # Synchronized motion
    NPC_VITALITY = "npc_vitality"         # Relaxed, varied NPC behaviors


class DistantCue(Enum):
    """Visual cues visible from a distance."""
    LIGHT_SHAFTS = "light_shafts"         # God rays through trees
    BIRD_ACTIVITY = "bird_activity"       # Birds circling/landing
    PEACEFUL_SMOKE = "peaceful_smoke"     # Chimney smoke, campfires
    DISTANT_MOVEMENT = "distant_movement" # Subtle movement at edge of vision
    CLEAR_SKY = "clear_sky"               # Visible blue sky patches
    WATER_GLINTS = "water_glints"         # Sunlight on water


class AttractionStrength(Enum):
    """Strength levels for attraction effects."""
    NONE = "none"           # No attraction (high pop)
    SUBTLE = "subtle"       # Barely noticeable
    MODERATE = "moderate"   # Noticeable if looking
    STRONG = "strong"       # Clear draw
    BEACON = "beacon"       # Maximum attraction


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class AttractionConfig:
    """Configuration for attraction system."""
    
    # Population thresholds for attraction strength
    # Note: LOWER population = MORE attraction
    beacon_max_pop: float = 0.10    # Below this = BEACON
    strong_max_pop: float = 0.25    # Below this = STRONG
    moderate_max_pop: float = 0.40  # Below this = MODERATE
    subtle_max_pop: float = 0.60    # Below this = SUBTLE
    # Above subtle_max_pop = NONE
    
    # Signal boost amounts per strength level
    signal_boosts: Dict[AttractionStrength, Dict[AttractionSignal, float]] = field(
        default_factory=lambda: {
            AttractionStrength.NONE: {
                AttractionSignal.LIGHT_QUALITY: 0.0,
                AttractionSignal.WILDLIFE_SURGE: 0.0,
                AttractionSignal.VISUAL_CLARITY: 0.0,
                AttractionSignal.MOTION_COHERENCE: 0.0,
                AttractionSignal.NPC_VITALITY: 0.0,
            },
            AttractionStrength.SUBTLE: {
                AttractionSignal.LIGHT_QUALITY: 0.05,
                AttractionSignal.WILDLIFE_SURGE: 0.08,
                AttractionSignal.VISUAL_CLARITY: 0.03,
                AttractionSignal.MOTION_COHERENCE: 0.05,
                AttractionSignal.NPC_VITALITY: 0.05,
            },
            AttractionStrength.MODERATE: {
                AttractionSignal.LIGHT_QUALITY: 0.10,
                AttractionSignal.WILDLIFE_SURGE: 0.15,
                AttractionSignal.VISUAL_CLARITY: 0.07,
                AttractionSignal.MOTION_COHERENCE: 0.10,
                AttractionSignal.NPC_VITALITY: 0.10,
            },
            AttractionStrength.STRONG: {
                AttractionSignal.LIGHT_QUALITY: 0.15,
                AttractionSignal.WILDLIFE_SURGE: 0.25,
                AttractionSignal.VISUAL_CLARITY: 0.10,
                AttractionSignal.MOTION_COHERENCE: 0.15,
                AttractionSignal.NPC_VITALITY: 0.15,
            },
            AttractionStrength.BEACON: {
                AttractionSignal.LIGHT_QUALITY: 0.20,
                AttractionSignal.WILDLIFE_SURGE: 0.35,
                AttractionSignal.VISUAL_CLARITY: 0.15,
                AttractionSignal.MOTION_COHERENCE: 0.20,
                AttractionSignal.NPC_VITALITY: 0.20,
            },
        }
    )
    
    # Distant cue thresholds (strength required to show cue)
    distant_cue_thresholds: Dict[DistantCue, AttractionStrength] = field(
        default_factory=lambda: {
            DistantCue.LIGHT_SHAFTS: AttractionStrength.MODERATE,
            DistantCue.BIRD_ACTIVITY: AttractionStrength.SUBTLE,
            DistantCue.PEACEFUL_SMOKE: AttractionStrength.MODERATE,
            DistantCue.DISTANT_MOVEMENT: AttractionStrength.SUBTLE,
            DistantCue.CLEAR_SKY: AttractionStrength.STRONG,
            DistantCue.WATER_GLINTS: AttractionStrength.MODERATE,
        }
    )
    
    # Cross-region influence
    neighbor_influence_radius: float = 1000.0  # cm
    neighbor_influence_falloff: float = 0.5    # How much influence drops with distance
    
    # Timing
    attraction_ramp_rate: float = 0.1    # How fast attraction builds
    attraction_decay_rate: float = 0.05  # How fast attraction fades
    
    # Smoothing
    smoothing_rate: float = 0.08


# =============================================================================
# Region State
# =============================================================================

@dataclass
class RegionAttractionState:
    """Attraction state for a single region."""
    region_id: str
    
    # Population
    population: float = 0.0
    
    # Attraction
    attraction_strength: AttractionStrength = AttractionStrength.NONE
    attraction_value: float = 0.0  # 0-1, smoothed
    target_attraction: float = 0.0
    
    # Signal boosts
    signal_boosts: Dict[AttractionSignal, float] = field(default_factory=dict)
    
    # Active distant cues
    active_cues: Set[DistantCue] = field(default_factory=set)
    cue_intensities: Dict[DistantCue, float] = field(default_factory=dict)
    
    # Neighbor influence
    neighbor_pressure: float = 0.0  # Pressure from crowded neighbors
    is_receiving_overflow: bool = False
    
    # Position (for cross-region calculations)
    position: Tuple[float, float] = (0.0, 0.0)
    
    def __post_init__(self):
        """Initialize signal boosts."""
        if not self.signal_boosts:
            for signal in AttractionSignal:
                self.signal_boosts[signal] = 0.0
        if not self.cue_intensities:
            for cue in DistantCue:
                self.cue_intensities[cue] = 0.0


@dataclass 
class AttractionSnapshot:
    """Snapshot of attraction system state."""
    region_id: str
    population: float = 0.0
    
    # Attraction
    attraction_strength: AttractionStrength = AttractionStrength.NONE
    attraction_value: float = 0.0
    
    # Signals
    signal_boosts: Dict[AttractionSignal, float] = field(default_factory=dict)
    
    # Cues
    active_cues: List[DistantCue] = field(default_factory=list)
    cue_intensities: Dict[DistantCue, float] = field(default_factory=dict)
    
    # Cross-region
    neighbor_pressure: float = 0.0
    is_receiving_overflow: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'region_id': self.region_id,
            'population': self.population,
            'attraction_strength': self.attraction_strength.value,
            'attraction_value': self.attraction_value,
            'signal_boosts': {k.value: v for k, v in self.signal_boosts.items()},
            'active_cues': [c.value for c in self.active_cues],
            'cue_intensities': {k.value: v for k, v in self.cue_intensities.items()},
            'neighbor_pressure': self.neighbor_pressure,
            'is_receiving_overflow': self.is_receiving_overflow,
        }


# =============================================================================
# Attraction Manager (Single Region)
# =============================================================================

class AttractionManager:
    """
    Manages attraction for a single region.
    
    Calculates attraction signals based on local population and
    pressure from neighboring regions.
    
    Example:
        >>> manager = AttractionManager("forest_clearing")
        >>> manager.set_population(0.15)
        >>> manager.set_neighbor_pressure(0.70)  # Crowded neighbor
        >>> 
        >>> snapshot = manager.update(delta_time=0.5)
        >>> params = manager.get_ue5_parameters()
    """
    
    STRENGTH_ORDER = [
        AttractionStrength.NONE,
        AttractionStrength.SUBTLE,
        AttractionStrength.MODERATE,
        AttractionStrength.STRONG,
        AttractionStrength.BEACON,
    ]
    
    def __init__(self, region_id: str, 
                 config: Optional[AttractionConfig] = None,
                 position: Tuple[float, float] = (0.0, 0.0)):
        """
        Initialize attraction manager.
        
        Args:
            region_id: Unique identifier for the region
            config: Attraction configuration
            position: Region position for cross-region calculations
        """
        self.region_id = region_id
        self.config = config or AttractionConfig()
        
        # State
        self.state = RegionAttractionState(
            region_id=region_id,
            position=position,
        )
        
        self._time = 0.0
    
    def set_population(self, population: float) -> None:
        """Set current population ratio (0.0 to 1.0)."""
        self.state.population = max(0.0, min(1.0, population))
    
    def set_neighbor_pressure(self, pressure: float) -> None:
        """Set pressure from neighboring crowded regions (0.0 to 1.0)."""
        self.state.neighbor_pressure = max(0.0, min(1.0, pressure))
        self.state.is_receiving_overflow = pressure > 0.5
    
    def update(self, delta_time: float) -> AttractionSnapshot:
        """
        Update attraction state for one tick.
        
        Args:
            delta_time: Time since last update in seconds
            
        Returns:
            Current attraction snapshot
        """
        self._time += delta_time
        cfg = self.config
        
        # Determine base attraction strength from population
        base_strength = self._get_attraction_strength(self.state.population)
        
        # Boost attraction if neighbors are crowded
        if self.state.neighbor_pressure > 0.5:
            # Crowded neighbors make this region more attractive
            boost_level = min(2, self.STRENGTH_ORDER.index(base_strength) + 1)
            base_strength = self.STRENGTH_ORDER[boost_level]
        
        self.state.attraction_strength = base_strength
        
        # Calculate target attraction value (0-1)
        strength_idx = self.STRENGTH_ORDER.index(base_strength)
        self.state.target_attraction = strength_idx / (len(self.STRENGTH_ORDER) - 1)
        
        # Smooth transition
        diff = self.state.target_attraction - self.state.attraction_value
        rate = cfg.attraction_ramp_rate if diff > 0 else cfg.attraction_decay_rate
        self.state.attraction_value += diff * min(1.0, delta_time * rate * 10)
        
        # Update signal boosts
        self._update_signals()
        
        # Update distant cues
        self._update_distant_cues()
        
        return self._create_snapshot()
    
    def _get_attraction_strength(self, population: float) -> AttractionStrength:
        """Determine attraction strength from population."""
        cfg = self.config
        
        # Lower population = higher attraction
        if population < cfg.beacon_max_pop:
            return AttractionStrength.BEACON
        elif population < cfg.strong_max_pop:
            return AttractionStrength.STRONG
        elif population < cfg.moderate_max_pop:
            return AttractionStrength.MODERATE
        elif population < cfg.subtle_max_pop:
            return AttractionStrength.SUBTLE
        else:
            return AttractionStrength.NONE
    
    def _update_signals(self) -> None:
        """Update attraction signal boosts."""
        cfg = self.config
        strength = self.state.attraction_strength
        
        boosts = cfg.signal_boosts.get(strength, {})
        
        for signal in AttractionSignal:
            target = boosts.get(signal, 0.0)
            current = self.state.signal_boosts.get(signal, 0.0)
            
            # Smooth transition
            diff = target - current
            self.state.signal_boosts[signal] = current + diff * cfg.smoothing_rate
    
    def _update_distant_cues(self) -> None:
        """Update active distant cues based on attraction strength."""
        cfg = self.config
        strength = self.state.attraction_strength
        strength_idx = self.STRENGTH_ORDER.index(strength)
        
        self.state.active_cues.clear()
        
        for cue, threshold in cfg.distant_cue_thresholds.items():
            threshold_idx = self.STRENGTH_ORDER.index(threshold)
            
            if strength_idx >= threshold_idx:
                self.state.active_cues.add(cue)
                
                # Calculate intensity based on how far above threshold
                intensity = (strength_idx - threshold_idx + 1) / len(self.STRENGTH_ORDER)
                self.state.cue_intensities[cue] = min(1.0, intensity)
            else:
                self.state.cue_intensities[cue] = 0.0
    
    def _create_snapshot(self) -> AttractionSnapshot:
        """Create a snapshot of current attraction state."""
        return AttractionSnapshot(
            region_id=self.region_id,
            population=self.state.population,
            attraction_strength=self.state.attraction_strength,
            attraction_value=self.state.attraction_value,
            signal_boosts=dict(self.state.signal_boosts),
            active_cues=list(self.state.active_cues),
            cue_intensities=dict(self.state.cue_intensities),
            neighbor_pressure=self.state.neighbor_pressure,
            is_receiving_overflow=self.state.is_receiving_overflow,
        )
    
    def get_ue5_parameters(self) -> 'FAttractionParameters':
        """Generate UE5-ready attraction parameters."""
        return FAttractionParameters.from_manager(self)
    
    def reset(self) -> None:
        """Reset attraction state."""
        self.state.population = 0.0
        self.state.attraction_strength = AttractionStrength.NONE
        self.state.attraction_value = 0.0
        self.state.target_attraction = 0.0
        self.state.neighbor_pressure = 0.0
        self.state.is_receiving_overflow = False
        
        for signal in AttractionSignal:
            self.state.signal_boosts[signal] = 0.0
        
        self.state.active_cues.clear()
        for cue in DistantCue:
            self.state.cue_intensities[cue] = 0.0
        
        self._time = 0.0
    
    @property
    def attraction_strength(self) -> AttractionStrength:
        """Current attraction strength."""
        return self.state.attraction_strength
    
    @property
    def attraction_value(self) -> float:
        """Current attraction value (0-1)."""
        return self.state.attraction_value
    
    @property
    def population(self) -> float:
        """Current population."""
        return self.state.population


# =============================================================================
# Cross-Region Coordinator
# =============================================================================

class AttractionCoordinator:
    """
    Coordinates attraction across multiple regions.
    
    Handles cross-region signaling where crowded regions boost
    the attraction of nearby quiet regions.
    
    Example:
        >>> coordinator = AttractionCoordinator()
        >>> coordinator.add_region("marketplace", position=(0, 0))
        >>> coordinator.add_region("forest_path", position=(500, 0))
        >>> coordinator.add_region("quiet_grove", position=(1000, 0))
        >>> 
        >>> coordinator.set_population("marketplace", 0.85)
        >>> coordinator.set_population("forest_path", 0.40)
        >>> coordinator.set_population("quiet_grove", 0.10)
        >>> 
        >>> snapshots = coordinator.update(delta_time=0.5)
        >>> # quiet_grove will have boosted attraction due to marketplace pressure
    """
    
    def __init__(self, config: Optional[AttractionConfig] = None):
        """
        Initialize attraction coordinator.
        
        Args:
            config: Shared attraction configuration
        """
        self.config = config or AttractionConfig()
        self.regions: Dict[str, AttractionManager] = {}
        self._time = 0.0
    
    def add_region(self, region_id: str, 
                   position: Tuple[float, float] = (0.0, 0.0)) -> None:
        """Add a region to coordinate."""
        self.regions[region_id] = AttractionManager(
            region_id=region_id,
            config=self.config,
            position=position,
        )
    
    def remove_region(self, region_id: str) -> None:
        """Remove a region from coordination."""
        if region_id in self.regions:
            del self.regions[region_id]
    
    def set_population(self, region_id: str, population: float) -> None:
        """Set population for a specific region."""
        if region_id in self.regions:
            self.regions[region_id].set_population(population)
    
    def update(self, delta_time: float) -> Dict[str, AttractionSnapshot]:
        """
        Update all regions with cross-region influence.
        
        Args:
            delta_time: Time since last update in seconds
            
        Returns:
            Snapshots for all regions
        """
        self._time += delta_time
        
        # First, calculate neighbor pressure for each region
        self._calculate_neighbor_pressures()
        
        # Then update each region
        snapshots = {}
        for region_id, manager in self.regions.items():
            snapshots[region_id] = manager.update(delta_time)
        
        return snapshots
    
    def _calculate_neighbor_pressures(self) -> None:
        """Calculate neighbor pressure for each region."""
        cfg = self.config
        
        for target_id, target in self.regions.items():
            total_pressure = 0.0
            influence_count = 0
            
            for source_id, source in self.regions.items():
                if source_id == target_id:
                    continue
                
                # Calculate distance
                dx = target.state.position[0] - source.state.position[0]
                dy = target.state.position[1] - source.state.position[1]
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance > cfg.neighbor_influence_radius:
                    continue
                
                # Calculate influence based on distance
                influence = 1.0 - (distance / cfg.neighbor_influence_radius)
                influence *= cfg.neighbor_influence_falloff
                
                # Only crowded regions exert pressure
                if source.state.population > 0.5:
                    pressure = source.state.population * influence
                    total_pressure += pressure
                    influence_count += 1
            
            # Set average pressure
            if influence_count > 0:
                target.set_neighbor_pressure(total_pressure / influence_count)
            else:
                target.set_neighbor_pressure(0.0)
    
    def get_region_parameters(self, region_id: str) -> Optional['FAttractionParameters']:
        """Get UE5 parameters for a specific region."""
        if region_id in self.regions:
            return self.regions[region_id].get_ue5_parameters()
        return None
    
    def get_all_parameters(self) -> Dict[str, 'FAttractionParameters']:
        """Get UE5 parameters for all regions."""
        return {
            region_id: manager.get_ue5_parameters()
            for region_id, manager in self.regions.items()
        }
    
    def get_most_attractive_region(self) -> Optional[str]:
        """Get the region with highest attraction."""
        if not self.regions:
            return None
        
        return max(
            self.regions.keys(),
            key=lambda r: self.regions[r].attraction_value
        )
    
    def get_pressure_map(self) -> Dict[str, float]:
        """Get population pressure for all regions."""
        return {
            region_id: manager.state.population
            for region_id, manager in self.regions.items()
        }
    
    def get_attraction_map(self) -> Dict[str, float]:
        """Get attraction values for all regions."""
        return {
            region_id: manager.attraction_value
            for region_id, manager in self.regions.items()
        }
    
    def reset(self) -> None:
        """Reset all regions."""
        for manager in self.regions.values():
            manager.reset()
        self._time = 0.0
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Generate complete UE5 JSON payload."""
        most_attractive = self.get_most_attractive_region()
        
        return {
            'Regions': {
                region_id: manager.get_ue5_parameters().to_ue5_json()
                for region_id, manager in self.regions.items()
            },
            'MostAttractiveRegion': most_attractive,
            'PressureMap': self.get_pressure_map(),
            'AttractionMap': self.get_attraction_map(),
        }


# =============================================================================
# UE5 Parameters
# =============================================================================

@dataclass
class FAttractionParameters:
    """UE5-ready attraction parameters."""
    
    # Core attraction
    attraction_strength: str = "none"
    attraction_value: float = 0.0
    
    # Signal boosts (additive modifiers)
    light_quality_boost: float = 0.0      # Add to lighting quality
    wildlife_surge_boost: float = 0.0     # Add to wildlife spawn rate
    visual_clarity_boost: float = 0.0     # Add to contrast, subtract from haze
    motion_coherence_boost: float = 0.0   # Add to motion coherence
    npc_vitality_boost: float = 0.0       # Add to NPC behavior variety
    
    # Distant cues
    light_shafts_intensity: float = 0.0   # God ray intensity
    bird_activity_intensity: float = 0.0  # Distant bird spawning
    peaceful_smoke_intensity: float = 0.0 # Chimney/campfire smoke
    distant_movement_intensity: float = 0.0  # Edge-of-vision movement
    clear_sky_intensity: float = 0.0      # Sky visibility
    water_glints_intensity: float = 0.0   # Water reflection
    
    # Cross-region
    neighbor_pressure: float = 0.0
    is_overflow_target: bool = False
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export as JSON for UE5."""
        return {
            'Attraction_Strength': self.attraction_strength,
            'Attraction_Value': self.attraction_value,
            'Boost_LightQuality': self.light_quality_boost,
            'Boost_WildlifeSurge': self.wildlife_surge_boost,
            'Boost_VisualClarity': self.visual_clarity_boost,
            'Boost_MotionCoherence': self.motion_coherence_boost,
            'Boost_NPCVitality': self.npc_vitality_boost,
            'Cue_LightShafts': self.light_shafts_intensity,
            'Cue_BirdActivity': self.bird_activity_intensity,
            'Cue_PeacefulSmoke': self.peaceful_smoke_intensity,
            'Cue_DistantMovement': self.distant_movement_intensity,
            'Cue_ClearSky': self.clear_sky_intensity,
            'Cue_WaterGlints': self.water_glints_intensity,
            'CrossRegion_NeighborPressure': self.neighbor_pressure,
            'CrossRegion_IsOverflowTarget': self.is_overflow_target,
        }
    
    @classmethod
    def from_manager(cls, manager: AttractionManager) -> 'FAttractionParameters':
        """Create parameters from attraction manager state."""
        params = cls()
        state = manager.state
        
        params.attraction_strength = state.attraction_strength.value
        params.attraction_value = state.attraction_value
        
        # Signal boosts
        params.light_quality_boost = state.signal_boosts.get(
            AttractionSignal.LIGHT_QUALITY, 0.0
        )
        params.wildlife_surge_boost = state.signal_boosts.get(
            AttractionSignal.WILDLIFE_SURGE, 0.0
        )
        params.visual_clarity_boost = state.signal_boosts.get(
            AttractionSignal.VISUAL_CLARITY, 0.0
        )
        params.motion_coherence_boost = state.signal_boosts.get(
            AttractionSignal.MOTION_COHERENCE, 0.0
        )
        params.npc_vitality_boost = state.signal_boosts.get(
            AttractionSignal.NPC_VITALITY, 0.0
        )
        
        # Distant cues
        params.light_shafts_intensity = state.cue_intensities.get(
            DistantCue.LIGHT_SHAFTS, 0.0
        )
        params.bird_activity_intensity = state.cue_intensities.get(
            DistantCue.BIRD_ACTIVITY, 0.0
        )
        params.peaceful_smoke_intensity = state.cue_intensities.get(
            DistantCue.PEACEFUL_SMOKE, 0.0
        )
        params.distant_movement_intensity = state.cue_intensities.get(
            DistantCue.DISTANT_MOVEMENT, 0.0
        )
        params.clear_sky_intensity = state.cue_intensities.get(
            DistantCue.CLEAR_SKY, 0.0
        )
        params.water_glints_intensity = state.cue_intensities.get(
            DistantCue.WATER_GLINTS, 0.0
        )
        
        # Cross-region
        params.neighbor_pressure = state.neighbor_pressure
        params.is_overflow_target = state.is_receiving_overflow
        
        return params


# =============================================================================
# Distant Cue Generator
# =============================================================================

@dataclass
class DistantCueCommand:
    """Command for spawning a distant visual cue."""
    cue_type: DistantCue
    intensity: float
    position: Tuple[float, float, float]  # x, y, z
    direction: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    scale: float = 1.0
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export as JSON for UE5."""
        return {
            'CueType': self.cue_type.value,
            'Intensity': self.intensity,
            'Position': {'X': self.position[0], 'Y': self.position[1], 'Z': self.position[2]},
            'Direction': {'X': self.direction[0], 'Y': self.direction[1], 'Z': self.direction[2]},
            'Scale': self.scale,
        }


class DistantCueGenerator:
    """
    Generates distant visual cue commands for UE5.
    
    Creates spawn commands for visual breadcrumbs that draw
    players toward attractive regions.
    """
    
    # Default spawn parameters per cue type
    CUE_DEFAULTS: Dict[DistantCue, Dict[str, Any]] = {
        DistantCue.LIGHT_SHAFTS: {
            'height_min': 500.0,
            'height_max': 1500.0,
            'scale_range': (0.8, 1.5),
        },
        DistantCue.BIRD_ACTIVITY: {
            'height_min': 300.0,
            'height_max': 800.0,
            'scale_range': (0.5, 1.0),
            'count_range': (3, 8),
        },
        DistantCue.PEACEFUL_SMOKE: {
            'height_min': 200.0,
            'height_max': 400.0,
            'scale_range': (0.6, 1.2),
        },
        DistantCue.DISTANT_MOVEMENT: {
            'height_min': 0.0,
            'height_max': 200.0,
            'scale_range': (0.3, 0.7),
        },
        DistantCue.CLEAR_SKY: {
            'height_min': 2000.0,
            'height_max': 5000.0,
            'scale_range': (1.0, 2.0),
        },
        DistantCue.WATER_GLINTS: {
            'height_min': 0.0,
            'height_max': 50.0,
            'scale_range': (0.5, 1.5),
        },
    }
    
    def __init__(self):
        """Initialize cue generator."""
        import random
        self._rng = random.Random(42)
    
    def generate_cues(self, manager: AttractionManager) -> List[DistantCueCommand]:
        """Generate distant cue commands for a region."""
        commands = []
        state = manager.state
        
        for cue in state.active_cues:
            intensity = state.cue_intensities.get(cue, 0.0)
            if intensity < 0.1:
                continue
            
            defaults = self.CUE_DEFAULTS.get(cue, {})
            
            # Generate position
            pos_x = state.position[0] + (self._rng.random() - 0.5) * 200
            pos_y = state.position[1] + (self._rng.random() - 0.5) * 200
            pos_z = self._rng.uniform(
                defaults.get('height_min', 100),
                defaults.get('height_max', 500)
            )
            
            # Generate scale
            scale_min, scale_max = defaults.get('scale_range', (0.8, 1.2))
            scale = self._rng.uniform(scale_min, scale_max)
            
            cmd = DistantCueCommand(
                cue_type=cue,
                intensity=intensity,
                position=(pos_x, pos_y, pos_z),
                scale=scale * intensity,  # Scale with intensity
            )
            commands.append(cmd)
        
        return commands
    
    def generate_all_cues(self, coordinator: AttractionCoordinator) -> Dict[str, List[DistantCueCommand]]:
        """Generate cues for all regions."""
        return {
            region_id: self.generate_cues(manager)
            for region_id, manager in coordinator.regions.items()
        }
