"""
Visual Discomfort Engine (VDE) for the Living Soundscape Engine.

Works alongside the LSE to create holistic environmental pressure
through visual manipulation. Outputs parameters for UE5 consumption.

Key principle: VDI lags SDI. Audio and visual discomfort correlate
but never synchronize, preventing player detection.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import math


class VisualPhase(Enum):
    """Visual pressure phases."""
    PRISTINE = "pristine"       # 0-10%: Maximum comfort
    HEALTHY = "healthy"         # 10-20%: Natural state
    OCCUPIED = "occupied"       # 20-35%: Subtle wear begins
    BUSY = "busy"               # 35-50%: Motion irregularity
    CROWDED = "crowded"         # 50-70%: Clear fatigue
    SATURATED = "saturated"     # 70%+: Maximum pressure


class WildlifeState(Enum):
    """Wildlife behavior states."""
    THRIVING = "thriving"       # Full activity
    WARY = "wary"               # Reduced, cautious
    RETREATING = "retreating"   # Edge only
    ABSENT = "absent"           # Gone


@dataclass
class VisualThresholds:
    """Configurable thresholds for visual phases."""
    pristine_max: float = 0.10
    healthy_max: float = 0.20
    occupied_max: float = 0.35
    busy_max: float = 0.50
    crowded_max: float = 0.70
    # Above crowded_max = SATURATED


@dataclass 
class VDIFactors:
    """Visual discomfort factor breakdown."""
    # Discomfort factors (positive)
    motion_incoherence: float = 0.0
    visual_density: float = 0.0
    light_diffusion: float = 0.0
    environmental_wear: float = 0.0
    wildlife_absence: float = 0.0
    npc_unease: float = 0.0
    spatial_noise: float = 0.0
    
    # Comfort factors (negative)
    motion_coherence: float = 0.0
    visual_clarity: float = 0.0
    light_quality: float = 0.0
    environmental_health: float = 0.0
    wildlife_presence: float = 0.0
    npc_comfort: float = 0.0
    spatial_invitation: float = 0.0
    
    @property
    def discomfort_total(self) -> float:
        return (
            self.motion_incoherence +
            self.visual_density +
            self.light_diffusion +
            self.environmental_wear +
            self.wildlife_absence +
            self.npc_unease +
            self.spatial_noise
        )
    
    @property
    def comfort_total(self) -> float:
        return (
            self.motion_coherence +
            self.visual_clarity +
            self.light_quality +
            self.environmental_health +
            self.wildlife_presence +
            self.npc_comfort +
            self.spatial_invitation
        )
    
    @property
    def total(self) -> float:
        return self.discomfort_total + self.comfort_total
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'motion_incoherence': self.motion_incoherence,
            'visual_density': self.visual_density,
            'light_diffusion': self.light_diffusion,
            'environmental_wear': self.environmental_wear,
            'wildlife_absence': self.wildlife_absence,
            'npc_unease': self.npc_unease,
            'spatial_noise': self.spatial_noise,
            'motion_coherence': self.motion_coherence,
            'visual_clarity': self.visual_clarity,
            'light_quality': self.light_quality,
            'environmental_health': self.environmental_health,
            'wildlife_presence': self.wildlife_presence,
            'npc_comfort': self.npc_comfort,
            'spatial_invitation': self.spatial_invitation,
            'discomfort_total': self.discomfort_total,
            'comfort_total': self.comfort_total,
            'total': self.total,
        }


@dataclass
class PostProcessParams:
    """Post-processing parameters for UE5."""
    bloom_intensity_mod: float = 0.0      # 0.0 = crisp, 1.0 = diffused
    contrast_reduction: float = 0.0        # 0.0 = full, 1.0 = flat
    shadow_softness: float = 0.0           # 0.0 = sharp, 1.0 = diffuse
    color_saturation_mod: float = 1.0      # 0.95-1.0 range only
    distance_haze_density: float = 0.0     # 0.0 = clear, 1.0 = hazy
    vignette_subtle: float = 0.0           # Very subtle edge darkening
    color_temperature_shift: float = 0.0   # -1 = cool, +1 = warm
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'bloom_intensity_mod': self.bloom_intensity_mod,
            'contrast_reduction': self.contrast_reduction,
            'shadow_softness': self.shadow_softness,
            'color_saturation_mod': self.color_saturation_mod,
            'distance_haze_density': self.distance_haze_density,
            'vignette_subtle': self.vignette_subtle,
            'color_temperature_shift': self.color_temperature_shift,
        }


@dataclass
class MaterialParams:
    """Material parameters for UE5."""
    foliage_restlessness: float = 0.0      # Animation irregularity
    cloth_settle_time: float = 1.0         # Time for cloth to rest (seconds)
    water_clarity: float = 1.0             # 1.0 = clear, 0.0 = murky
    ground_wear: float = 0.0               # Decal intensity
    prop_micro_jitter: float = 0.0         # Imperceptible movement
    grass_trampling: float = 0.0           # Shader-driven displacement
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'foliage_restlessness': self.foliage_restlessness,
            'cloth_settle_time': self.cloth_settle_time,
            'water_clarity': self.water_clarity,
            'ground_wear': self.ground_wear,
            'prop_micro_jitter': self.prop_micro_jitter,
            'grass_trampling': self.grass_trampling,
        }


@dataclass
class SpawnParams:
    """Spawning parameters for wildlife and NPCs."""
    wildlife_spawn_rate: float = 1.0       # Multiplier
    bird_landing_chance: float = 1.0       # Probability
    insect_density: float = 1.0            # Multiplier
    npc_idle_variety: float = 1.0          # How many behaviors available
    npc_comfort_level: float = 1.0         # Affects idle selection
    wildlife_state: WildlifeState = WildlifeState.THRIVING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'wildlife_spawn_rate': self.wildlife_spawn_rate,
            'bird_landing_chance': self.bird_landing_chance,
            'insect_density': self.insect_density,
            'npc_idle_variety': self.npc_idle_variety,
            'npc_comfort_level': self.npc_comfort_level,
            'wildlife_state': self.wildlife_state.value,
        }


@dataclass
class ParticleParams:
    """Particle system parameters."""
    dust_density: float = 0.0              # Airborne particles
    pollen_intensity: float = 0.0          # Organic particles  
    debris_frequency: float = 0.0          # Leaves, small debris
    particle_coherence: float = 1.0        # Motion alignment (1 = aligned)
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'dust_density': self.dust_density,
            'pollen_intensity': self.pollen_intensity,
            'debris_frequency': self.debris_frequency,
            'particle_coherence': self.particle_coherence,
        }


@dataclass
class MotionParams:
    """Motion coherence parameters."""
    wind_direction_variance: float = 0.0   # 0 = unified, 1 = chaotic
    animation_phase_sync: float = 1.0      # 1 = synced, 0 = random
    foliage_wave_coherence: float = 1.0    # Wave pattern alignment
    cloth_rest_achieved: float = 1.0       # How settled cloth is
    prop_stability: float = 1.0            # 1 = still, 0 = jittery
    
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
    """Attraction signals for nearby regions."""
    light_quality_boost: float = 0.0       # Added comfort lighting
    wildlife_surge: float = 0.0            # Spawn rate boost
    visual_clarity_boost: float = 0.0      # Haze reduction
    motion_coherence_boost: float = 0.0    # Extra animation sync
    broadcasting: bool = False             # Is this region broadcasting?
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'light_quality_boost': self.light_quality_boost,
            'wildlife_surge': self.wildlife_surge,
            'visual_clarity_boost': self.visual_clarity_boost,
            'motion_coherence_boost': self.motion_coherence_boost,
            'broadcasting': self.broadcasting,
        }


@dataclass
class VDEState:
    """Complete VDE state."""
    # Core values
    raw_vdi: float = 0.0
    smoothed_vdi: float = 0.0
    target_vdi: float = 0.0
    
    # Phase
    phase: VisualPhase = VisualPhase.PRISTINE
    population: float = 0.0
    
    # Factor breakdown
    factors: VDIFactors = field(default_factory=VDIFactors)
    
    # Output parameters
    post_process: PostProcessParams = field(default_factory=PostProcessParams)
    materials: MaterialParams = field(default_factory=MaterialParams)
    spawning: SpawnParams = field(default_factory=SpawnParams)
    particles: ParticleParams = field(default_factory=ParticleParams)
    motion: MotionParams = field(default_factory=MotionParams)
    attraction: AttractionParams = field(default_factory=AttractionParams)
    
    # Timing
    time_in_phase: float = 0.0
    last_phase_change: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'raw_vdi': self.raw_vdi,
            'smoothed_vdi': self.smoothed_vdi,
            'target_vdi': self.target_vdi,
            'phase': self.phase.value,
            'population': self.population,
            'factors': self.factors.to_dict(),
            'post_process': self.post_process.to_dict(),
            'materials': self.materials.to_dict(),
            'spawning': self.spawning.to_dict(),
            'particles': self.particles.to_dict(),
            'motion': self.motion.to_dict(),
            'attraction': self.attraction.to_dict(),
        }


class VDECalculator:
    """
    Calculates VDI factors and output parameters.
    
    This is the visual equivalent of SDICalculator from the LSE.
    """
    
    # Factor weights
    WEIGHTS = {
        # Discomfort (positive)
        'motion_incoherence': 0.15,
        'visual_density': 0.12,
        'light_diffusion': 0.10,
        'environmental_wear': 0.08,
        'wildlife_absence': 0.12,
        'npc_unease': 0.08,
        'spatial_noise': 0.10,
        
        # Comfort (negative)
        'motion_coherence': -0.12,
        'visual_clarity': -0.10,
        'light_quality': -0.08,
        'environmental_health': -0.10,
        'wildlife_presence': -0.15,
        'npc_comfort': -0.08,
        'spatial_invitation': -0.10,
    }
    
    def __init__(self, thresholds: Optional[VisualThresholds] = None):
        self.thresholds = thresholds or VisualThresholds()
        self._smoothed_vdi = 0.0
        self._smoothing_factor = 0.15  # Slower than SDI
        
        # Wildlife recovery tracking
        self._wildlife_state = WildlifeState.THRIVING
        self._wildlife_transition_time = 0.0
        self._target_wildlife_state = WildlifeState.THRIVING
        
        # Wear accumulation
        self._accumulated_wear = 0.0
        self._wear_decay_rate = 0.002  # Per second when population low
        self._wear_accumulation_rate = 0.01  # Per second at high population
    
    def calculate(self, 
                  population: float,
                  current_time: float,
                  delta_time: float,
                  biome_type: str = "forest",
                  weather: str = "clear",
                  time_of_day: str = "day") -> VDEState:
        """
        Calculate complete VDE state.
        
        Args:
            population: Population ratio (0.0-1.0)
            current_time: Current simulation time
            delta_time: Time since last calculation
            biome_type: Current biome
            weather: Current weather
            time_of_day: Current time of day
            
        Returns:
            Complete VDEState with all parameters
        """
        state = VDEState()
        state.population = population
        
        # Determine phase
        state.phase = self._determine_phase(population)
        
        # Update wildlife state (with recovery lag)
        self._update_wildlife_state(population, delta_time)
        state.spawning.wildlife_state = self._wildlife_state
        
        # Update wear accumulation
        self._update_wear(population, delta_time)
        
        # Calculate factors
        state.factors = self._calculate_factors(population, state.phase)
        
        # Calculate raw VDI
        state.raw_vdi = state.factors.total
        state.raw_vdi = max(-1.0, min(1.0, state.raw_vdi))
        
        # Apply smoothing (slower than SDI)
        self._smoothed_vdi = self._apply_smoothing(state.raw_vdi)
        state.smoothed_vdi = self._smoothed_vdi
        
        # Calculate target from population (similar curve to SDI)
        state.target_vdi = self._calculate_target(population)
        
        # Generate output parameters
        state.post_process = self._generate_post_process(state)
        state.materials = self._generate_materials(state)
        state.spawning = self._generate_spawning(state)
        state.particles = self._generate_particles(state)
        state.motion = self._generate_motion(state)
        state.attraction = self._generate_attraction(state)
        
        return state
    
    def _determine_phase(self, population: float) -> VisualPhase:
        """Determine visual phase from population."""
        t = self.thresholds
        
        if population < t.pristine_max:
            return VisualPhase.PRISTINE
        elif population < t.healthy_max:
            return VisualPhase.HEALTHY
        elif population < t.occupied_max:
            return VisualPhase.OCCUPIED
        elif population < t.busy_max:
            return VisualPhase.BUSY
        elif population < t.crowded_max:
            return VisualPhase.CROWDED
        else:
            return VisualPhase.SATURATED
    
    def _update_wildlife_state(self, population: float, delta_time: float) -> None:
        """Update wildlife state with recovery lag."""
        # Determine target state from population
        if population < 0.15:
            target = WildlifeState.THRIVING
        elif population < 0.30:
            target = WildlifeState.WARY
        elif population < 0.50:
            target = WildlifeState.RETREATING
        else:
            target = WildlifeState.ABSENT
        
        # Wildlife flees quickly but returns slowly
        states = [WildlifeState.THRIVING, WildlifeState.WARY, 
                  WildlifeState.RETREATING, WildlifeState.ABSENT]
        current_idx = states.index(self._wildlife_state)
        target_idx = states.index(target)
        
        if target_idx > current_idx:
            # Fleeing - fast
            self._wildlife_transition_time += delta_time * 2.0
            if self._wildlife_transition_time >= 5.0:  # 5 seconds to flee one step
                self._wildlife_state = states[min(current_idx + 1, len(states) - 1)]
                self._wildlife_transition_time = 0.0
        elif target_idx < current_idx:
            # Returning - slow
            self._wildlife_transition_time += delta_time
            recovery_times = [60.0, 45.0, 30.0]  # Seconds per step back
            if current_idx > 0:
                required_time = recovery_times[current_idx - 1]
                if self._wildlife_transition_time >= required_time:
                    self._wildlife_state = states[current_idx - 1]
                    self._wildlife_transition_time = 0.0
        else:
            self._wildlife_transition_time = 0.0
    
    def _update_wear(self, population: float, delta_time: float) -> None:
        """Update environmental wear accumulation."""
        if population > 0.3:
            # Accumulate wear
            rate = self._wear_accumulation_rate * (population - 0.3) / 0.7
            self._accumulated_wear += rate * delta_time
            self._accumulated_wear = min(1.0, self._accumulated_wear)
        elif population < 0.2:
            # Decay wear
            decay = self._wear_decay_rate * (0.2 - population) / 0.2
            self._accumulated_wear -= decay * delta_time
            self._accumulated_wear = max(0.0, self._accumulated_wear)
    
    def _calculate_factors(self, population: float, 
                           phase: VisualPhase) -> VDIFactors:
        """Calculate all VDI factors."""
        factors = VDIFactors()
        
        # Population-based scaling
        pop_pressure = max(0, (population - 0.15) / 0.85)  # 0 at 15%, 1 at 100%
        pop_comfort = max(0, (0.25 - population) / 0.25)   # 1 at 0%, 0 at 25%
        
        # Discomfort factors
        if phase in (VisualPhase.BUSY, VisualPhase.CROWDED, VisualPhase.SATURATED):
            factors.motion_incoherence = self.WEIGHTS['motion_incoherence'] * pop_pressure
        
        if phase in (VisualPhase.OCCUPIED, VisualPhase.BUSY, 
                     VisualPhase.CROWDED, VisualPhase.SATURATED):
            factors.visual_density = self.WEIGHTS['visual_density'] * pop_pressure * 0.8
        
        if phase in (VisualPhase.CROWDED, VisualPhase.SATURATED):
            factors.light_diffusion = self.WEIGHTS['light_diffusion'] * pop_pressure
        
        factors.environmental_wear = self.WEIGHTS['environmental_wear'] * self._accumulated_wear
        
        # Wildlife absence based on state
        wildlife_absence_map = {
            WildlifeState.THRIVING: 0.0,
            WildlifeState.WARY: 0.3,
            WildlifeState.RETREATING: 0.6,
            WildlifeState.ABSENT: 1.0,
        }
        factors.wildlife_absence = (self.WEIGHTS['wildlife_absence'] * 
                                    wildlife_absence_map[self._wildlife_state])
        
        if phase in (VisualPhase.CROWDED, VisualPhase.SATURATED):
            factors.npc_unease = self.WEIGHTS['npc_unease'] * pop_pressure
        
        if phase == VisualPhase.SATURATED:
            factors.spatial_noise = self.WEIGHTS['spatial_noise'] * pop_pressure
        
        # Comfort factors (only at low population)
        if phase in (VisualPhase.PRISTINE, VisualPhase.HEALTHY):
            factors.motion_coherence = self.WEIGHTS['motion_coherence'] * pop_comfort
            factors.visual_clarity = self.WEIGHTS['visual_clarity'] * pop_comfort
            factors.light_quality = self.WEIGHTS['light_quality'] * pop_comfort
            factors.spatial_invitation = self.WEIGHTS['spatial_invitation'] * pop_comfort
        
        if self._accumulated_wear < 0.2:
            factors.environmental_health = (self.WEIGHTS['environmental_health'] * 
                                            (1.0 - self._accumulated_wear / 0.2) * pop_comfort)
        
        if self._wildlife_state == WildlifeState.THRIVING:
            factors.wildlife_presence = self.WEIGHTS['wildlife_presence'] * pop_comfort
        
        if phase == VisualPhase.PRISTINE:
            factors.npc_comfort = self.WEIGHTS['npc_comfort'] * pop_comfort
        
        return factors
    
    def _apply_smoothing(self, raw_vdi: float) -> float:
        """Apply exponential smoothing to VDI."""
        return self._smoothed_vdi + self._smoothing_factor * (raw_vdi - self._smoothed_vdi)
    
    def _calculate_target(self, population: float) -> float:
        """Calculate target VDI from population."""
        # Similar curve to SDI population mapping
        if population < 0.15:
            return -0.2  # Comfortable
        elif population < 0.35:
            return (population - 0.15) / 0.20 * 0.2 - 0.1  # Transition
        elif population < 0.70:
            return (population - 0.35) / 0.35 * 0.4 + 0.1  # Building
        else:
            return (population - 0.70) / 0.30 * 0.3 + 0.5  # Maximum
    
    def _generate_post_process(self, state: VDEState) -> PostProcessParams:
        """Generate post-processing parameters."""
        params = PostProcessParams()
        
        vdi = max(0, state.smoothed_vdi)  # Only positive VDI affects post-process
        
        params.bloom_intensity_mod = vdi * 0.3  # Up to 30% bloom increase
        params.contrast_reduction = vdi * 0.25  # Up to 25% contrast loss
        params.shadow_softness = vdi * 0.35  # Up to 35% softer shadows
        params.color_saturation_mod = 1.0 - vdi * 0.05  # Max 5% desaturation
        params.distance_haze_density = vdi * 0.2  # Up to 20% haze
        params.vignette_subtle = vdi * 0.1  # Very subtle
        
        # Color temperature: cooler when uncomfortable
        params.color_temperature_shift = -vdi * 0.15
        
        # Comfort boost (negative VDI)
        if state.smoothed_vdi < 0:
            comfort = abs(state.smoothed_vdi)
            params.color_temperature_shift = comfort * 0.1  # Warmer
        
        return params
    
    def _generate_materials(self, state: VDEState) -> MaterialParams:
        """Generate material parameters."""
        params = MaterialParams()
        
        vdi = max(0, state.smoothed_vdi)
        
        params.foliage_restlessness = vdi * 0.4  # Up to 40% irregular motion
        params.cloth_settle_time = 1.0 + vdi * 3.0  # 1-4 seconds to settle
        params.water_clarity = 1.0 - vdi * 0.5  # Up to 50% murkier
        params.ground_wear = self._accumulated_wear
        params.prop_micro_jitter = vdi * 0.15  # Subtle jitter
        params.grass_trampling = self._accumulated_wear * 0.8
        
        return params
    
    def _generate_spawning(self, state: VDEState) -> SpawnParams:
        """Generate spawning parameters."""
        params = SpawnParams()
        
        # Wildlife state already updated
        params.wildlife_state = self._wildlife_state
        
        # Spawn rates based on wildlife state
        spawn_rates = {
            WildlifeState.THRIVING: (1.0, 1.0, 1.0),
            WildlifeState.WARY: (0.6, 0.4, 0.8),
            WildlifeState.RETREATING: (0.2, 0.1, 0.5),
            WildlifeState.ABSENT: (0.0, 0.0, 0.2),
        }
        
        rates = spawn_rates[self._wildlife_state]
        params.wildlife_spawn_rate = rates[0]
        params.bird_landing_chance = rates[1]
        params.insect_density = rates[2]
        
        # NPC comfort
        vdi = state.smoothed_vdi
        if vdi < 0:
            params.npc_idle_variety = 1.0
            params.npc_comfort_level = 1.0
        elif vdi < 0.3:
            params.npc_idle_variety = 0.8
            params.npc_comfort_level = 0.7
        elif vdi < 0.5:
            params.npc_idle_variety = 0.5
            params.npc_comfort_level = 0.4
        else:
            params.npc_idle_variety = 0.2
            params.npc_comfort_level = 0.2
        
        return params
    
    def _generate_particles(self, state: VDEState) -> ParticleParams:
        """Generate particle parameters."""
        params = ParticleParams()
        
        vdi = max(0, state.smoothed_vdi)
        
        params.dust_density = vdi * 0.4 + self._accumulated_wear * 0.3
        params.pollen_intensity = vdi * 0.25
        params.debris_frequency = vdi * 0.3 + self._accumulated_wear * 0.2
        params.particle_coherence = 1.0 - vdi * 0.4  # Less aligned at high VDI
        
        return params
    
    def _generate_motion(self, state: VDEState) -> MotionParams:
        """Generate motion coherence parameters."""
        params = MotionParams()
        
        vdi = max(0, state.smoothed_vdi)
        comfort = max(0, -state.smoothed_vdi)
        
        # Discomfort = incoherent motion
        params.wind_direction_variance = vdi * 0.35
        params.animation_phase_sync = 1.0 - vdi * 0.4
        params.foliage_wave_coherence = 1.0 - vdi * 0.35
        params.cloth_rest_achieved = 1.0 - vdi * 0.5
        params.prop_stability = 1.0 - vdi * 0.2
        
        # Comfort = extra coherent
        if comfort > 0:
            params.animation_phase_sync = min(1.0, 1.0 + comfort * 0.1)
            params.foliage_wave_coherence = min(1.0, 1.0 + comfort * 0.1)
        
        return params
    
    def _generate_attraction(self, state: VDEState) -> AttractionParams:
        """Generate attraction signals."""
        params = AttractionParams()
        
        # Broadcast attraction when VDI is high
        if state.smoothed_vdi > 0.3:
            params.broadcasting = True
            pressure = (state.smoothed_vdi - 0.3) / 0.7  # 0-1 above threshold
            
            # These are boosts for NEARBY LOW-POP regions
            params.light_quality_boost = pressure * 0.15
            params.wildlife_surge = pressure * 0.25
            params.visual_clarity_boost = pressure * 0.10
            params.motion_coherence_boost = pressure * 0.10
        
        return params
    
    def reset(self) -> None:
        """Reset calculator state."""
        self._smoothed_vdi = 0.0
        self._wildlife_state = WildlifeState.THRIVING
        self._wildlife_transition_time = 0.0
        self._accumulated_wear = 0.0


class VDEEngine:
    """
    Visual Discomfort Engine - main interface.
    
    Example:
        >>> vde = VDEEngine()
        >>> 
        >>> # Each frame
        >>> state = vde.tick(population=0.45, delta_time=0.016)
        >>> 
        >>> # Get parameters for UE5
        >>> post_process = state.post_process.to_dict()
        >>> materials = state.materials.to_dict()
    """
    
    def __init__(self, thresholds: Optional[VisualThresholds] = None):
        self.calculator = VDECalculator(thresholds)
        self._current_time = 0.0
        self._population = 0.0
        self._last_state: Optional[VDEState] = None
        
        # Lag settings for SDI coupling
        self.lag_rise = 10.0   # Seconds to follow SDI up
        self.lag_fall = 15.0   # Seconds to follow SDI down
        
        # Population smoothing for lag
        self._target_population = 0.0
        self._lagged_population = 0.0
    
    def set_population(self, population: float) -> None:
        """Set target population (will lag to this value)."""
        self._target_population = max(0.0, min(1.0, population))
    
    def tick(self, delta_time: float, 
             population: Optional[float] = None,
             biome_type: str = "forest",
             weather: str = "clear",
             time_of_day: str = "day") -> VDEState:
        """
        Run one VDE tick.
        
        Args:
            delta_time: Time since last tick
            population: Population override (or use set_population)
            biome_type: Current biome
            weather: Current weather
            time_of_day: Current time of day
            
        Returns:
            Complete VDEState
        """
        self._current_time += delta_time
        
        if population is not None:
            self._target_population = max(0.0, min(1.0, population))
        
        # Apply population lag
        self._update_lagged_population(delta_time)
        
        # Calculate state
        state = self.calculator.calculate(
            population=self._lagged_population,
            current_time=self._current_time,
            delta_time=delta_time,
            biome_type=biome_type,
            weather=weather,
            time_of_day=time_of_day,
        )
        
        self._last_state = state
        self._population = self._lagged_population
        
        return state
    
    def _update_lagged_population(self, delta_time: float) -> None:
        """Update lagged population with asymmetric timing."""
        diff = self._target_population - self._lagged_population
        
        if diff > 0:
            # Rising - use rise lag
            rate = delta_time / self.lag_rise
        else:
            # Falling - use fall lag (slower)
            rate = delta_time / self.lag_fall
        
        self._lagged_population += diff * min(1.0, rate * 3.0)
    
    @property
    def vdi(self) -> float:
        """Get current smoothed VDI."""
        if self._last_state:
            return self._last_state.smoothed_vdi
        return 0.0
    
    @property
    def phase(self) -> VisualPhase:
        """Get current visual phase."""
        if self._last_state:
            return self._last_state.phase
        return VisualPhase.PRISTINE
    
    @property
    def wildlife_state(self) -> WildlifeState:
        """Get current wildlife state."""
        if self._last_state:
            return self._last_state.spawning.wildlife_state
        return WildlifeState.THRIVING
    
    def get_state(self) -> Optional[VDEState]:
        """Get last calculated state."""
        return self._last_state
    
    def get_post_process_params(self) -> Dict[str, float]:
        """Get post-process parameters for UE5."""
        if self._last_state:
            return self._last_state.post_process.to_dict()
        return PostProcessParams().to_dict()
    
    def get_material_params(self) -> Dict[str, float]:
        """Get material parameters for UE5."""
        if self._last_state:
            return self._last_state.materials.to_dict()
        return MaterialParams().to_dict()
    
    def get_spawn_params(self) -> Dict[str, Any]:
        """Get spawning parameters."""
        if self._last_state:
            return self._last_state.spawning.to_dict()
        return SpawnParams().to_dict()
    
    def get_motion_params(self) -> Dict[str, float]:
        """Get motion coherence parameters."""
        if self._last_state:
            return self._last_state.motion.to_dict()
        return MotionParams().to_dict()
    
    def reset(self) -> None:
        """Reset the engine."""
        self.calculator.reset()
        self._current_time = 0.0
        self._population = 0.0
        self._target_population = 0.0
        self._lagged_population = 0.0
        self._last_state = None
