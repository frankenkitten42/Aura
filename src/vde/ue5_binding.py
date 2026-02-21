"""
VDE Phase 2: UE5 Integration

Provides the binding layer between VDE calculations and Unreal Engine 5:
- Post-process parameter binding
- Material Parameter Collection (MPC) integration
- Niagara particle system parameters
- Region-based parameter blending
- Blueprint-friendly data structures

This module generates UE5-compatible data structures and provides
serialization for communication with UE5 via JSON or direct binding.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import math

from .vdi_calculator import VDIResult, VisualPhase, WildlifeState
from .output_params import (
    VDEOutputState, PostProcessParams, MaterialParams,
    SpawnParams, ParticleParams, MotionParams, AttractionParams
)


# =============================================================================
# UE5 Data Structures (mirrors C++ structs)
# =============================================================================

@dataclass
class FVDEPostProcessSettings:
    """
    Post-process settings for UE5 Post Process Volume.
    
    Maps to UE5's FPostProcessSettings with VDE-specific modifications.
    All values are deltas/multipliers applied to base settings.
    """
    # Bloom
    bloom_intensity_multiplier: float = 1.0      # Multiply base bloom
    bloom_threshold_bias: float = 0.0            # Lower threshold = more bloom
    
    # Color Grading
    saturation_multiplier: float = 1.0           # 0.95-1.0 for subtle effect
    contrast_multiplier: float = 1.0             # Reduce for flat look
    color_temp_offset: float = 0.0               # Kelvin shift
    
    # Shadows
    shadow_amount_multiplier: float = 1.0        # Reduce for softer shadows
    
    # Fog/Haze
    fog_density_multiplier: float = 1.0          # Increase for haze
    fog_height_falloff_multiplier: float = 1.0   # Affects vertical distribution
    
    # Vignette
    vignette_intensity: float = 0.0              # 0.0-0.4 range
    
    # Depth of Field (subtle)
    dof_focal_distance_bias: float = 0.0         # Shift focus slightly
    
    def to_ue5_json(self) -> Dict[str, float]:
        """Export as JSON for UE5 consumption."""
        return {
            'BloomIntensityMultiplier': self.bloom_intensity_multiplier,
            'BloomThresholdBias': self.bloom_threshold_bias,
            'SaturationMultiplier': self.saturation_multiplier,
            'ContrastMultiplier': self.contrast_multiplier,
            'ColorTempOffset': self.color_temp_offset,
            'ShadowAmountMultiplier': self.shadow_amount_multiplier,
            'FogDensityMultiplier': self.fog_density_multiplier,
            'FogHeightFalloffMultiplier': self.fog_height_falloff_multiplier,
            'VignetteIntensity': self.vignette_intensity,
            'DOFFocalDistanceBias': self.dof_focal_distance_bias,
        }


@dataclass
class FVDEMaterialParameters:
    """
    Material Parameter Collection values for VDE.
    
    These drive material instances across the scene:
    - Foliage materials (wind response, color)
    - Water materials (clarity, turbulence)
    - Ground materials (wear, displacement)
    - Cloth materials (settle behavior)
    """
    # Foliage
    foliage_wind_intensity: float = 1.0          # Base wind strength
    foliage_wind_turbulence: float = 0.0         # Random variation
    foliage_phase_offset_range: float = 0.0      # Animation desync
    foliage_color_desaturation: float = 0.0      # Subtle color shift
    
    # Water
    water_clarity: float = 1.0                   # 1.0 = clear, 0.0 = murky
    water_turbulence: float = 0.0                # Surface agitation
    water_color_tint: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    
    # Ground
    ground_wear_intensity: float = 0.0           # Decal/blend strength
    ground_displacement_reduction: float = 0.0   # Flatten grass
    ground_color_darkening: float = 0.0          # Mud/dirt tint
    
    # Cloth
    cloth_damping_multiplier: float = 1.0        # How fast cloth settles
    cloth_wind_response: float = 1.0             # Reactivity to wind
    
    # Props
    prop_jitter_intensity: float = 0.0           # Micro-movement
    prop_jitter_frequency: float = 0.0           # Speed of jitter
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export as JSON for Material Parameter Collection."""
        return {
            'Foliage_WindIntensity': self.foliage_wind_intensity,
            'Foliage_WindTurbulence': self.foliage_wind_turbulence,
            'Foliage_PhaseOffsetRange': self.foliage_phase_offset_range,
            'Foliage_ColorDesaturation': self.foliage_color_desaturation,
            'Water_Clarity': self.water_clarity,
            'Water_Turbulence': self.water_turbulence,
            'Water_ColorTint': list(self.water_color_tint),
            'Ground_WearIntensity': self.ground_wear_intensity,
            'Ground_DisplacementReduction': self.ground_displacement_reduction,
            'Ground_ColorDarkening': self.ground_color_darkening,
            'Cloth_DampingMultiplier': self.cloth_damping_multiplier,
            'Cloth_WindResponse': self.cloth_wind_response,
            'Prop_JitterIntensity': self.prop_jitter_intensity,
            'Prop_JitterFrequency': self.prop_jitter_frequency,
        }


