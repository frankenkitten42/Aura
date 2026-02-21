"""
VDE Phase 5: Environmental Wear System

The ground tells a story. Crowded areas look used.

This module handles:
- Multi-layer wear accumulation (displacement, discoloration, damage)
- Asymmetric accumulation/recovery rates
- Per-surface-type wear behavior
- Spatial wear distribution (paths, gathering points)
- UE5-ready decal and shader parameters

Key insight: Environmental wear provides persistent visual evidence of
past crowding. Even after people leave, the trampled grass and worn
paths tell the story of what happened here.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import math


# =============================================================================
# Enums and Constants
# =============================================================================

class WearLayer(Enum):
    """Layers of environmental wear, from immediate to persistent."""
    DISPLACEMENT = "displacement"   # Immediate: footprints, trampled grass
    DISCOLORATION = "discoloration" # Medium: browning, mud, paths
    DAMAGE = "damage"               # Slow: dead patches, compaction, erosion


class SurfaceType(Enum):
    """Types of surfaces with different wear characteristics."""
    GRASS = "grass"                 # Most visible wear
    DIRT = "dirt"                   # Shows paths well
    STONE = "stone"                 # Minimal wear, shows dust
    WOOD = "wood"                   # Shows scuffs, wear patterns
    SAND = "sand"                   # Very visible but recovers fast
    SNOW = "snow"                   # Extremely visible, slow recovery
    MUD = "mud"                     # Already worn, shows deep tracks
    GRAVEL = "gravel"               # Shows displacement
    WATER_EDGE = "water_edge"       # Muddy banks, disturbed


class WearType(Enum):
    """Specific types of wear effects."""
    # Layer 1: Displacement
    FOOTPRINTS = "footprints"
    TRAMPLED_GRASS = "trampled_grass"
    DISTURBED_DIRT = "disturbed_dirt"
    DISPLACED_GRAVEL = "displaced_gravel"
    SNOW_TRACKS = "snow_tracks"
    
    # Layer 2: Discoloration
    GRASS_BROWNING = "grass_browning"
    MUD_ACCUMULATION = "mud_accumulation"
    WORN_PATH = "worn_path"
    DUST_LAYER = "dust_layer"
    WATER_MUDDYING = "water_muddying"
    
    # Layer 3: Damage
    DEAD_PATCHES = "dead_patches"
    COMPACTED_SOIL = "compacted_soil"
    EROSION = "erosion"
    ROOT_EXPOSURE = "root_exposure"
    PUDDLE_FORMATION = "puddle_formation"


# Mapping of wear types to layers
WEAR_LAYER_MAP: Dict[WearType, WearLayer] = {
    # Displacement
    WearType.FOOTPRINTS: WearLayer.DISPLACEMENT,
    WearType.TRAMPLED_GRASS: WearLayer.DISPLACEMENT,
    WearType.DISTURBED_DIRT: WearLayer.DISPLACEMENT,
    WearType.DISPLACED_GRAVEL: WearLayer.DISPLACEMENT,
    WearType.SNOW_TRACKS: WearLayer.DISPLACEMENT,
    # Discoloration
    WearType.GRASS_BROWNING: WearLayer.DISCOLORATION,
    WearType.MUD_ACCUMULATION: WearLayer.DISCOLORATION,
    WearType.WORN_PATH: WearLayer.DISCOLORATION,
    WearType.DUST_LAYER: WearLayer.DISCOLORATION,
    WearType.WATER_MUDDYING: WearLayer.DISCOLORATION,
    # Damage
    WearType.DEAD_PATCHES: WearLayer.DAMAGE,
    WearType.COMPACTED_SOIL: WearLayer.DAMAGE,
    WearType.EROSION: WearLayer.DAMAGE,
    WearType.ROOT_EXPOSURE: WearLayer.DAMAGE,
    WearType.PUDDLE_FORMATION: WearLayer.DAMAGE,
}

# Which wear types apply to which surfaces
SURFACE_WEAR_MAP: Dict[SurfaceType, List[WearType]] = {
    SurfaceType.GRASS: [
        WearType.FOOTPRINTS, WearType.TRAMPLED_GRASS,
        WearType.GRASS_BROWNING, WearType.WORN_PATH,
        WearType.DEAD_PATCHES, WearType.COMPACTED_SOIL,
    ],
    SurfaceType.DIRT: [
        WearType.FOOTPRINTS, WearType.DISTURBED_DIRT,
        WearType.MUD_ACCUMULATION, WearType.WORN_PATH, WearType.DUST_LAYER,
        WearType.COMPACTED_SOIL, WearType.EROSION,
    ],
    SurfaceType.STONE: [
        WearType.DUST_LAYER,
    ],
    SurfaceType.WOOD: [
        WearType.DUST_LAYER, WearType.WORN_PATH,
    ],
    SurfaceType.SAND: [
        WearType.FOOTPRINTS, WearType.DISTURBED_DIRT,
        WearType.WORN_PATH,
    ],
    SurfaceType.SNOW: [
        WearType.SNOW_TRACKS, WearType.FOOTPRINTS,
        WearType.COMPACTED_SOIL,
    ],
    SurfaceType.MUD: [
        WearType.FOOTPRINTS, WearType.MUD_ACCUMULATION,
        WearType.PUDDLE_FORMATION,
    ],
    SurfaceType.GRAVEL: [
        WearType.DISPLACED_GRAVEL, WearType.WORN_PATH,
        WearType.DUST_LAYER,
    ],
    SurfaceType.WATER_EDGE: [
        WearType.MUD_ACCUMULATION, WearType.WATER_MUDDYING,
        WearType.EROSION,
    ],
}


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class WearConfig:
    """Configuration for environmental wear system."""
    
    # Population threshold to start accumulating wear
    wear_start_threshold: float = 0.25
    
    # Accumulation rates per layer (per second at 100% population)
    accumulation_rates: Dict[WearLayer, float] = field(default_factory=lambda: {
        WearLayer.DISPLACEMENT: 0.08,    # Fast accumulation
        WearLayer.DISCOLORATION: 0.02,   # Medium accumulation
        WearLayer.DAMAGE: 0.005,         # Slow accumulation
    })
    
    # Recovery rates per layer (per second at 0% population)
    recovery_rates: Dict[WearLayer, float] = field(default_factory=lambda: {
        WearLayer.DISPLACEMENT: 0.0083,   # ~2 minutes to full recovery
        WearLayer.DISCOLORATION: 0.0011,  # ~15 minutes
        WearLayer.DAMAGE: 0.00055,        # ~30 minutes
    })
    
    # Population threshold for recovery to begin
    recovery_threshold: float = 0.20
    
    # Maximum wear values per layer
    max_wear: Dict[WearLayer, float] = field(default_factory=lambda: {
        WearLayer.DISPLACEMENT: 1.0,
        WearLayer.DISCOLORATION: 1.0,
        WearLayer.DAMAGE: 1.0,
    })
    
    # Layer cascade - higher layers contribute to lower layers
    cascade_rates: Dict[Tuple[WearLayer, WearLayer], float] = field(
        default_factory=lambda: {
            (WearLayer.DISPLACEMENT, WearLayer.DISCOLORATION): 0.3,
            (WearLayer.DISCOLORATION, WearLayer.DAMAGE): 0.2,
        }
    )
    
    # Surface-specific multipliers
    surface_multipliers: Dict[SurfaceType, float] = field(default_factory=lambda: {
        SurfaceType.GRASS: 1.0,
        SurfaceType.DIRT: 0.8,
        SurfaceType.STONE: 0.2,
        SurfaceType.WOOD: 0.5,
        SurfaceType.SAND: 1.2,      # Visible but recovers fast
        SurfaceType.SNOW: 1.5,      # Very visible
        SurfaceType.MUD: 0.6,       # Already worn
        SurfaceType.GRAVEL: 0.7,
        SurfaceType.WATER_EDGE: 1.1,
    })
    
    # Surface-specific recovery multipliers
    surface_recovery_multipliers: Dict[SurfaceType, float] = field(default_factory=lambda: {
        SurfaceType.GRASS: 1.0,
        SurfaceType.DIRT: 0.8,
        SurfaceType.STONE: 2.0,     # Easy to clean
        SurfaceType.WOOD: 1.5,
        SurfaceType.SAND: 2.0,      # Wind helps
        SurfaceType.SNOW: 0.3,      # Slow recovery
        SurfaceType.MUD: 0.5,
        SurfaceType.GRAVEL: 1.2,
        SurfaceType.WATER_EDGE: 0.7,
    })


# =============================================================================
# Wear State Tracking
# =============================================================================

@dataclass
class LayerState:
    """State tracking for a single wear layer."""
    layer: WearLayer
    value: float = 0.0
    target_value: float = 0.0
    accumulation_rate: float = 0.0
    recovery_rate: float = 0.0
    is_accumulating: bool = False
    is_recovering: bool = False
    time_at_current: float = 0.0


@dataclass
class SurfaceState:
    """State tracking for a surface area."""
    surface_type: SurfaceType
    layers: Dict[WearLayer, LayerState] = field(default_factory=dict)
    
    # Active wear effects
    active_effects: Dict[WearType, float] = field(default_factory=dict)
    
    # Aggregate values
    total_wear: float = 0.0
    visual_wear: float = 0.0  # What the player sees (weighted)
    
    def __post_init__(self):
        """Initialize layers if not provided."""
        if not self.layers:
            for layer in WearLayer:
                self.layers[layer] = LayerState(layer=layer)


@dataclass
class WearSnapshot:
    """Snapshot of environmental wear state."""
    population: float = 0.0
    
    # Per-layer global values
    layer_values: Dict[WearLayer, float] = field(default_factory=dict)
    
    # Per-surface states (if tracking multiple surfaces)
    surface_states: Dict[str, SurfaceState] = field(default_factory=dict)
    
    # Active effects
    active_effects: Dict[WearType, float] = field(default_factory=dict)
    
    # Aggregates
    total_wear: float = 0.0
    is_accumulating: bool = False
    is_recovering: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'population': self.population,
            'layer_values': {k.value: v for k, v in self.layer_values.items()},
            'active_effects': {k.value: v for k, v in self.active_effects.items()},
            'total_wear': self.total_wear,
            'is_accumulating': self.is_accumulating,
            'is_recovering': self.is_recovering,
        }


# =============================================================================
# Wear Manager
# =============================================================================

class WearManager:
    """
    Manages environmental wear for a region.
    
    Tracks wear accumulation across multiple layers and surfaces,
    handles recovery timing, and generates UE5-ready parameters.
    
    Example:
        >>> manager = WearManager(surface_type=SurfaceType.GRASS)
        >>> manager.set_population(0.70)
        >>> 
        >>> # Update each tick
        >>> snapshot = manager.update(delta_time=0.5)
        >>> 
        >>> # Get UE5 parameters
        >>> params = manager.get_ue5_parameters()
    """
    
    def __init__(self, 
                 surface_type: SurfaceType = SurfaceType.GRASS,
                 config: Optional[WearConfig] = None):
        """
        Initialize wear manager.
        
        Args:
            surface_type: Primary surface type for this region
            config: Wear configuration
        """
        self.config = config or WearConfig()
        self.surface_type = surface_type
        
        # Initialize surface state
        self.surface = SurfaceState(surface_type=surface_type)
        
        # Get applicable wear types for this surface
        self.applicable_wear = SURFACE_WEAR_MAP.get(surface_type, [])
        
        # Initialize active effects
        for wear_type in self.applicable_wear:
            self.surface.active_effects[wear_type] = 0.0
        
        # Global state
        self._population = 0.0
        self._time = 0.0
    
    def set_population(self, population: float) -> None:
        """Set current population ratio (0.0 to 1.0)."""
        self._population = max(0.0, min(1.0, population))
    
    def update(self, delta_time: float) -> WearSnapshot:
        """
        Update wear state for one tick.
        
        Args:
            delta_time: Time since last update in seconds
            
        Returns:
            Current wear snapshot
        """
        self._time += delta_time
        cfg = self.config
        
        # Get surface multipliers
        surf_mult = cfg.surface_multipliers.get(self.surface_type, 1.0)
        surf_recovery_mult = cfg.surface_recovery_multipliers.get(self.surface_type, 1.0)
        
        # Update each layer
        for layer in WearLayer:
            layer_state = self.surface.layers[layer]
            
            # Determine if accumulating or recovering
            if self._population >= cfg.wear_start_threshold:
                # Accumulating
                layer_state.is_accumulating = True
                layer_state.is_recovering = False
                
                # Calculate accumulation amount
                base_rate = cfg.accumulation_rates.get(layer, 0.01)
                pop_factor = (self._population - cfg.wear_start_threshold) / (1.0 - cfg.wear_start_threshold)
                accum = base_rate * pop_factor * surf_mult * delta_time
                
                layer_state.value = min(
                    cfg.max_wear.get(layer, 1.0),
                    layer_state.value + accum
                )
                
            elif self._population <= cfg.recovery_threshold:
                # Recovering
                layer_state.is_accumulating = False
                layer_state.is_recovering = True
                
                # Calculate recovery amount
                base_rate = cfg.recovery_rates.get(layer, 0.001)
                recovery_factor = 1.0 - (self._population / cfg.recovery_threshold)
                recovery = base_rate * recovery_factor * surf_recovery_mult * delta_time
                
                layer_state.value = max(0.0, layer_state.value - recovery)
                
            else:
                # In between - no change
                layer_state.is_accumulating = False
                layer_state.is_recovering = False
            
            layer_state.time_at_current += delta_time
        
        # Apply layer cascade (higher layers contribute to lower)
        for (from_layer, to_layer), cascade_rate in cfg.cascade_rates.items():
            from_state = self.surface.layers[from_layer]
            to_state = self.surface.layers[to_layer]
            
            if from_state.value > 0.5:  # Only cascade when significant
                cascade_amount = from_state.value * cascade_rate * delta_time * 0.1
                to_state.value = min(
                    cfg.max_wear.get(to_layer, 1.0),
                    to_state.value + cascade_amount
                )
        
        # Update active effects based on layer values
        self._update_active_effects()
        
        # Calculate aggregates
        self._calculate_aggregates()
        
        return self._create_snapshot()
    
    def _update_active_effects(self) -> None:
        """Update individual wear effects based on layer values."""
        for wear_type in self.applicable_wear:
            layer = WEAR_LAYER_MAP.get(wear_type, WearLayer.DISPLACEMENT)
            layer_value = self.surface.layers[layer].value
            
            # Effect strength is based on layer value
            self.surface.active_effects[wear_type] = layer_value
    
    def _calculate_aggregates(self) -> None:
        """Calculate aggregate wear values."""
        # Total wear is weighted sum of layers
        weights = {
            WearLayer.DISPLACEMENT: 0.3,
            WearLayer.DISCOLORATION: 0.4,
            WearLayer.DAMAGE: 0.3,
        }
        
        self.surface.total_wear = sum(
            self.surface.layers[layer].value * weight
            for layer, weight in weights.items()
        )
        
        # Visual wear emphasizes displacement (most immediately visible)
        visual_weights = {
            WearLayer.DISPLACEMENT: 0.5,
            WearLayer.DISCOLORATION: 0.35,
            WearLayer.DAMAGE: 0.15,
        }
        
        self.surface.visual_wear = sum(
            self.surface.layers[layer].value * weight
            for layer, weight in visual_weights.items()
        )
    
    def _create_snapshot(self) -> WearSnapshot:
        """Create a snapshot of current wear state."""
        snapshot = WearSnapshot()
        snapshot.population = self._population
        
        # Layer values
        for layer in WearLayer:
            snapshot.layer_values[layer] = self.surface.layers[layer].value
        
        # Active effects
        snapshot.active_effects = dict(self.surface.active_effects)
        
        # Aggregates
        snapshot.total_wear = self.surface.total_wear
        snapshot.is_accumulating = any(
            self.surface.layers[l].is_accumulating for l in WearLayer
        )
        snapshot.is_recovering = any(
            self.surface.layers[l].is_recovering for l in WearLayer
        )
        
        return snapshot
    
    def get_ue5_parameters(self) -> 'FWearParameters':
        """Generate UE5-ready wear parameters."""
        return FWearParameters.from_manager(self)
    
    def reset(self) -> None:
        """Reset all wear to zero."""
        for layer in WearLayer:
            state = self.surface.layers[layer]
            state.value = 0.0
            state.target_value = 0.0
            state.is_accumulating = False
            state.is_recovering = False
            state.time_at_current = 0.0
        
        for wear_type in self.surface.active_effects:
            self.surface.active_effects[wear_type] = 0.0
        
        self.surface.total_wear = 0.0
        self.surface.visual_wear = 0.0
        self._population = 0.0
        self._time = 0.0
    
    @property
    def total_wear(self) -> float:
        """Total accumulated wear."""
        return self.surface.total_wear
    
    @property
    def visual_wear(self) -> float:
        """Visual wear (weighted for player perception)."""
        return self.surface.visual_wear
    
    @property
    def population(self) -> float:
        """Current population."""
        return self._population


# =============================================================================
# UE5 Parameters
# =============================================================================

@dataclass
class FWearParameters:
    """UE5-ready environmental wear parameters."""
    
    # Layer intensities (0-1)
    displacement_intensity: float = 0.0
    discoloration_intensity: float = 0.0
    damage_intensity: float = 0.0
    
    # Decal parameters
    footprint_density: float = 0.0          # Footprints per sq meter
    footprint_opacity: float = 0.0          # 0-1
    path_blend_amount: float = 0.0          # Worn path visibility
    
    # Grass parameters (shader-driven)
    grass_height_multiplier: float = 1.0    # 1 = full, 0 = flat
    grass_bend_amount: float = 0.0          # 0-1, how bent over
    grass_color_shift: float = 0.0          # 0 = green, 1 = brown
    grass_density_multiplier: float = 1.0   # Spawn density
    
    # Ground parameters
    ground_displacement: float = 0.0        # Height offset
    ground_roughness_mod: float = 0.0       # Roughness increase
    ground_color_darkening: float = 0.0     # Mud/dirt tint
    ground_wetness: float = 0.0             # Puddle formation
    
    # Dust/debris
    dust_accumulation: float = 0.0          # Dust layer thickness
    debris_density: float = 0.0             # Leaves, twigs
    
    # Erosion
    erosion_depth: float = 0.0              # Erosion channel depth
    compaction_amount: float = 0.0          # Soil compaction
    
    def to_ue5_json(self) -> Dict[str, float]:
        """Export as JSON for UE5."""
        return {
            'Wear_DisplacementIntensity': self.displacement_intensity,
            'Wear_DiscolorationIntensity': self.discoloration_intensity,
            'Wear_DamageIntensity': self.damage_intensity,
            'Decal_FootprintDensity': self.footprint_density,
            'Decal_FootprintOpacity': self.footprint_opacity,
            'Decal_PathBlendAmount': self.path_blend_amount,
            'Grass_HeightMultiplier': self.grass_height_multiplier,
            'Grass_BendAmount': self.grass_bend_amount,
            'Grass_ColorShift': self.grass_color_shift,
            'Grass_DensityMultiplier': self.grass_density_multiplier,
            'Ground_Displacement': self.ground_displacement,
            'Ground_RoughnessMod': self.ground_roughness_mod,
            'Ground_ColorDarkening': self.ground_color_darkening,
            'Ground_Wetness': self.ground_wetness,
            'Dust_Accumulation': self.dust_accumulation,
            'Debris_Density': self.debris_density,
            'Erosion_Depth': self.erosion_depth,
            'Compaction_Amount': self.compaction_amount,
        }
    
    @classmethod
    def from_manager(cls, manager: WearManager) -> 'FWearParameters':
        """Create parameters from wear manager state."""
        params = cls()
        surface = manager.surface
        
        # Layer intensities
        params.displacement_intensity = surface.layers[WearLayer.DISPLACEMENT].value
        params.discoloration_intensity = surface.layers[WearLayer.DISCOLORATION].value
        params.damage_intensity = surface.layers[WearLayer.DAMAGE].value
        
        # Footprints (from displacement)
        disp = params.displacement_intensity
        params.footprint_density = disp * 5.0  # 0-5 per sq meter
        params.footprint_opacity = min(1.0, disp * 1.2)
        
        # Path wear (from discoloration)
        disc = params.discoloration_intensity
        params.path_blend_amount = disc
        
        # Grass parameters (primarily for grass surface)
        if manager.surface_type == SurfaceType.GRASS:
            params.grass_height_multiplier = 1.0 - disp * 0.7
            params.grass_bend_amount = disp
            params.grass_color_shift = disc * 0.8
            params.grass_density_multiplier = 1.0 - params.damage_intensity * 0.5
        
        # Ground parameters
        params.ground_displacement = -disp * 0.05  # Negative = pushed down
        params.ground_roughness_mod = disc * 0.3
        params.ground_color_darkening = disc * 0.4
        params.ground_wetness = params.damage_intensity * 0.3
        
        # Dust/debris
        params.dust_accumulation = disc * 0.5
        params.debris_density = disp * 0.3
        
        # Erosion (from damage)
        dmg = params.damage_intensity
        params.erosion_depth = dmg * 0.1
        params.compaction_amount = dmg * 0.8
        
        return params


# =============================================================================
# Multi-Zone Wear Tracking
# =============================================================================

@dataclass
class WearZone:
    """A zone within a region with its own wear characteristics."""
    zone_id: str
    surface_type: SurfaceType
    manager: WearManager = field(default=None)
    
    # Zone properties
    position: Tuple[float, float] = (0.0, 0.0)
    radius: float = 500.0  # cm
    population_weight: float = 1.0  # How much of region pop affects this zone
    
    # Traffic patterns
    is_path: bool = False
    is_gathering_point: bool = False
    
    def __post_init__(self):
        if self.manager is None:
            self.manager = WearManager(surface_type=self.surface_type)


class RegionWearManager:
    """
    Manages wear across multiple zones in a region.
    
    Handles spatial distribution of wear, path formation, and
    gathering point effects.
    
    Example:
        >>> region = RegionWearManager("marketplace")
        >>> region.add_zone("center", SurfaceType.STONE, is_gathering_point=True)
        >>> region.add_zone("grass_edge", SurfaceType.GRASS)
        >>> region.add_zone("main_path", SurfaceType.DIRT, is_path=True)
        >>> 
        >>> region.set_population(0.65)
        >>> snapshot = region.update(delta_time=0.5)
    """
    
    def __init__(self, region_id: str, config: Optional[WearConfig] = None):
        """
        Initialize region wear manager.
        
        Args:
            region_id: Unique identifier for the region
            config: Wear configuration (shared across zones)
        """
        self.region_id = region_id
        self.config = config or WearConfig()
        self.zones: Dict[str, WearZone] = {}
        
        self._population = 0.0
        self._time = 0.0
    
    def add_zone(self, zone_id: str, surface_type: SurfaceType,
                 position: Tuple[float, float] = (0.0, 0.0),
                 radius: float = 500.0,
                 population_weight: float = 1.0,
                 is_path: bool = False,
                 is_gathering_point: bool = False) -> None:
        """Add a wear zone to the region."""
        zone = WearZone(
            zone_id=zone_id,
            surface_type=surface_type,
            manager=WearManager(surface_type=surface_type, config=self.config),
            position=position,
            radius=radius,
            population_weight=population_weight,
            is_path=is_path,
            is_gathering_point=is_gathering_point,
        )
        self.zones[zone_id] = zone
    
    def set_population(self, population: float) -> None:
        """Set overall region population."""
        self._population = max(0.0, min(1.0, population))
    
    def update(self, delta_time: float) -> Dict[str, WearSnapshot]:
        """Update all zones."""
        self._time += delta_time
        snapshots = {}
        
        for zone_id, zone in self.zones.items():
            # Calculate zone-specific population
            zone_pop = self._calculate_zone_population(zone)
            zone.manager.set_population(zone_pop)
            
            # Update zone
            snapshots[zone_id] = zone.manager.update(delta_time)
        
        return snapshots
    
    def _calculate_zone_population(self, zone: WearZone) -> float:
        """Calculate effective population for a zone."""
        base_pop = self._population * zone.population_weight
        
        # Paths get more wear
        if zone.is_path:
            base_pop = min(1.0, base_pop * 1.3)
        
        # Gathering points get concentrated wear
        if zone.is_gathering_point:
            base_pop = min(1.0, base_pop * 1.5)
        
        return base_pop
    
    def get_zone_parameters(self, zone_id: str) -> Optional[FWearParameters]:
        """Get UE5 parameters for a specific zone."""
        if zone_id in self.zones:
            return self.zones[zone_id].manager.get_ue5_parameters()
        return None
    
    def get_all_parameters(self) -> Dict[str, FWearParameters]:
        """Get UE5 parameters for all zones."""
        return {
            zone_id: zone.manager.get_ue5_parameters()
            for zone_id, zone in self.zones.items()
        }
    
    def get_aggregate_wear(self) -> float:
        """Get average wear across all zones."""
        if not self.zones:
            return 0.0
        return sum(z.manager.total_wear for z in self.zones.values()) / len(self.zones)
    
    def reset(self) -> None:
        """Reset all zones."""
        for zone in self.zones.values():
            zone.manager.reset()
        self._population = 0.0
        self._time = 0.0
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Generate complete UE5 JSON payload."""
        return {
            'RegionID': self.region_id,
            'Population': self._population,
            'AggregateWear': self.get_aggregate_wear(),
            'Zones': {
                zone_id: {
                    'SurfaceType': zone.surface_type.value,
                    'IsPath': zone.is_path,
                    'IsGatheringPoint': zone.is_gathering_point,
                    'Parameters': zone.manager.get_ue5_parameters().to_ue5_json(),
                }
                for zone_id, zone in self.zones.items()
            },
        }
