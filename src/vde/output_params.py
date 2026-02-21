"""
VDE Output Parameters - Phase 1 Implementation.

Generates normalized parameters for UE5 consumption:
- Post-processing (bloom, contrast, shadows, etc.)
- Materials (foliage, water, ground wear)
- Spawning (wildlife, NPCs)
- Particles (dust, pollen, debris)
- Motion (wind coherence, animation sync)
- Attraction (for low-pop areas)

All values are normalized 0.0-1.0 unless otherwise noted.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from .vdi_calculator import VDIResult, VisualPhase, WildlifeState


@dataclass
class PostProcessParams:
    """
    Post-processing parameters for UE5.
    
    Controls visual quality degradation through post-process effects.
    All values start at 0.0 (no effect) and increase with discomfort.
    """
    bloom_intensity_mod: float = 0.0      # 0.0 = crisp, 0.3 = diffused
    contrast_reduction: float = 0.0        # 0.0 = full contrast, 0.25 = flat
    shadow_softness: float = 0.0           # 0.0 = sharp shadows, 0.35 = diffuse
    saturation_mod: float = 1.0            # 0.95-1.0 only (very subtle)
    haze_density: float = 0.0              # 0.0 = clear, 0.20 = hazy
    vignette: float = 0.0                  # 0.0 = none, 0.10 = subtle edge darkening
    color_temp_shift: float = 0.0          # Kelvin offset (-150 = cooler, +200 = warmer)
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'bloom_intensity_mod': self.bloom_intensity_mod,
            'contrast_reduction': self.contrast_reduction,
            'shadow_softness': self.shadow_softness,
            'saturation_mod': self.saturation_mod,
            'haze_density': self.haze_density,
            'vignette': self.vignette,
            'color_temp_shift': self.color_temp_shift,
        }


@dataclass
class MaterialParams:
    """
    Material parameters for UE5.
    
    Controls material-level visual changes for environmental objects.
    """
    foliage_restlessness: float = 0.0      # 0.0 = calm, 0.4 = restless animation
    cloth_settle_time: float = 1.0         # Seconds for cloth to settle (1.0-4.0)
    water_clarity: float = 1.0             # 1.0 = clear, 0.5 = murky
    ground_wear: float = 0.0               # 0.0 = pristine, 0.8 = heavily worn
    prop_jitter: float = 0.0               # 0.0 = stable, 0.15 = micro-jitter
    grass_trampling: float = 0.0           # 0.0 = upright, 0.8 = trampled
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'foliage_restlessness': self.foliage_restlessness,
            'cloth_settle_time': self.cloth_settle_time,
            'water_clarity': self.water_clarity,
            'ground_wear': self.ground_wear,
            'prop_jitter': self.prop_jitter,
            'grass_trampling': self.grass_trampling,
        }


@dataclass
class SpawnParams:
    """
    Spawning parameters for wildlife and NPCs.
    
    Controls how ambient life behaves in the region.
    """
    wildlife_spawn_rate: float = 1.0       # Multiplier (0.0-1.5)
    bird_landing_chance: float = 1.0       # Probability (0.0-1.0)
    insect_density: float = 1.0            # Multiplier (0.0-1.0)
    npc_idle_variety: float = 1.0          # How many behaviors (0.2-1.0)
    npc_comfort_level: float = 1.0         # Affects idle selection (0.2-1.0)
    npc_reposition_rate: float = 0.0       # How often NPCs shift (0.0-0.5)
    ambient_creature_rate: float = 1.0     # Butterflies, fireflies (0.2-1.0)
    wildlife_state: str = "thriving"       # Current wildlife behavior
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'wildlife_spawn_rate': self.wildlife_spawn_rate,
            'bird_landing_chance': self.bird_landing_chance,
            'insect_density': self.insect_density,
            'npc_idle_variety': self.npc_idle_variety,
            'npc_comfort_level': self.npc_comfort_level,
            'npc_reposition_rate': self.npc_reposition_rate,
            'ambient_creature_rate': self.ambient_creature_rate,
            'wildlife_state': self.wildlife_state,
        }


@dataclass
class ParticleParams:
    """
    Particle system parameters.
    
    Controls ambient particle effects.
    """
    dust_density: float = 0.0              # Airborne dust (0.0-0.7)
    pollen_intensity: float = 0.0          # Organic particles (0.0-0.5)
    debris_frequency: float = 0.0          # Leaves, small debris (0.0-0.5)
    particle_coherence: float = 1.0        # How aligned motion is (0.6-1.0)
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'dust_density': self.dust_density,
            'pollen_intensity': self.pollen_intensity,
            'debris_frequency': self.debris_frequency,
            'particle_coherence': self.particle_coherence,
        }


@dataclass
class MotionParams:
    """
    Motion coherence parameters.
    
    Controls animation synchronization and environmental motion.
    """
    wind_direction_variance: float = 0.0   # 0.0 = unified, 0.3 = chaotic
    animation_phase_sync: float = 1.0      # 1.0 = synced, 0.6 = random
    foliage_wave_coherence: float = 1.0    # Wave alignment (0.6-1.0)
    cloth_rest_achieved: float = 1.0       # How settled cloth is (0.5-1.0)
    prop_stability: float = 1.0            # 1.0 = still, 0.8 = jittery
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'wind_direction_variance': self.wind_direction_variance,
            'animation_phase_sync': self.animation_phase_sync,
            'foliage_wave_coherence': self.foliage_wave_coherence,
            'cloth_rest_achieved': self.cloth_rest_achieved,
            'prop_stability': self.prop_stability,
        }


@dataclass
class AttractionParams:
    """
    Attraction parameters for low-population areas.
    
    These make nearby low-pop regions more visually appealing.
    """
    # Light guidance
    light_temp_boost: float = 0.0          # Kelvin offset (0-200 warmer)
    god_ray_probability: float = 0.0       # Sun breaks (0.0-0.4)
    specular_bonus: float = 0.0            # Eye-catching reflections (0.0-0.15)
    
    # Visual calm
    wind_coherence_boost: float = 0.0      # Extra animation sync (0.0-0.1)
    effect_density_reduction: float = 0.0  # Fewer overlapping effects
    
    # Life attraction
    wildlife_spawn_bonus: float = 0.0      # Extra wildlife (0.0-0.5)
    npc_idle_richness: float = 0.0         # Richer behaviors (0.0-0.3)
    ambient_interaction_rate: float = 0.0  # Environmental interactions
    
    # Environmental affordance
    path_visibility_boost: float = 0.0     # Clearer paths (0.0-0.2)
    foliage_density_reduction: float = 0.0 # Open sightlines (0.0-0.15)
    landmark_clarity: float = 0.0          # Visible landmarks (0.0-0.3)
    
    # Promise
    discovery_visibility: float = 0.0      # Revealed secrets (0.0-0.5)
    distant_activity_spawn: float = 0.0    # Movement at distance (0.0-0.4)
    
    # State
    is_attracting: bool = False            # Is this region attracting?
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'light_temp_boost': self.light_temp_boost,
            'god_ray_probability': self.god_ray_probability,
            'specular_bonus': self.specular_bonus,
            'wind_coherence_boost': self.wind_coherence_boost,
            'effect_density_reduction': self.effect_density_reduction,
            'wildlife_spawn_bonus': self.wildlife_spawn_bonus,
            'npc_idle_richness': self.npc_idle_richness,
            'ambient_interaction_rate': self.ambient_interaction_rate,
            'path_visibility_boost': self.path_visibility_boost,
            'foliage_density_reduction': self.foliage_density_reduction,
            'landmark_clarity': self.landmark_clarity,
            'discovery_visibility': self.discovery_visibility,
            'distant_activity_spawn': self.distant_activity_spawn,
            'is_attracting': self.is_attracting,
        }


@dataclass
class VDEOutputState:
    """Complete VDE output state for UE5."""
    post_process: PostProcessParams = field(default_factory=PostProcessParams)
    materials: MaterialParams = field(default_factory=MaterialParams)
    spawning: SpawnParams = field(default_factory=SpawnParams)
    particles: ParticleParams = field(default_factory=ParticleParams)
    motion: MotionParams = field(default_factory=MotionParams)
    attraction: AttractionParams = field(default_factory=AttractionParams)
    
    # Metadata
    phase: str = "pristine"
    population: float = 0.0
    vdi: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'post_process': self.post_process.to_dict(),
            'materials': self.materials.to_dict(),
            'spawning': self.spawning.to_dict(),
            'particles': self.particles.to_dict(),
            'motion': self.motion.to_dict(),
            'attraction': self.attraction.to_dict(),
            'phase': self.phase,
            'population': self.population,
            'vdi': self.vdi,
        }


class OutputGenerator:
    """
    Generates output parameters from VDI calculation results.
    
    Converts abstract VDI values into concrete, UE5-ready parameters.
    
    Example:
        >>> generator = OutputGenerator()
        >>> output = generator.generate(vdi_result)
        >>> 
        >>> # Get parameters for UE5
        >>> post_process = output.post_process.to_dict()
        >>> materials = output.materials.to_dict()
    """
    
    # Output limits (maximum effect values)
    LIMITS = {
        'bloom_max': 0.30,
        'contrast_max': 0.25,
        'shadow_soft_max': 0.35,
        'saturation_min': 0.95,
        'haze_max': 0.20,
        'vignette_max': 0.10,
        'temp_shift_max': 150.0,
        
        'foliage_restless_max': 0.40,
        'cloth_settle_max': 4.0,
        'water_clarity_min': 0.50,
        'prop_jitter_max': 0.15,
        'grass_trample_max': 0.80,
        
        'dust_max': 0.70,
        'pollen_max': 0.50,
        'debris_max': 0.50,
        'coherence_min': 0.60,
        
        'wind_variance_max': 0.30,
        'phase_sync_min': 0.60,
        'wave_coherence_min': 0.65,
        'cloth_rest_min': 0.50,
        'prop_stable_min': 0.80,
        
        'attraction_threshold': 0.20,
    }
    
    def generate(self, vdi_result: VDIResult) -> VDEOutputState:
        """
        Generate output parameters from VDI result.
        
        Args:
            vdi_result: Result from VDICalculator
            
        Returns:
            Complete VDEOutputState
        """
        output = VDEOutputState()
        output.phase = vdi_result.phase.value
        output.population = vdi_result.population
        output.vdi = vdi_result.smoothed_vdi
        
        # Generate each parameter group
        output.post_process = self._generate_post_process(vdi_result)
        output.materials = self._generate_materials(vdi_result)
        output.spawning = self._generate_spawning(vdi_result)
        output.particles = self._generate_particles(vdi_result)
        output.motion = self._generate_motion(vdi_result)
        output.attraction = self._generate_attraction(vdi_result)
        
        return output
    
    def _generate_post_process(self, result: VDIResult) -> PostProcessParams:
        """Generate post-processing parameters."""
        params = PostProcessParams()
        
        # Only positive VDI affects post-process negatively
        vdi = max(0, result.smoothed_vdi)
        L = self.LIMITS
        
        params.bloom_intensity_mod = vdi * L['bloom_max']
        params.contrast_reduction = vdi * L['contrast_max']
        params.shadow_softness = vdi * L['shadow_soft_max']
        params.saturation_mod = 1.0 - vdi * (1.0 - L['saturation_min'])
        params.haze_density = vdi * L['haze_max']
        params.vignette = vdi * L['vignette_max']
        
        # Color temperature: cooler when uncomfortable, warmer when comfortable
        if result.smoothed_vdi > 0:
            params.color_temp_shift = -vdi * L['temp_shift_max']
        else:
            comfort = abs(result.smoothed_vdi)
            params.color_temp_shift = comfort * 100  # Warmer
        
        return params
    
    def _generate_materials(self, result: VDIResult) -> MaterialParams:
        """Generate material parameters."""
        params = MaterialParams()
        
        vdi = max(0, result.smoothed_vdi)
        wear = result.accumulated_wear
        L = self.LIMITS
        
        params.foliage_restlessness = vdi * L['foliage_restless_max']
        params.cloth_settle_time = 1.0 + vdi * (L['cloth_settle_max'] - 1.0)
        params.water_clarity = 1.0 - wear * (1.0 - L['water_clarity_min'])
        params.ground_wear = wear * L['grass_trample_max']
        params.prop_jitter = vdi * L['prop_jitter_max']
        params.grass_trampling = wear * L['grass_trample_max']
        
        return params
    
    def _generate_spawning(self, result: VDIResult) -> SpawnParams:
        """Generate spawning parameters."""
        params = SpawnParams()
        
        # Wildlife based on state
        wildlife_rates = {
            WildlifeState.THRIVING: (1.0, 1.0, 1.0),
            WildlifeState.WARY: (0.6, 0.4, 0.8),
            WildlifeState.RETREATING: (0.2, 0.1, 0.5),
            WildlifeState.ABSENT: (0.0, 0.0, 0.2),
        }
        
        rates = wildlife_rates.get(result.wildlife_state, (1.0, 1.0, 1.0))
        params.wildlife_spawn_rate = rates[0]
        params.bird_landing_chance = rates[1]
        params.insect_density = rates[2]
        params.wildlife_state = result.wildlife_state.value
        
        # Ambient creatures based on visibility
        params.ambient_creature_rate = max(0.2, result.wildlife_visibility)
        
        # NPC comfort based on phase
        vdi = result.smoothed_vdi
        if vdi < 0:
            params.npc_idle_variety = 1.0
            params.npc_comfort_level = 1.0
            params.npc_reposition_rate = 0.0
        elif vdi < 0.3:
            params.npc_idle_variety = 0.8
            params.npc_comfort_level = 0.7
            params.npc_reposition_rate = 0.1
        elif vdi < 0.5:
            params.npc_idle_variety = 0.5
            params.npc_comfort_level = 0.4
            params.npc_reposition_rate = 0.3
        else:
            params.npc_idle_variety = 0.2
            params.npc_comfort_level = 0.2
            params.npc_reposition_rate = 0.5
        
        return params
    
    def _generate_particles(self, result: VDIResult) -> ParticleParams:
        """Generate particle parameters."""
        params = ParticleParams()
        
        vdi = max(0, result.smoothed_vdi)
        wear = result.accumulated_wear
        L = self.LIMITS
        
        params.dust_density = vdi * 0.5 + wear * 0.2
        params.dust_density = min(L['dust_max'], params.dust_density)
        
        params.pollen_intensity = vdi * L['pollen_max']
        params.debris_frequency = vdi * 0.3 + wear * 0.2
        params.debris_frequency = min(L['debris_max'], params.debris_frequency)
        
        params.particle_coherence = 1.0 - vdi * (1.0 - L['coherence_min'])
        
        return params
    
    def _generate_motion(self, result: VDIResult) -> MotionParams:
        """Generate motion coherence parameters."""
        params = MotionParams()
        
        vdi = max(0, result.smoothed_vdi)
        comfort = max(0, -result.smoothed_vdi)
        L = self.LIMITS
        
        # Discomfort = incoherent motion
        params.wind_direction_variance = vdi * L['wind_variance_max']
        params.animation_phase_sync = 1.0 - vdi * (1.0 - L['phase_sync_min'])
        params.foliage_wave_coherence = 1.0 - vdi * (1.0 - L['wave_coherence_min'])
        params.cloth_rest_achieved = 1.0 - vdi * (1.0 - L['cloth_rest_min'])
        params.prop_stability = 1.0 - vdi * (1.0 - L['prop_stable_min'])
        
        # Comfort bonus (slightly more coherent than baseline)
        if comfort > 0:
            params.animation_phase_sync = min(1.0, params.animation_phase_sync + comfort * 0.05)
            params.foliage_wave_coherence = min(1.0, params.foliage_wave_coherence + comfort * 0.05)
        
        return params
    
    def _generate_attraction(self, result: VDIResult) -> AttractionParams:
        """Generate attraction parameters for low-pop areas."""
        params = AttractionParams()
        
        pop = result.population
        threshold = self.LIMITS['attraction_threshold']
        
        if pop < threshold:
            # Low population - this region is attractive
            attraction_strength = (threshold - pop) / threshold
            params.is_attracting = True
            
            # Light guidance
            params.light_temp_boost = attraction_strength * 200.0  # Kelvin
            params.god_ray_probability = attraction_strength * 0.4
            params.specular_bonus = attraction_strength * 0.15
            
            # Visual calm
            params.wind_coherence_boost = attraction_strength * 0.1
            params.effect_density_reduction = attraction_strength * 0.2
            
            # Life attraction
            params.wildlife_spawn_bonus = attraction_strength * 0.5
            params.npc_idle_richness = attraction_strength * 0.3
            params.ambient_interaction_rate = attraction_strength * 0.4
            
            # Environmental affordance
            params.path_visibility_boost = attraction_strength * 0.2
            params.foliage_density_reduction = attraction_strength * 0.15
            params.landmark_clarity = attraction_strength * 0.3
            
            # Promise
            params.discovery_visibility = attraction_strength * 0.5
            params.distant_activity_spawn = attraction_strength * 0.4
        else:
            params.is_attracting = False
        
        return params