@dataclass
class FVDENiagaraParameters:
    """
    Niagara particle system parameters.
    
    Controls ambient particle effects:
    - Dust/debris systems
    - Pollen/organic particles
    - Insect swarms
    - Environmental effects
    """
    # Dust System
    dust_spawn_rate: float = 0.0                 # Particles per second
    dust_lifetime: float = 3.0                   # Seconds
    dust_size_range: Tuple[float, float] = (0.5, 2.0)
    dust_velocity_scale: float = 1.0
    dust_color_tint: Tuple[float, float, float, float] = (0.8, 0.75, 0.7, 0.3)
    
    # Pollen System
    pollen_spawn_rate: float = 0.0
    pollen_drift_speed: float = 0.5
    pollen_size: float = 0.3
    
    # Debris System
    debris_spawn_rate: float = 0.0
    debris_fall_speed: float = 1.0
    debris_rotation_speed: float = 1.0
    
    # Global Coherence
    wind_direction: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    wind_direction_variance: float = 0.0         # 0 = unified, 1 = chaotic
    global_velocity_scale: float = 1.0
    
    # Insect System
    insect_density: float = 1.0
    insect_activity_level: float = 1.0           # Flight pattern intensity
    insect_avoidance_radius: float = 100.0       # Player avoidance
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export as JSON for Niagara systems."""
        return {
            'Dust_SpawnRate': self.dust_spawn_rate,
            'Dust_Lifetime': self.dust_lifetime,
            'Dust_SizeMin': self.dust_size_range[0],
            'Dust_SizeMax': self.dust_size_range[1],
            'Dust_VelocityScale': self.dust_velocity_scale,
            'Dust_ColorTint': list(self.dust_color_tint),
            'Pollen_SpawnRate': self.pollen_spawn_rate,
            'Pollen_DriftSpeed': self.pollen_drift_speed,
            'Pollen_Size': self.pollen_size,
            'Debris_SpawnRate': self.debris_spawn_rate,
            'Debris_FallSpeed': self.debris_fall_speed,
            'Debris_RotationSpeed': self.debris_rotation_speed,
            'Wind_Direction': list(self.wind_direction),
            'Wind_DirectionVariance': self.wind_direction_variance,
            'Global_VelocityScale': self.global_velocity_scale,
            'Insect_Density': self.insect_density,
            'Insect_ActivityLevel': self.insect_activity_level,
            'Insect_AvoidanceRadius': self.insect_avoidance_radius,
        }


@dataclass
class FVDESpawnSettings:
    """
    Spawn manager settings for wildlife and NPCs.
    
    Controls what spawns and how it behaves.
    """
    # Wildlife
    wildlife_spawn_multiplier: float = 1.0
    wildlife_behavior_state: str = "thriving"    # thriving/wary/retreating/absent
    bird_landing_probability: float = 1.0
    bird_flee_distance: float = 300.0            # Cm from player
    ambient_creature_density: float = 1.0
    
    # NPCs
    npc_idle_behavior_mask: int = 0xFFFFFFFF     # Bitmask of allowed idles
    npc_comfort_level: float = 1.0               # Affects behavior selection
    npc_reposition_frequency: float = 0.0        # How often they shift
    npc_interaction_radius: float = 200.0        # Engagement distance
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export as JSON for spawn managers."""
        return {
            'Wildlife_SpawnMultiplier': self.wildlife_spawn_multiplier,
            'Wildlife_BehaviorState': self.wildlife_behavior_state,
            'Bird_LandingProbability': self.bird_landing_probability,
            'Bird_FleeDistance': self.bird_flee_distance,
            'AmbientCreature_Density': self.ambient_creature_density,
            'NPC_IdleBehaviorMask': self.npc_idle_behavior_mask,
            'NPC_ComfortLevel': self.npc_comfort_level,
            'NPC_RepositionFrequency': self.npc_reposition_frequency,
            'NPC_InteractionRadius': self.npc_interaction_radius,
        }


