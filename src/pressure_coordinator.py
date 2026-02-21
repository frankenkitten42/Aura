"""
Pressure Coordinator - Couples LSE (Audio) and VDE (Visual) systems.

Manages the timing relationship between SDI and VDI to prevent
synchronized spikes that would reveal the manipulation to players.

Key principles:
1. SDI leads, VDI lags (5-15 seconds)
2. Recovery is slower than degradation
3. Never let both spike simultaneously
4. Cross-region attraction signals
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import math


@dataclass
class RegionPressure:
    """Pressure state for a single region."""
    region_id: str
    population: float = 0.0
    
    # Individual system values
    sdi: float = 0.0
    vdi: float = 0.0
    
    # Combined pressure
    combined_pressure: float = 0.0
    pressure_trend: str = "stable"  # rising, falling, stable
    
    # Timing state
    last_sdi_spike: float = 0.0
    last_vdi_spike: float = 0.0
    spike_blocked: bool = False
    
    # Attraction state
    broadcasting_attraction: bool = False
    receiving_attraction: float = 0.0


@dataclass 
class AttractionSignal:
    """Attraction signal from high-pressure to low-pressure region."""
    source_region: str
    target_region: str
    strength: float
    time_remaining: float


class PressureCoordinator:
    """
    Coordinates LSE and VDE to create organic environmental pressure.
    
    Manages:
    - Timing offsets between audio and visual discomfort
    - Anti-synchronization (prevents both spiking together)
    - Cross-region attraction broadcasting
    - Trend smoothing and hysteresis
    
    Example:
        >>> from engine import LSEEngine
        >>> from vde import VDEEngine
        >>> 
        >>> lse = LSEEngine(config_path="config/")
        >>> vde = VDEEngine(lse_engine=lse)
        >>> coordinator = PressureCoordinator(lse, vde)
        >>> 
        >>> # Each tick
        >>> coordinator.update(delta_time=0.5)
        >>> 
        >>> # Get combined state
        >>> state = coordinator.get_region_state("forest_clearing")
    """
    
    # Timing constants
    VDI_LAG_RISE = 8.0          # Seconds VDI lags SDI when rising
    VDI_LAG_FALL = 12.0         # Seconds VDI lags SDI when falling
    SPIKE_BLOCK_DURATION = 5.0  # Block VDI spike for N seconds after SDI spike
    
    # Thresholds
    SPIKE_THRESHOLD = 0.15      # Change per second to count as spike
    ATTRACTION_THRESHOLD = 0.35  # Pressure above this broadcasts attraction
    ATTRACTION_RANGE = 500.0    # Meters to broadcast
    ATTRACTION_DURATION = 30.0  # How long attraction lasts
    
    def __init__(self, lse_engine, vde_engine):
        """
        Initialize the coordinator.
        
        Args:
            lse_engine: LSEEngine instance
            vde_engine: VDEEngine instance
        """
        self.lse = lse_engine
        self.vde = vde_engine
        
        # Multi-region support (for future)
        self.regions: Dict[str, RegionPressure] = {}
        self.active_region = "default"
        
        # Initialize default region
        self.regions["default"] = RegionPressure(region_id="default")
        
        # Attraction signals
        self.attraction_signals: List[AttractionSignal] = []
        
        # History for trend detection
        self._sdi_history: List[Tuple[float, float]] = []
        self._vdi_history: List[Tuple[float, float]] = []
        self._current_time = 0.0
        
        # Anti-sync state
        self._last_sdi_spike_time = -100.0
        self._vdi_blocked_until = 0.0
    
    def update(self, delta_time: float, 
               region_id: str = "default") -> RegionPressure:
        """
        Update pressure coordination.
        
        Args:
            delta_time: Time since last update
            region_id: Which region to update
            
        Returns:
            Updated RegionPressure state
        """
        self._current_time += delta_time
        
        # Get or create region
        if region_id not in self.regions:
            self.regions[region_id] = RegionPressure(region_id=region_id)
        
        region = self.regions[region_id]
        
        # Get current values
        current_sdi = self.lse.sdi
        current_vdi = self.vde.vdi
        population = self.lse.environment.population_ratio
        
        # Record history
        self._sdi_history.append((self._current_time, current_sdi))
        self._vdi_history.append((self._current_time, current_vdi))
        self._cleanup_history()
        
        # Detect SDI spike
        sdi_rate = self._calculate_rate(self._sdi_history)
        if sdi_rate > self.SPIKE_THRESHOLD:
            self._last_sdi_spike_time = self._current_time
            self._vdi_blocked_until = self._current_time + self.SPIKE_BLOCK_DURATION
            region.last_sdi_spike = self._current_time
        
        # Check if VDI should be blocked
        region.spike_blocked = self._current_time < self._vdi_blocked_until
        
        # Apply VDI modulation if blocked
        if region.spike_blocked:
            # Hold VDI steady during SDI spike
            modulated_vdi = self._get_historical_vdi(self._last_sdi_spike_time)
        else:
            modulated_vdi = current_vdi
        
        # Update region state
        region.population = population
        region.sdi = current_sdi
        region.vdi = modulated_vdi
        region.combined_pressure = self._calculate_combined(current_sdi, modulated_vdi)
        region.pressure_trend = self._detect_trend()
        
        # Update attraction
        self._update_attraction(region, delta_time)
        
        return region
    
    def _calculate_rate(self, history: List[Tuple[float, float]]) -> float:
        """Calculate rate of change from history."""
        if len(history) < 2:
            return 0.0
        
        # Look at last 2 seconds
        recent = [(t, v) for t, v in history 
                  if t > self._current_time - 2.0]
        
        if len(recent) < 2:
            return 0.0
        
        time_span = recent[-1][0] - recent[0][0]
        if time_span <= 0:
            return 0.0
        
        value_change = recent[-1][1] - recent[0][1]
        return value_change / time_span
    
    def _get_historical_vdi(self, target_time: float) -> float:
        """Get VDI value from a specific time."""
        for time, vdi in reversed(self._vdi_history):
            if time <= target_time:
                return vdi
        return self.vde.vdi
    
    def _calculate_combined(self, sdi: float, vdi: float) -> float:
        """Calculate combined pressure value."""
        # Weighted combination (audio slightly more impactful)
        return sdi * 0.55 + vdi * 0.45
    
    def _detect_trend(self) -> str:
        """Detect pressure trend from history."""
        if len(self._sdi_history) < 10:
            return "stable"
        
        # Compare recent average to older average
        recent = [v for t, v in self._sdi_history[-10:]]
        older = [v for t, v in self._sdi_history[-20:-10]] if len(self._sdi_history) >= 20 else recent
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        diff = recent_avg - older_avg
        
        if diff > 0.05:
            return "rising"
        elif diff < -0.05:
            return "falling"
        else:
            return "stable"
    
    def _update_attraction(self, region: RegionPressure, 
                           delta_time: float) -> None:
        """Update attraction broadcasting/receiving."""
        # Check if should broadcast
        if region.combined_pressure > self.ATTRACTION_THRESHOLD:
            region.broadcasting_attraction = True
            # In multi-region system, would create AttractionSignals here
        else:
            region.broadcasting_attraction = False
        
        # Decay existing signals
        self.attraction_signals = [
            AttractionSignal(
                source_region=s.source_region,
                target_region=s.target_region,
                strength=s.strength,
                time_remaining=s.time_remaining - delta_time
            )
            for s in self.attraction_signals
            if s.time_remaining > delta_time
        ]
        
        # Calculate received attraction (would sum from multiple sources)
        region.receiving_attraction = sum(
            s.strength * (s.time_remaining / self.ATTRACTION_DURATION)
            for s in self.attraction_signals
            if s.target_region == region.region_id
        )
    
    def _cleanup_history(self) -> None:
        """Remove old history entries."""
        cutoff = self._current_time - 30.0
        self._sdi_history = [(t, v) for t, v in self._sdi_history if t > cutoff]
        self._vdi_history = [(t, v) for t, v in self._vdi_history if t > cutoff]
    
    def get_region_state(self, region_id: str = "default") -> RegionPressure:
        """Get current state for a region."""
        return self.regions.get(region_id, RegionPressure(region_id=region_id))
    
    def get_combined_pressure(self) -> float:
        """Get combined pressure for active region."""
        region = self.regions.get(self.active_region)
        return region.combined_pressure if region else 0.0
    
    def is_vdi_blocked(self) -> bool:
        """Check if VDI changes are currently blocked."""
        return self._current_time < self._vdi_blocked_until
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        region = self.regions.get(self.active_region, RegionPressure(region_id="none"))
        
        block_status = "BLOCKED" if region.spike_blocked else "active"
        
        return f"""
