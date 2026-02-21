"""
VDE Core Calculator - Phase 1 Implementation.

Handles:
- VDI factor calculation
- Population pressure phases
- Basic output parameter generation

This is the foundation for the Visual Discomfort Engine.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import os


class VisualPhase(Enum):
    """Visual pressure phases based on population."""
    PRISTINE = "pristine"       # 0-10%: Maximum comfort, abundant wildlife
    HEALTHY = "healthy"         # 10-20%: Natural state, balanced
    OCCUPIED = "occupied"       # 20-35%: Subtle wear begins
    BUSY = "busy"               # 35-50%: Motion irregularity starts
    CROWDED = "crowded"         # 50-70%: Clear fatigue, light diffusion
    SATURATED = "saturated"     # 70%+: Maximum visual pressure


class WildlifeState(Enum):
    """Wildlife behavior states."""
    THRIVING = "thriving"       # Full activity, birds land, insects hover
    WARY = "wary"               # Reduced landing, quicker flight
    RETREATING = "retreating"   # Animals at edges only, no landing
    ABSENT = "absent"           # No wildlife spawns


@dataclass
class VDEConfig:
    """VDE configuration loaded from JSON."""
    # Thresholds
    pristine_max: float = 0.10
    healthy_max: float = 0.20
    occupied_max: float = 0.35
    busy_max: float = 0.50
    crowded_max: float = 0.70
    
    # Smoothing
    smoothing_factor: float = 0.08
    lag_rise_seconds: float = 10.0
    lag_fall_seconds: float = 15.0
    
    # Wildlife
    wildlife_thriving_max: float = 0.15
    wildlife_wary_max: float = 0.30
    wildlife_retreating_max: float = 0.50
    wildlife_flee_rate: float = 0.15
    wildlife_return_rate: float = 0.03
    
    # Wear
    wear_growth_threshold: float = 0.30
    wear_decay_threshold: float = 0.20
    wear_growth_rate: float = 0.02
    wear_decay_rate: float = 0.005
    
    # Factor weights
    weights: Dict[str, float] = field(default_factory=dict)
    
    @classmethod
    def from_json(cls, path: str) -> 'VDEConfig':
        """Load config from JSON file."""
        config = cls()
        
        if not os.path.exists(path):
            return config
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Load thresholds
        if 'thresholds' in data:
            t = data['thresholds']
            config.pristine_max = t.get('pristine_max', config.pristine_max)
            config.healthy_max = t.get('healthy_max', config.healthy_max)
            config.occupied_max = t.get('occupied_max', config.occupied_max)
            config.busy_max = t.get('busy_max', config.busy_max)
            config.crowded_max = t.get('crowded_max', config.crowded_max)
        
        # Load smoothing
        if 'smoothing' in data:
            s = data['smoothing']
            config.smoothing_factor = s.get('factor', config.smoothing_factor)
            config.lag_rise_seconds = s.get('lag_rise_seconds', config.lag_rise_seconds)
            config.lag_fall_seconds = s.get('lag_fall_seconds', config.lag_fall_seconds)
        
        # Load wildlife
        if 'wildlife' in data:
            w = data['wildlife']
            config.wildlife_thriving_max = w.get('thriving_max_pop', config.wildlife_thriving_max)
            config.wildlife_wary_max = w.get('wary_max_pop', config.wildlife_wary_max)
            config.wildlife_retreating_max = w.get('retreating_max_pop', config.wildlife_retreating_max)
            config.wildlife_flee_rate = w.get('flee_rate', config.wildlife_flee_rate)
            config.wildlife_return_rate = w.get('return_rate', config.wildlife_return_rate)
        
        # Load wear
        if 'wear' in data:
            wr = data['wear']
            config.wear_growth_threshold = wr.get('growth_threshold', config.wear_growth_threshold)
            config.wear_decay_threshold = wr.get('decay_threshold', config.wear_decay_threshold)
            config.wear_growth_rate = wr.get('growth_rate', config.wear_growth_rate)
            config.wear_decay_rate = wr.get('decay_rate', config.wear_decay_rate)
        
        # Load weights
        if 'factor_weights' in data:
            fw = data['factor_weights']
            config.weights = {}
            if 'discomfort' in fw:
                config.weights.update(fw['discomfort'])
            if 'comfort' in fw:
                config.weights.update(fw['comfort'])
        
        return config


@dataclass
class VDIFactors:
    """
    Visual Discomfort Index factor breakdown.
    
    Positive values = discomfort (push away)
    Negative values = comfort (pull toward)
    """
    # Discomfort factors (positive values)
    motion_incoherence: float = 0.0   # Foliage/cloth out of sync
    visual_density: float = 0.0        # Overlapping decals, particles
    light_diffusion: float = 0.0       # Soft shadows, bloom bleed
    environmental_wear: float = 0.0    # Trampled grass, murky water
    wildlife_absence: float = 0.0      # No birds, no ambient creatures
    npc_unease: float = 0.0            # NPCs repositioning
    spatial_noise: float = 0.0         # Hard to parse visually
    
    # Comfort factors (negative values)
    motion_coherence: float = 0.0      # Wind/foliage aligned
    visual_clarity: float = 0.0        # Clean sightlines
    light_quality: float = 0.0         # Intentional lighting
    environmental_health: float = 0.0  # Fresh grass, clear water
    wildlife_presence: float = 0.0     # Birds, insects, life
    npc_comfort: float = 0.0           # NPCs relaxed
    spatial_invitation: float = 0.0    # Open paths, framing
    
    @property
    def discomfort_total(self) -> float:
        """Sum of discomfort factors."""
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
        """Sum of comfort factors (negative)."""
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
        """Net VDI contribution."""
        return self.discomfort_total + self.comfort_total
    
    def get_top_contributors(self) -> Tuple[Tuple[str, float], Tuple[str, float]]:
        """Get top positive and negative contributors."""
        discomfort = [
            ('motion_incoherence', self.motion_incoherence),
            ('visual_density', self.visual_density),
            ('light_diffusion', self.light_diffusion),
            ('environmental_wear', self.environmental_wear),
            ('wildlife_absence', self.wildlife_absence),
            ('npc_unease', self.npc_unease),
            ('spatial_noise', self.spatial_noise),
        ]
        
        comfort = [
            ('motion_coherence', self.motion_coherence),
            ('visual_clarity', self.visual_clarity),
            ('light_quality', self.light_quality),
            ('environmental_health', self.environmental_health),
            ('wildlife_presence', self.wildlife_presence),
            ('npc_comfort', self.npc_comfort),
            ('spatial_invitation', self.spatial_invitation),
        ]
        
        top_discomfort = max(discomfort, key=lambda x: x[1])
        top_comfort = min(comfort, key=lambda x: x[1])
        
        return top_discomfort, top_comfort
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
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
class VDIResult:
    """Complete VDI calculation result."""
    # Core values
    raw_vdi: float = 0.0
    smoothed_vdi: float = 0.0
    target_vdi: float = 0.0
    delta: float = 0.0  # target - smoothed
    
    # Phase info
    phase: VisualPhase = VisualPhase.PRISTINE
    population: float = 0.0
    
    # Factor breakdown
    factors: VDIFactors = field(default_factory=VDIFactors)
    
    # Wildlife state
    wildlife_state: WildlifeState = WildlifeState.THRIVING
    wildlife_visibility: float = 1.0  # 0-1, how visible wildlife is
    
    # Environmental wear
    accumulated_wear: float = 0.0
    
    # Delta categorization (mirrors SDI)
    delta_category: str = "none"  # none, small, medium, large
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'raw_vdi': self.raw_vdi,
            'smoothed_vdi': self.smoothed_vdi,
            'target_vdi': self.target_vdi,
            'delta': self.delta,
            'delta_category': self.delta_category,
            'phase': self.phase.value,
            'population': self.population,
            'wildlife_state': self.wildlife_state.value,
            'wildlife_visibility': self.wildlife_visibility,
            'accumulated_wear': self.accumulated_wear,
            'factors': self.factors.to_dict(),
        }


class VDICalculator:
    """
    Core VDI calculator.
    
    Handles:
    - Phase determination from population
    - Factor calculation based on phase
    - Wildlife state tracking with recovery lag
    - Wear accumulation and decay
    - VDI smoothing
    
    Example:
        >>> calc = VDICalculator()
        >>> result = calc.calculate(population=0.45, delta_time=0.5)
        >>> print(result.phase)  # VisualPhase.BUSY
        >>> print(result.smoothed_vdi)  # ~0.15
    """
    
    # Default factor weights (from design doc)
    DEFAULT_WEIGHTS = {
        # Discomfort
        'motion_incoherence': 0.15,
        'visual_density': 0.12,
        'light_diffusion': 0.10,
        'environmental_wear': 0.08,
        'wildlife_absence': 0.12,
        'npc_unease': 0.08,
        'spatial_noise': 0.10,
        # Comfort
        'motion_coherence': -0.12,
        'visual_clarity': -0.10,
        'light_quality': -0.08,
        'environmental_health': -0.10,
        'wildlife_presence': -0.15,
        'npc_comfort': -0.08,
        'spatial_invitation': -0.10,
    }
    
    # Delta thresholds
    DELTA_THRESHOLDS = {
        'small': 0.10,
        'medium': 0.25,
        'large': 0.40,
    }
    
    def __init__(self, config: Optional[VDEConfig] = None):
        """
        Initialize the calculator.
        
        Args:
            config: VDE configuration, or None for defaults
        """
        self.config = config or VDEConfig()
        self.weights = config.weights if config and config.weights else self.DEFAULT_WEIGHTS
        
        # State
        self._smoothed_vdi = 0.0
        self._wildlife_state = WildlifeState.THRIVING
        self._wildlife_visibility = 1.0
        self._wildlife_transition_progress = 0.0
        self._accumulated_wear = 0.0
    
    def calculate(self, 
                  population: float,
                  delta_time: float = 0.5,
                  current_time: float = 0.0) -> VDIResult:
        """
        Calculate VDI for current population.
        
        Args:
            population: Population ratio (0.0 to 1.0)
            delta_time: Time since last calculation
            current_time: Current simulation time
            
        Returns:
            Complete VDIResult
        """
        result = VDIResult()
        result.population = population
        
        # 1. Determine phase
        result.phase = self._determine_phase(population)
        
        # 2. Update wildlife state
        self._update_wildlife(population, delta_time)
        result.wildlife_state = self._wildlife_state
        result.wildlife_visibility = self._wildlife_visibility
        
        # 3. Update wear accumulation
        self._update_wear(population, delta_time)
        result.accumulated_wear = self._accumulated_wear
        
        # 4. Calculate factors
        result.factors = self._calculate_factors(population, result.phase)
        
        # 5. Calculate raw VDI
        result.raw_vdi = result.factors.total
        result.raw_vdi = max(-1.0, min(1.0, result.raw_vdi))
        
        # 6. Apply smoothing
        self._smoothed_vdi = self._apply_smoothing(result.raw_vdi)
        result.smoothed_vdi = self._smoothed_vdi
        
        # 7. Calculate target (for debugging/tuning)
        result.target_vdi = self._calculate_target(population)
        result.delta = result.target_vdi - result.smoothed_vdi
        result.delta_category = self._categorize_delta(result.delta)
        
        return result
    
    def _determine_phase(self, population: float) -> VisualPhase:
        """Determine visual phase from population."""
        c = self.config
        
        if population < c.pristine_max:
            return VisualPhase.PRISTINE
        elif population < c.healthy_max:
            return VisualPhase.HEALTHY
        elif population < c.occupied_max:
            return VisualPhase.OCCUPIED
        elif population < c.busy_max:
            return VisualPhase.BUSY
        elif population < c.crowded_max:
            return VisualPhase.CROWDED
        else:
            return VisualPhase.SATURATED
    
    def _update_wildlife(self, population: float, delta_time: float) -> None:
        """Update wildlife state with asymmetric timing."""
        c = self.config
        
        # Determine target state
        if population < c.wildlife_thriving_max:
            target = WildlifeState.THRIVING
        elif population < c.wildlife_wary_max:
            target = WildlifeState.WARY
        elif population < c.wildlife_retreating_max:
            target = WildlifeState.RETREATING
        else:
            target = WildlifeState.ABSENT
        
        # Wildlife flees fast, returns slow
        states = [WildlifeState.THRIVING, WildlifeState.WARY, 
                  WildlifeState.RETREATING, WildlifeState.ABSENT]
        current_idx = states.index(self._wildlife_state)
        target_idx = states.index(target)
        
        if target_idx > current_idx:
            # Fleeing - fast
            self._wildlife_transition_progress += delta_time * c.wildlife_flee_rate * 10
            if self._wildlife_transition_progress >= 1.0:
                self._wildlife_state = states[min(current_idx + 1, len(states) - 1)]
                self._wildlife_transition_progress = 0.0
        elif target_idx < current_idx:
            # Returning - slow
            self._wildlife_transition_progress += delta_time * c.wildlife_return_rate * 10
            if self._wildlife_transition_progress >= 1.0:
                self._wildlife_state = states[max(current_idx - 1, 0)]
                self._wildlife_transition_progress = 0.0
        else:
            self._wildlife_transition_progress = 0.0
        
        # Update visibility based on state
        visibility_map = {
            WildlifeState.THRIVING: 1.0,
            WildlifeState.WARY: 0.6,
            WildlifeState.RETREATING: 0.2,
            WildlifeState.ABSENT: 0.0,
        }
        target_visibility = visibility_map[self._wildlife_state]
        
        # Smooth visibility changes
        diff = target_visibility - self._wildlife_visibility
        self._wildlife_visibility += diff * min(1.0, delta_time * 2.0)
    
    def _update_wear(self, population: float, delta_time: float) -> None:
        """Update environmental wear accumulation."""
        c = self.config
        
        if population > c.wear_growth_threshold:
            # Accumulate wear
            rate = c.wear_growth_rate * (population - c.wear_growth_threshold) / (1.0 - c.wear_growth_threshold)
            self._accumulated_wear += rate * delta_time
            self._accumulated_wear = min(1.0, self._accumulated_wear)
        elif population < c.wear_decay_threshold:
            # Decay wear
            rate = c.wear_decay_rate * (c.wear_decay_threshold - population) / c.wear_decay_threshold
            self._accumulated_wear -= rate * delta_time
            self._accumulated_wear = max(0.0, self._accumulated_wear)
    
    def _calculate_factors(self, population: float, 
                           phase: VisualPhase) -> VDIFactors:
        """Calculate all VDI factors based on phase and population."""
        factors = VDIFactors()
        w = self.weights
        
        # Population pressure (0 at 15%, 1 at 100%)
        pop_pressure = max(0, (population - 0.15) / 0.85)
        
        # Population comfort (1 at 0%, 0 at 25%)
        pop_comfort = max(0, (0.25 - population) / 0.25)
        
        # === Discomfort factors ===
        
        # Motion incoherence (BUSY+)
        if phase in (VisualPhase.BUSY, VisualPhase.CROWDED, VisualPhase.SATURATED):
            factors.motion_incoherence = w['motion_incoherence'] * pop_pressure
        elif phase == VisualPhase.OCCUPIED:
            factors.motion_incoherence = w['motion_incoherence'] * pop_pressure * 0.3
        
        # Visual density (OCCUPIED+)
        if phase in (VisualPhase.OCCUPIED, VisualPhase.BUSY, 
                     VisualPhase.CROWDED, VisualPhase.SATURATED):
            factors.visual_density = w['visual_density'] * pop_pressure * 0.8
        
        # Light diffusion (CROWDED+)
        if phase in (VisualPhase.CROWDED, VisualPhase.SATURATED):
            factors.light_diffusion = w['light_diffusion'] * pop_pressure
        elif phase == VisualPhase.BUSY:
            factors.light_diffusion = w['light_diffusion'] * pop_pressure * 0.3
        
        # Environmental wear (from accumulation)
        factors.environmental_wear = w['environmental_wear'] * self._accumulated_wear
        
        # Wildlife absence (from wildlife state)
        factors.wildlife_absence = w['wildlife_absence'] * (1.0 - self._wildlife_visibility)
        
        # NPC unease (CROWDED+)
        if phase in (VisualPhase.CROWDED, VisualPhase.SATURATED):
            factors.npc_unease = w['npc_unease'] * pop_pressure
        elif phase == VisualPhase.BUSY:
            factors.npc_unease = w['npc_unease'] * pop_pressure * 0.4
        
        # Spatial noise (SATURATED only)
        if phase == VisualPhase.SATURATED:
            factors.spatial_noise = w['spatial_noise'] * pop_pressure
        
        # === Comfort factors ===
        
        # Only active at low population (PRISTINE, HEALTHY)
        if phase in (VisualPhase.PRISTINE, VisualPhase.HEALTHY):
            factors.motion_coherence = w['motion_coherence'] * pop_comfort
            factors.visual_clarity = w['visual_clarity'] * pop_comfort
            factors.light_quality = w['light_quality'] * pop_comfort
            factors.spatial_invitation = w['spatial_invitation'] * pop_comfort
        
        # Environmental health (based on lack of wear)
        if self._accumulated_wear < 0.2:
            factors.environmental_health = (
                w['environmental_health'] * 
                (1.0 - self._accumulated_wear / 0.2) * 
                pop_comfort
            )
        
        # Wildlife presence (based on visibility)
        if self._wildlife_visibility > 0.5:
            factors.wildlife_presence = (
                w['wildlife_presence'] * 
                (self._wildlife_visibility - 0.5) * 2.0 * 
                pop_comfort
            )
        
        # NPC comfort (PRISTINE only)
        if phase == VisualPhase.PRISTINE:
            factors.npc_comfort = w['npc_comfort'] * pop_comfort
        
        return factors
    
    def _apply_smoothing(self, raw_vdi: float) -> float:
        """Apply exponential smoothing."""
        return self._smoothed_vdi + self.config.smoothing_factor * (raw_vdi - self._smoothed_vdi)
    
    def _calculate_target(self, population: float) -> float:
        """Calculate target VDI from population (for tuning reference)."""
        if population < 0.15:
            return -0.2  # Comfortable
        elif population < 0.35:
            return (population - 0.15) / 0.20 * 0.3 - 0.1  # Transition
        elif population < 0.70:
            return (population - 0.35) / 0.35 * 0.4 + 0.1  # Building
        else:
            return (population - 0.70) / 0.30 * 0.3 + 0.5  # Maximum
    
    def _categorize_delta(self, delta: float) -> str:
        """Categorize delta magnitude."""
        abs_delta = abs(delta)
        
        if abs_delta < self.DELTA_THRESHOLDS['small']:
            return "none"
        elif abs_delta < self.DELTA_THRESHOLDS['medium']:
            return "small"
        elif abs_delta < self.DELTA_THRESHOLDS['large']:
            return "medium"
        else:
            return "large"
    
    @property
    def current_vdi(self) -> float:
        """Get current smoothed VDI."""
        return self._smoothed_vdi
    
    @property
    def wildlife_state(self) -> WildlifeState:
        """Get current wildlife state."""
        return self._wildlife_state
    
    @property
    def accumulated_wear(self) -> float:
        """Get current accumulated wear."""
        return self._accumulated_wear
    
    def reset(self) -> None:
        """Reset calculator state."""
        self._smoothed_vdi = 0.0
        self._wildlife_state = WildlifeState.THRIVING
        self._wildlife_visibility = 1.0
        self._wildlife_transition_progress = 0.0
        self._accumulated_wear = 0.0
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        return f"""VDI Calculator State:
  Smoothed VDI: {self._smoothed_vdi:+.3f}
  Wildlife: {self._wildlife_state.value} (visibility: {self._wildlife_visibility:.0%})
  Wear: {self._accumulated_wear:.0%}
"""