@dataclass
class FVDEAttractionSettings:
    """
    Attraction system settings for low-population areas.
    
    Applied to regions that should draw players away from crowded areas.
    """
    is_active: bool = False
    attraction_strength: float = 0.0             # 0-1 intensity
    
    # Light modifications
    light_color_warmth: float = 0.0              # Kelvin boost
    god_ray_intensity: float = 0.0               # Volumetric light
    ambient_light_boost: float = 0.0             # Fill light increase
    
    # Visual clarity
    fog_reduction: float = 0.0                   # Clearer air
    contrast_boost: float = 0.0                  # Sharper visuals
    saturation_boost: float = 0.0                # More vibrant
    
    # Life signals
    wildlife_spawn_bonus: float = 0.0
    distant_activity_spawns: int = 0             # NPCs/animals visible at distance
    ambient_sound_bonus: float = 0.0             # Pleasant sounds
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export as JSON for attraction system."""
        return {
            'IsActive': self.is_active,
            'AttractionStrength': self.attraction_strength,
            'Light_ColorWarmth': self.light_color_warmth,
            'Light_GodRayIntensity': self.god_ray_intensity,
            'Light_AmbientBoost': self.ambient_light_boost,
            'Visual_FogReduction': self.fog_reduction,
            'Visual_ContrastBoost': self.contrast_boost,
            'Visual_SaturationBoost': self.saturation_boost,
            'Life_WildlifeBonus': self.wildlife_spawn_bonus,
            'Life_DistantActivitySpawns': self.distant_activity_spawns,
            'Life_AmbientSoundBonus': self.ambient_sound_bonus,
        }


@dataclass
class FVDERegionState:
    """
    Complete VDE state for a single region.
    
    This is the main data structure passed to UE5.
    """
    region_id: str = "default"
    
    # Core state
    population: float = 0.0
    vdi: float = 0.0
    phase: str = "pristine"
    wildlife_state: str = "thriving"
    accumulated_wear: float = 0.0
    
    # UE5 parameters
    post_process: FVDEPostProcessSettings = field(default_factory=FVDEPostProcessSettings)
    materials: FVDEMaterialParameters = field(default_factory=FVDEMaterialParameters)
    niagara: FVDENiagaraParameters = field(default_factory=FVDENiagaraParameters)
    spawning: FVDESpawnSettings = field(default_factory=FVDESpawnSettings)
    attraction: FVDEAttractionSettings = field(default_factory=FVDEAttractionSettings)
    
    # Timing
    timestamp: float = 0.0
    delta_time: float = 0.0
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export complete state as JSON for UE5."""
        return {
            'RegionID': self.region_id,
            'Population': self.population,
            'VDI': self.vdi,
            'Phase': self.phase,
            'WildlifeState': self.wildlife_state,
            'AccumulatedWear': self.accumulated_wear,
            'PostProcess': self.post_process.to_ue5_json(),
            'Materials': self.materials.to_ue5_json(),
            'Niagara': self.niagara.to_ue5_json(),
            'Spawning': self.spawning.to_ue5_json(),
            'Attraction': self.attraction.to_ue5_json(),
            'Timestamp': self.timestamp,
            'DeltaTime': self.delta_time,
        }
    
    def to_json_string(self, indent: int = None) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_ue5_json(), indent=indent)