Pressure Coordinator Status:
  Region: {region.region_id}
  Population: {region.population*100:.0f}%
  
  Individual Systems:
    SDI (Audio): {region.sdi:+.3f}
    VDI (Visual): {region.vdi:+.3f} [{block_status}]
  
  Combined:
    Pressure: {region.combined_pressure:+.3f}
    Trend: {region.pressure_trend}
  
  Attraction:
    Broadcasting: {region.broadcasting_attraction}
    Receiving: {region.receiving_attraction:.2f}
  
  Timing:
    Last SDI spike: {self._last_sdi_spike_time:.1f}s
    VDI blocked until: {self._vdi_blocked_until:.1f}s
    Current time: {self._current_time:.1f}s
"""
    
    def reset(self) -> None:
        """Reset coordinator state."""
        self.regions.clear()
        self.regions["default"] = RegionPressure(region_id="default")
        self.attraction_signals.clear()
        self._sdi_history.clear()
        self._vdi_history.clear()
        self._current_time = 0.0
        self._last_sdi_spike_time = -100.0
        self._vdi_blocked_until = 0.0


class UnifiedPressureEngine:
    """
    Unified interface for the complete Environmental Pressure System.
    
    Combines:
    - LSE (Living Soundscape Engine) - Audio discomfort
    - VDE (Visual Discomfort Engine) - Visual discomfort
    - Pressure Coordinator - Timing and coupling
    
    Example:
        >>> from pressure_coordinator import UnifiedPressureEngine
        >>> 
        >>> engine = UnifiedPressureEngine(config_path="config/")
        >>> engine.set_population(0.45)
        >>> 
        >>> # Each tick
        >>> state = engine.tick(delta_time=0.5)
        >>> 
        >>> # Get outputs for UE5
        >>> audio_events = state['audio_events']
        >>> visual_params = state['visual_params']
        >>> combined_pressure = state['combined_pressure']
    """
    
    def __init__(self, config_path: str = "config/", seed: int = None):
        """
        Initialize the unified engine.
        
        Args:
            config_path: Path to LSE config directory
            seed: Random seed for reproducibility
        """
        # Import here to avoid circular imports
        import sys
        import os
        src_path = os.path.dirname(os.path.abspath(__file__))
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        from engine import LSEEngine
        from vde import VDEEngine
        
        self.lse = LSEEngine(config_path=config_path, seed=seed)
        self.vde = VDEEngine()
        self.coordinator = PressureCoordinator(self.lse, self.vde)
        
        self._simulation_time = 0.0
    
    def set_population(self, ratio: float) -> None:
        """Set population ratio (0.0 to 1.0)."""
        self.lse.set_population(ratio)
        self.vde.set_population(ratio)
    
    def set_environment(self, **kwargs) -> None:
        """Set environment parameters (biome_id, weather, time_of_day)."""
        self.lse.set_environment(**kwargs)
    
    def tick(self, delta_time: float = 0.5) -> Dict[str, Any]:
        """
        Run one simulation tick.
        
        Returns dict with:
        - audio_events: List of sound events from LSE
        - visual_params: Dict of visual parameters from VDE
        - sdi: Current SDI value
        - vdi: Current VDI value
        - combined_pressure: Combined pressure value
        - pressure_state: Full pressure coordinator state
        """
        self._simulation_time += delta_time
        
        # Update LSE (audio)
        audio_events = self.lse.tick(delta_time=delta_time)
        
        # Update VDE (visual) with population
        vde_state = self.vde.tick(
            delta_time=delta_time,
            population=self.lse.environment.population_ratio
        )
        
        # Update coordinator with current values
        pressure_state = self.coordinator.update(
            delta_time=delta_time
        )
        
        return {
            'audio_events': audio_events,
            'visual_params': {
                'post_process': vde_state.post_process.to_dict() if vde_state else {},
                'materials': vde_state.materials.to_dict() if vde_state else {},
                'spawning': vde_state.spawning.to_dict() if vde_state else {},
                'particles': vde_state.particles.to_dict() if vde_state else {},
                'motion': vde_state.motion.to_dict() if vde_state else {},
                'attraction': vde_state.attraction.to_dict() if vde_state else {},
            },
            'sdi': self.lse.sdi,
            'vdi': self.vde.vdi,
            'combined_pressure': pressure_state.combined_pressure,
            'pressure_trend': pressure_state.pressure_trend,
            'pressure_state': pressure_state,
            'simulation_time': self._simulation_time,
        }
    
    @property
    def sdi(self) -> float:
        """Current SDI (audio discomfort)."""
        return self.lse.sdi
    
    @property
    def vdi(self) -> float:
        """Current VDI (visual discomfort)."""
        return self.vde.vdi
    
    @property
    def combined_pressure(self) -> float:
        """Combined environmental pressure."""
        return self.coordinator.get_combined_pressure()
    
    def get_summary(self) -> str:
        """Get combined summary of all systems."""
        return f"""
╔══════════════════════════════════════════════════════════════╗
║          UNIFIED ENVIRONMENTAL PRESSURE SYSTEM               ║
╠══════════════════════════════════════════════════════════════╣
║  Simulation Time: {self._simulation_time:.1f}s
║  Population: {self.lse.environment.population_ratio*100:.0f}%
║
║  AUDIO (SDI):
║    Phase: {self.lse.pressure_phase.upper()}
║    Value: {self.lse.sdi:+.3f}
║    Target: {self.lse.sdi_result.target_sdi if self.lse.sdi_result else 0:+.3f}
║
║  VISUAL (VDI):
║    Phase: {self.vde.phase.value.upper()}
║    Value: {self.vde.vdi:+.3f}
║    Blocked: {self.coordinator.is_vdi_blocked()}
║
║  COMBINED:
║    Pressure: {self.combined_pressure:+.3f}
║    Trend: {self.coordinator.get_region_state().pressure_trend}
╚══════════════════════════════════════════════════════════════╝
"""
    
    def reset(self) -> None:
        """Reset all systems."""
        self.lse.reset()
        self.vde.reset()
        self.coordinator.reset()
        self._simulation_time = 0.0