# =============================================================================
# UE5 Binding Generator
# =============================================================================

class UE5BindingGenerator:
    """
    Generates UE5-compatible parameter bindings from VDE output.
    
    Converts abstract VDE parameters to concrete UE5 values with
    proper ranges, curves, and mappings.
    
    Example:
        >>> from vde import VDICalculator, OutputGenerator
        >>> from vde.ue5_binding import UE5BindingGenerator
        >>> 
        >>> calc = VDICalculator()
        >>> gen = OutputGenerator()
        >>> ue5 = UE5BindingGenerator()
        >>> 
        >>> result = calc.calculate(population=0.65, delta_time=0.5)
        >>> output = gen.generate(result)
        >>> region_state = ue5.generate_region_state(result, output)
        >>> 
        >>> # Send to UE5
        >>> json_data = region_state.to_json_string()
    """
    
    # Base values (what UE5 uses when VDI = 0)
    BASE_VALUES = {
        'bloom_intensity': 1.0,
        'bloom_threshold': 1.0,
        'contrast': 1.0,
        'saturation': 1.0,
        'shadow_amount': 1.0,
        'fog_density': 1.0,
        'dust_spawn_rate': 5.0,      # Particles/sec baseline
        'pollen_spawn_rate': 2.0,
        'debris_spawn_rate': 1.0,
    }
    
    # Curve parameters for non-linear mappings
    CURVES = {
        'bloom': {'power': 2.0, 'max_delta': 0.5},
        'contrast': {'power': 1.5, 'max_delta': 0.3},
        'fog': {'power': 2.0, 'max_delta': 0.4},
        'dust': {'power': 1.5, 'max_mult': 5.0},
    }
    
    def __init__(self, region_id: str = "default"):
        self.region_id = region_id
        self._timestamp = 0.0
    
    def generate_region_state(self, 
                               vdi_result: VDIResult,
                               output: VDEOutputState,
                               delta_time: float = 0.5) -> FVDERegionState:
        """
        Generate complete UE5 region state from VDE output.
        
        Args:
            vdi_result: Result from VDICalculator
            output: Result from OutputGenerator
            delta_time: Time since last update
            
        Returns:
            FVDERegionState ready for UE5
        """
        self._timestamp += delta_time
        
        state = FVDERegionState()
        state.region_id = self.region_id
        state.timestamp = self._timestamp
        state.delta_time = delta_time
        
        # Core state
        state.population = vdi_result.population
        state.vdi = vdi_result.smoothed_vdi
        state.phase = vdi_result.phase.value
        state.wildlife_state = vdi_result.wildlife_state.value
        state.accumulated_wear = vdi_result.accumulated_wear
        
        # Generate UE5 parameters
        state.post_process = self._generate_post_process(output)
        state.materials = self._generate_materials(output, vdi_result)
        state.niagara = self._generate_niagara(output)
        state.spawning = self._generate_spawning(output, vdi_result)
        state.attraction = self._generate_attraction(output)
        
        return state
    
    def _generate_post_process(self, output: VDEOutputState) -> FVDEPostProcessSettings:
        """Generate post-process settings."""
        pp = FVDEPostProcessSettings()
        src = output.post_process
        
        # Bloom: increase with discomfort
        bloom_factor = self._apply_curve(src.bloom_intensity_mod, 'bloom')
        pp.bloom_intensity_multiplier = 1.0 + bloom_factor
        pp.bloom_threshold_bias = -src.bloom_intensity_mod * 0.3  # Lower threshold
        
        # Color grading
        pp.saturation_multiplier = src.saturation_mod
        pp.contrast_multiplier = 1.0 - src.contrast_reduction
        pp.color_temp_offset = src.color_temp_shift
        
        # Shadows
        pp.shadow_amount_multiplier = 1.0 - src.shadow_softness * 0.5
        
        # Fog/Haze
        fog_factor = self._apply_curve(src.haze_density, 'fog')
        pp.fog_density_multiplier = 1.0 + fog_factor
        pp.fog_height_falloff_multiplier = 1.0 - src.haze_density * 0.2
        
        # Vignette
        pp.vignette_intensity = src.vignette
        
        return pp
    
    def _generate_materials(self, output: VDEOutputState, 
                            vdi_result: VDIResult) -> FVDEMaterialParameters:
        """Generate material parameter collection values."""
        mat = FVDEMaterialParameters()
        src_mat = output.materials
        src_motion = output.motion
        
        # Foliage
        mat.foliage_wind_intensity = 1.0 + src_mat.foliage_restlessness * 0.5
        mat.foliage_wind_turbulence = src_motion.wind_direction_variance
        mat.foliage_phase_offset_range = (1.0 - src_motion.animation_phase_sync) * 2.0
        mat.foliage_color_desaturation = max(0, vdi_result.smoothed_vdi) * 0.1
        
        # Water
        mat.water_clarity = src_mat.water_clarity
        mat.water_turbulence = (1.0 - src_mat.water_clarity) * 0.5
        
        # Tint water slightly brown when murky
        turbidity = 1.0 - src_mat.water_clarity
        mat.water_color_tint = (
            1.0 - turbidity * 0.1,
            1.0 - turbidity * 0.15,
            1.0 - turbidity * 0.2,
        )
        
        # Ground
        mat.ground_wear_intensity = src_mat.ground_wear
        mat.ground_displacement_reduction = src_mat.grass_trampling
        mat.ground_color_darkening = src_mat.ground_wear * 0.3
        
        # Cloth
        mat.cloth_damping_multiplier = 2.0 - src_motion.cloth_rest_achieved
        mat.cloth_wind_response = 1.0 + src_mat.foliage_restlessness * 0.3
        
        # Props
        mat.prop_jitter_intensity = src_mat.prop_jitter
        mat.prop_jitter_frequency = 2.0 + src_mat.prop_jitter * 5.0
        
        return mat
    
    def _generate_niagara(self, output: VDEOutputState) -> FVDENiagaraParameters:
        """Generate Niagara particle parameters."""
        nia = FVDENiagaraParameters()
        src_part = output.particles
        src_motion = output.motion
        src_spawn = output.spawning
        
        # Dust system
        nia.dust_spawn_rate = self.BASE_VALUES['dust_spawn_rate'] * (1.0 + src_part.dust_density * 4.0)
        nia.dust_lifetime = 3.0 + src_part.dust_density * 2.0
        nia.dust_size_range = (0.5 + src_part.dust_density * 0.5, 2.0 + src_part.dust_density * 1.0)
        nia.dust_velocity_scale = 1.0 - src_part.particle_coherence * 0.3
        
        # Dust color: slightly more visible when dense
        alpha = 0.3 + src_part.dust_density * 0.2
        nia.dust_color_tint = (0.8, 0.75, 0.7, alpha)
        
        # Pollen system
        nia.pollen_spawn_rate = self.BASE_VALUES['pollen_spawn_rate'] * (1.0 + src_part.pollen_intensity * 3.0)
        nia.pollen_drift_speed = 0.5 + src_part.pollen_intensity * 0.3
        nia.pollen_size = 0.3 + src_part.pollen_intensity * 0.2
        
        # Debris system
        nia.debris_spawn_rate = self.BASE_VALUES['debris_spawn_rate'] * (1.0 + src_part.debris_frequency * 4.0)
        nia.debris_fall_speed = 1.0 + src_part.debris_frequency * 0.5
        nia.debris_rotation_speed = 1.0 + src_part.debris_frequency * 2.0
        
        # Wind coherence
        nia.wind_direction_variance = src_motion.wind_direction_variance
        nia.global_velocity_scale = 1.0 + (1.0 - src_part.particle_coherence) * 0.5
        
        # Insects
        nia.insect_density = src_spawn.insect_density
        nia.insect_activity_level = 0.5 + src_spawn.insect_density * 0.5
        
        return nia
    
    def _generate_spawning(self, output: VDEOutputState, 
                           vdi_result: VDIResult) -> FVDESpawnSettings:
        """Generate spawn manager settings."""
        spawn = FVDESpawnSettings()
        src = output.spawning
        
        # Wildlife
        spawn.wildlife_spawn_multiplier = src.wildlife_spawn_rate
        spawn.wildlife_behavior_state = src.wildlife_state
        spawn.bird_landing_probability = src.bird_landing_chance
        spawn.ambient_creature_density = src.ambient_creature_rate
        
        # Adjust flee distance based on state
        flee_distances = {
            'thriving': 300.0,
            'wary': 500.0,
            'retreating': 800.0,
            'absent': 1500.0,
        }
        spawn.bird_flee_distance = flee_distances.get(src.wildlife_state, 500.0)
        
        # NPCs
        spawn.npc_comfort_level = src.npc_comfort_level
        spawn.npc_reposition_frequency = src.npc_reposition_rate
        
        # Calculate idle behavior mask
        # Bits: 0=stand, 1=sit, 2=lean, 3=stretch, 4=look_around, 5=chat, 6=eat, 7=sleep
        if src.npc_idle_variety >= 0.9:
            spawn.npc_idle_behavior_mask = 0xFF  # All behaviors
        elif src.npc_idle_variety >= 0.7:
            spawn.npc_idle_behavior_mask = 0x3F  # No eat/sleep
        elif src.npc_idle_variety >= 0.5:
            spawn.npc_idle_behavior_mask = 0x1F  # Stand, sit, lean, stretch, look
        elif src.npc_idle_variety >= 0.3:
            spawn.npc_idle_behavior_mask = 0x07  # Stand, sit, lean only
        else:
            spawn.npc_idle_behavior_mask = 0x01  # Stand only
        
        # Interaction radius shrinks when uncomfortable
        spawn.npc_interaction_radius = 200.0 + src.npc_comfort_level * 100.0
        
        return spawn
    
    def _generate_attraction(self, output: VDEOutputState) -> FVDEAttractionSettings:
        """Generate attraction system settings."""
        attr = FVDEAttractionSettings()
        src = output.attraction
        
        attr.is_active = src.is_attracting
        
        if src.is_attracting:
            # Calculate overall attraction strength
            attr.attraction_strength = (
                src.light_temp_boost / 200.0 +
                src.wildlife_spawn_bonus +
                src.discovery_visibility
            ) / 3.0
            
            # Light modifications
            attr.light_color_warmth = src.light_temp_boost
            attr.god_ray_intensity = src.god_ray_probability
            attr.ambient_light_boost = src.specular_bonus * 2.0
            
            # Visual clarity
            attr.fog_reduction = src.path_visibility_boost
            attr.contrast_boost = src.landmark_clarity * 0.1
            attr.saturation_boost = src.path_visibility_boost * 0.05
            
            # Life signals
            attr.wildlife_spawn_bonus = src.wildlife_spawn_bonus
            attr.distant_activity_spawns = int(src.distant_activity_spawn * 5)
            attr.ambient_sound_bonus = src.ambient_interaction_rate
        
        return attr
    
    def _apply_curve(self, value: float, curve_name: str) -> float:
        """Apply non-linear curve to value."""
        curve = self.CURVES.get(curve_name, {'power': 1.0, 'max_delta': 1.0})
        
        # Apply power curve
        curved = math.pow(value, curve.get('power', 1.0))
        
        # Scale to max
        if 'max_delta' in curve:
            curved *= curve['max_delta']
        elif 'max_mult' in curve:
            curved *= curve['max_mult']
        
        return curved
    
    def reset(self) -> None:
        """Reset the generator."""
        self._timestamp = 0.0


# =============================================================================
# Batch Processing for Multiple Regions
# =============================================================================

@dataclass
class FVDEWorldState:
    """
    Complete VDE state for all regions in the world.
    
    Used for multi-region scenarios with attraction broadcasting.
    """
    regions: Dict[str, FVDERegionState] = field(default_factory=dict)
    timestamp: float = 0.0
    
    # Cross-region data
    attraction_sources: List[str] = field(default_factory=list)
    attraction_targets: Dict[str, List[str]] = field(default_factory=dict)
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export complete world state."""
        return {
            'Regions': {k: v.to_ue5_json() for k, v in self.regions.items()},
            'Timestamp': self.timestamp,
            'AttractionSources': self.attraction_sources,
            'AttractionTargets': self.attraction_targets,
        }
    
    def to_json_string(self, indent: int = None) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_ue5_json(), indent=indent)


class MultiRegionProcessor:
    """
    Processes multiple regions and handles cross-region attraction.
    
    Example:
        >>> processor = MultiRegionProcessor()
        >>> processor.add_region("forest_clearing", adjacent=["forest_path", "river_bank"])
        >>> processor.add_region("forest_path", adjacent=["forest_clearing", "village"])
        >>> 
        >>> # Update regions
        >>> processor.update_region("forest_clearing", population=0.75)
        >>> processor.update_region("forest_path", population=0.15)
        >>> 
        >>> world_state = processor.process(delta_time=0.5)
    """
    
    def __init__(self):
        self.regions: Dict[str, Dict[str, Any]] = {}
        self.adjacency: Dict[str, List[str]] = {}
        self.calculators: Dict[str, 'VDICalculator'] = {}
        self.generators: Dict[str, UE5BindingGenerator] = {}
        self._output_gen = None
    
    def add_region(self, region_id: str, adjacent: List[str] = None) -> None:
        """Add a region to the processor."""
        from .vdi_calculator import VDICalculator
        from .output_params import OutputGenerator
        
        if self._output_gen is None:
            self._output_gen = OutputGenerator()
        
        self.regions[region_id] = {
            'population': 0.0,
            'last_result': None,
            'last_output': None,
        }
        
        self.adjacency[region_id] = adjacent or []
        self.calculators[region_id] = VDICalculator()
        self.generators[region_id] = UE5BindingGenerator(region_id)
    
    def update_region(self, region_id: str, population: float) -> None:
        """Update a region's population."""
        if region_id in self.regions:
            self.regions[region_id]['population'] = population
    
    def process(self, delta_time: float = 0.5) -> FVDEWorldState:
        """Process all regions and generate world state."""
        world = FVDEWorldState()
        world.timestamp = delta_time  # Could track cumulative time
        
        # First pass: calculate VDI for each region
        for region_id, data in self.regions.items():
            calc = self.calculators[region_id]
            result = calc.calculate(
                population=data['population'],
                delta_time=delta_time
            )
            output = self._output_gen.generate(result)
            
            data['last_result'] = result
            data['last_output'] = output
            
            # Check if this region is an attraction source
            if result.smoothed_vdi > 0.35:  # High pressure
                world.attraction_sources.append(region_id)
        
        # Second pass: apply attraction to adjacent low-pop regions
        for source_id in world.attraction_sources:
            adjacent = self.adjacency.get(source_id, [])
            targets = []
            
            for adj_id in adjacent:
                if adj_id in self.regions:
                    adj_data = self.regions[adj_id]
                    if adj_data['last_result'].population < 0.25:
                        targets.append(adj_id)
                        # Boost attraction in target region
                        # (would modify the output here)
            
            if targets:
                world.attraction_targets[source_id] = targets
        
        # Third pass: generate UE5 states
        for region_id, data in self.regions.items():
            gen = self.generators[region_id]
            state = gen.generate_region_state(
                data['last_result'],
                data['last_output'],
                delta_time
            )
            world.regions[region_id] = state
        
        return world
    
    def reset(self) -> None:
        """Reset all regions."""
        for calc in self.calculators.values():
            calc.reset()
        for gen in self.generators.values():
            gen.reset()
