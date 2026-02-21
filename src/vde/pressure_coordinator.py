"""
VDE Phase 8: Pressure Coordinator

The final integration layer that coordinates LSE (audio) and VDE (visual)
systems to create seamless environmental pressure.

Key principles:
1. Audio leads, visual follows (VDI lags SDI)
2. Never synchronize peaks (anti-sync logic)
3. Asymmetric rise/fall timing
4. Cross-region attraction broadcasting
5. Unified interface for game engine

This module handles:
- LSE/VDE coupling with configurable lag
- Timing offset management
- Anti-synchronization logic
- Cross-modal pressure balancing
- Holistic state management
- UE5-ready unified output
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from collections import deque
import math


# =============================================================================
# Enums and Constants
# =============================================================================

class PressurePhase(Enum):
    """Overall pressure phase combining SDI and VDI."""
    PRISTINE = "pristine"       # Low SDI, Low VDI
    AUDIO_LEADING = "audio_leading"   # High SDI, Low VDI (audio discomfort first)
    FULLY_PRESSURED = "fully_pressured"  # High SDI, High VDI
    VISUAL_TRAILING = "visual_trailing"  # Low SDI, High VDI (visual recovery lagging)
    RECOVERING = "recovering"    # Both falling


class SyncState(Enum):
    """Anti-synchronization state."""
    NORMAL = "normal"           # No sync concerns
    SDI_SPIKING = "sdi_spiking"     # SDI rising fast, hold VDI
    VDI_CATCHING = "vdi_catching"   # VDI catching up after hold
    DESYNC_ACTIVE = "desync_active"  # Actively preventing sync


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class PressureConfig:
    """Configuration for pressure coordinator."""
    
    # Lag timing (VDI follows SDI)
    vdi_lag_rise: float = 10.0      # Seconds for VDI to follow SDI up
    vdi_lag_fall: float = 15.0      # Seconds for VDI to follow SDI down
    
    # Smoothing rates
    sdi_smoothing: float = 0.15     # How fast SDI responds to population
    vdi_smoothing: float = 0.08     # How fast VDI responds (slower)
    
    # Anti-synchronization
    sync_threshold: float = 0.15    # SDI rate of change to trigger anti-sync
    sync_hold_duration: float = 2.0  # Seconds to hold VDI during spike
    sync_desync_offset: float = 0.1  # Target offset between SDI and VDI peaks
    
    # Pressure thresholds
    low_pressure_threshold: float = 0.25
    high_pressure_threshold: float = 0.50
    critical_pressure_threshold: float = 0.75
    
    # Cross-region
    attraction_broadcast_threshold: float = 0.30  # SDI/VDI level to broadcast
    attraction_radius: float = 1000.0  # cm
    
    # History tracking
    history_duration: float = 30.0   # Seconds of history to keep
    history_sample_rate: float = 0.5  # Samples per second


# =============================================================================
# Pressure History
# =============================================================================

@dataclass
class PressureSample:
    """A single pressure sample."""
    timestamp: float
    population: float
    sdi: float
    vdi: float
    phase: PressurePhase


class PressureHistory:
    """Tracks pressure history for analysis."""
    
    def __init__(self, duration: float = 30.0, sample_rate: float = 0.5):
        """
        Initialize pressure history.
        
        Args:
            duration: How long to keep history (seconds)
            sample_rate: Samples per second
        """
        self.duration = duration
        self.sample_rate = sample_rate
        self.samples: deque = deque()
        self._last_sample_time = 0.0
    
    def add_sample(self, timestamp: float, population: float, 
                   sdi: float, vdi: float, phase: PressurePhase) -> None:
        """Add a pressure sample if enough time has passed."""
        if timestamp - self._last_sample_time < 1.0 / self.sample_rate:
            return
        
        self.samples.append(PressureSample(
            timestamp=timestamp,
            population=population,
            sdi=sdi,
            vdi=vdi,
            phase=phase,
        ))
        self._last_sample_time = timestamp
        
        # Prune old samples
        cutoff = timestamp - self.duration
        while self.samples and self.samples[0].timestamp < cutoff:
            self.samples.popleft()
    
    def get_sdi_rate_of_change(self, window: float = 2.0) -> float:
        """Calculate SDI rate of change over recent window."""
        if len(self.samples) < 2:
            return 0.0
        
        recent = [s for s in self.samples if s.timestamp > self.samples[-1].timestamp - window]
        if len(recent) < 2:
            return 0.0
        
        sdi_diff = recent[-1].sdi - recent[0].sdi
        time_diff = recent[-1].timestamp - recent[0].timestamp
        
        if time_diff == 0:
            return 0.0
        
        return sdi_diff / time_diff
    
    def get_average_pressure(self, window: float = 5.0) -> Tuple[float, float]:
        """Get average SDI and VDI over window."""
        if not self.samples:
            return 0.0, 0.0
        
        recent = [s for s in self.samples if s.timestamp > self.samples[-1].timestamp - window]
        if not recent:
            return 0.0, 0.0
        
        avg_sdi = sum(s.sdi for s in recent) / len(recent)
        avg_vdi = sum(s.vdi for s in recent) / len(recent)
        
        return avg_sdi, avg_vdi
    
    def get_peak_pressure(self, window: float = 10.0) -> Tuple[float, float]:
        """Get peak SDI and VDI over window."""
        if not self.samples:
            return 0.0, 0.0
        
        recent = [s for s in self.samples if s.timestamp > self.samples[-1].timestamp - window]
        if not recent:
            return 0.0, 0.0
        
        peak_sdi = max(s.sdi for s in recent)
        peak_vdi = max(s.vdi for s in recent)
        
        return peak_sdi, peak_vdi
    
    def clear(self) -> None:
        """Clear history."""
        self.samples.clear()
        self._last_sample_time = 0.0


# =============================================================================
# Pressure State
# =============================================================================

@dataclass
class RegionPressureState:
    """Pressure state for a single region."""
    region_id: str
    
    # Population
    population: float = 0.0
    population_target: float = 0.0
    
    # Discomfort indices
    sdi: float = 0.0           # Soundscape Discomfort Index
    sdi_target: float = 0.0
    vdi: float = 0.0           # Visual Discomfort Index
    vdi_target: float = 0.0
    vdi_lagged: float = 0.0    # VDI after lag applied
    
    # Phase
    phase: PressurePhase = PressurePhase.PRISTINE
    
    # Anti-sync
    sync_state: SyncState = SyncState.NORMAL
    sync_hold_timer: float = 0.0
    
    # History
    history: PressureHistory = field(default_factory=PressureHistory)
    
    # Derived
    combined_pressure: float = 0.0  # Weighted combination
    pressure_differential: float = 0.0  # SDI - VDI (positive = audio leading)
    
    # Position
    position: Tuple[float, float] = (0.0, 0.0)


@dataclass
class PressureSnapshot:
    """Snapshot of pressure coordinator state."""
    region_id: str
    timestamp: float = 0.0
    
    # Population
    population: float = 0.0
    
    # Indices
    sdi: float = 0.0
    vdi: float = 0.0
    vdi_lagged: float = 0.0
    
    # Phase
    phase: PressurePhase = PressurePhase.PRISTINE
    sync_state: SyncState = SyncState.NORMAL
    
    # Derived
    combined_pressure: float = 0.0
    pressure_differential: float = 0.0
    
    # History metrics
    sdi_rate_of_change: float = 0.0
    avg_sdi: float = 0.0
    avg_vdi: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'region_id': self.region_id,
            'timestamp': self.timestamp,
            'population': self.population,
            'sdi': self.sdi,
            'vdi': self.vdi,
            'vdi_lagged': self.vdi_lagged,
            'phase': self.phase.value,
            'sync_state': self.sync_state.value,
            'combined_pressure': self.combined_pressure,
            'pressure_differential': self.pressure_differential,
            'sdi_rate_of_change': self.sdi_rate_of_change,
        }


# =============================================================================
# Region Pressure Manager
# =============================================================================

class RegionPressureManager:
    """
    Manages pressure coordination for a single region.
    
    Coordinates SDI and VDI with appropriate lag, anti-sync logic,
    and phase tracking.
    
    Example:
        >>> manager = RegionPressureManager("forest_clearing")
        >>> manager.set_population(0.65)
        >>> 
        >>> snapshot = manager.update(delta_time=0.5)
        >>> print(snapshot.phase)  # PressurePhase.AUDIO_LEADING
    """
    
    def __init__(self, region_id: str,
                 config: Optional[PressureConfig] = None,
                 position: Tuple[float, float] = (0.0, 0.0)):
        """
        Initialize region pressure manager.
        
        Args:
            region_id: Unique identifier for the region
            config: Pressure configuration
            position: Region position for cross-region calculations
        """
        self.region_id = region_id
        self.config = config or PressureConfig()
        
        # State
        self.state = RegionPressureState(
            region_id=region_id,
            position=position,
            history=PressureHistory(
                duration=self.config.history_duration,
                sample_rate=self.config.history_sample_rate,
            ),
        )
        
        self._time = 0.0
        
        # External system references (optional callbacks)
        self._sdi_callback: Optional[Callable[[float], float]] = None
        self._vdi_callback: Optional[Callable[[float], float]] = None
    
    def set_sdi_callback(self, callback: Callable[[float], float]) -> None:
        """Set callback to calculate SDI from population."""
        self._sdi_callback = callback
    
    def set_vdi_callback(self, callback: Callable[[float], float]) -> None:
        """Set callback to calculate VDI from population."""
        self._vdi_callback = callback
    
    def set_population(self, population: float) -> None:
        """Set current population ratio (0.0 to 1.0)."""
        self.state.population_target = max(0.0, min(1.0, population))
    
    def update(self, delta_time: float) -> PressureSnapshot:
        """
        Update pressure state for one tick.
        
        Args:
            delta_time: Time since last update in seconds
            
        Returns:
            Current pressure snapshot
        """
        self._time += delta_time
        cfg = self.config
        state = self.state
        
        # Smooth population
        pop_diff = state.population_target - state.population
        state.population += pop_diff * min(1.0, delta_time * 2.0)
        
        # Calculate target SDI and VDI
        if self._sdi_callback:
            state.sdi_target = self._sdi_callback(state.population)
        else:
            state.sdi_target = self._default_sdi(state.population)
        
        if self._vdi_callback:
            state.vdi_target = self._vdi_callback(state.population)
        else:
            state.vdi_target = self._default_vdi(state.population)
        
        # Update SDI (fast response)
        sdi_diff = state.sdi_target - state.sdi
        state.sdi += sdi_diff * min(1.0, delta_time * cfg.sdi_smoothing * 10)
        
        # Check for SDI spike (anti-sync)
        sdi_rate = state.history.get_sdi_rate_of_change()
        self._update_sync_state(sdi_rate, delta_time)
        
        # Update VDI with lag (slow response)
        if state.sync_state == SyncState.SDI_SPIKING:
            # Hold VDI during SDI spike
            state.sync_hold_timer -= delta_time
        else:
            # Apply lagged VDI update
            vdi_diff = state.vdi_target - state.vdi
            
            # Asymmetric timing
            if vdi_diff > 0:
                lag_rate = 1.0 / cfg.vdi_lag_rise
            else:
                lag_rate = 1.0 / cfg.vdi_lag_fall
            
            state.vdi += vdi_diff * min(1.0, delta_time * lag_rate)
        
        # Calculate lagged VDI (additional smoothing)
        lag_diff = state.vdi - state.vdi_lagged
        state.vdi_lagged += lag_diff * min(1.0, delta_time * cfg.vdi_smoothing * 10)
        
        # Update phase
        state.phase = self._determine_phase()
        
        # Calculate derived values
        state.combined_pressure = (state.sdi + state.vdi_lagged) / 2.0
        state.pressure_differential = state.sdi - state.vdi_lagged
        
        # Record history
        state.history.add_sample(
            timestamp=self._time,
            population=state.population,
            sdi=state.sdi,
            vdi=state.vdi_lagged,
            phase=state.phase,
        )
        
        return self._create_snapshot()
    
    def _default_sdi(self, population: float) -> float:
        """Default SDI calculation."""
        # Simple mapping: population directly affects SDI
        # Comfortable below 30%, uncomfortable above 60%
        if population < 0.30:
            return (population - 0.30) * 0.5  # Negative (comfortable)
        else:
            return (population - 0.30) * 1.0  # Positive (uncomfortable)
    
    def _default_vdi(self, population: float) -> float:
        """Default VDI calculation."""
        # VDI tracks similarly but with different curve
        if population < 0.25:
            return (population - 0.25) * 0.6
        else:
            return (population - 0.25) * 0.9
    
    def _update_sync_state(self, sdi_rate: float, delta_time: float) -> None:
        """Update anti-synchronization state."""
        cfg = self.config
        state = self.state
        
        if state.sync_state == SyncState.SDI_SPIKING:
            if state.sync_hold_timer <= 0:
                state.sync_state = SyncState.VDI_CATCHING
        elif state.sync_state == SyncState.VDI_CATCHING:
            # Check if VDI has caught up enough
            if abs(state.sdi - state.vdi) < cfg.sync_desync_offset:
                state.sync_state = SyncState.NORMAL
        else:
            # Check for new spike
            if sdi_rate > cfg.sync_threshold:
                state.sync_state = SyncState.SDI_SPIKING
                state.sync_hold_timer = cfg.sync_hold_duration
    
    def _determine_phase(self) -> PressurePhase:
        """Determine current pressure phase."""
        cfg = self.config
        state = self.state
        
        sdi_high = state.sdi > cfg.high_pressure_threshold
        vdi_high = state.vdi_lagged > cfg.high_pressure_threshold
        sdi_low = state.sdi < cfg.low_pressure_threshold
        vdi_low = state.vdi_lagged < cfg.low_pressure_threshold
        
        if sdi_low and vdi_low:
            return PressurePhase.PRISTINE
        elif sdi_high and vdi_low:
            return PressurePhase.AUDIO_LEADING
        elif sdi_high and vdi_high:
            return PressurePhase.FULLY_PRESSURED
        elif sdi_low and vdi_high:
            return PressurePhase.VISUAL_TRAILING
        else:
            return PressurePhase.RECOVERING
    
    def _create_snapshot(self) -> PressureSnapshot:
        """Create a snapshot of current pressure state."""
        state = self.state
        avg_sdi, avg_vdi = state.history.get_average_pressure()
        
        return PressureSnapshot(
            region_id=self.region_id,
            timestamp=self._time,
            population=state.population,
            sdi=state.sdi,
            vdi=state.vdi,
            vdi_lagged=state.vdi_lagged,
            phase=state.phase,
            sync_state=state.sync_state,
            combined_pressure=state.combined_pressure,
            pressure_differential=state.pressure_differential,
            sdi_rate_of_change=state.history.get_sdi_rate_of_change(),
            avg_sdi=avg_sdi,
            avg_vdi=avg_vdi,
        )
    
    def reset(self) -> None:
        """Reset pressure state."""
        self.state.population = 0.0
        self.state.population_target = 0.0
        self.state.sdi = 0.0
        self.state.sdi_target = 0.0
        self.state.vdi = 0.0
        self.state.vdi_target = 0.0
        self.state.vdi_lagged = 0.0
        self.state.phase = PressurePhase.PRISTINE
        self.state.sync_state = SyncState.NORMAL
        self.state.sync_hold_timer = 0.0
        self.state.combined_pressure = 0.0
        self.state.pressure_differential = 0.0
        self.state.history.clear()
        self._time = 0.0
    
    @property
    def sdi(self) -> float:
        """Current SDI."""
        return self.state.sdi
    
    @property
    def vdi(self) -> float:
        """Current VDI (lagged)."""
        return self.state.vdi_lagged
    
    @property
    def phase(self) -> PressurePhase:
        """Current pressure phase."""
        return self.state.phase


# =============================================================================
# Global Pressure Coordinator
# =============================================================================

class PressureCoordinator:
    """
    Coordinates pressure across all regions.
    
    Manages multiple RegionPressureManagers and handles cross-region
    attraction broadcasting.
    
    Example:
        >>> coordinator = PressureCoordinator()
        >>> coordinator.add_region("marketplace", position=(0, 0))
        >>> coordinator.add_region("forest", position=(800, 0))
        >>> 
        >>> coordinator.set_population("marketplace", 0.85)
        >>> coordinator.set_population("forest", 0.10)
        >>> 
        >>> snapshots = coordinator.update(delta_time=0.5)
        >>> # Forest receives attraction boost from marketplace overflow
    """
    
    def __init__(self, config: Optional[PressureConfig] = None):
        """
        Initialize pressure coordinator.
        
        Args:
            config: Shared pressure configuration
        """
        self.config = config or PressureConfig()
        self.regions: Dict[str, RegionPressureManager] = {}
        self._time = 0.0
        
        # Cross-region attraction state
        self._attraction_targets: Dict[str, float] = {}
    
    def add_region(self, region_id: str,
                   position: Tuple[float, float] = (0.0, 0.0)) -> None:
        """Add a region to coordinate."""
        self.regions[region_id] = RegionPressureManager(
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
    
    def set_sdi_callback(self, region_id: str, 
                         callback: Callable[[float], float]) -> None:
        """Set SDI calculation callback for a region."""
        if region_id in self.regions:
            self.regions[region_id].set_sdi_callback(callback)
    
    def set_vdi_callback(self, region_id: str,
                         callback: Callable[[float], float]) -> None:
        """Set VDI calculation callback for a region."""
        if region_id in self.regions:
            self.regions[region_id].set_vdi_callback(callback)
    
    def update(self, delta_time: float) -> Dict[str, PressureSnapshot]:
        """
        Update all regions.
        
        Args:
            delta_time: Time since last update in seconds
            
        Returns:
            Snapshots for all regions
        """
        self._time += delta_time
        
        # Update each region
        snapshots = {}
        for region_id, manager in self.regions.items():
            snapshots[region_id] = manager.update(delta_time)
        
        # Calculate cross-region attraction
        self._calculate_attraction()
        
        return snapshots
    
    def _calculate_attraction(self) -> None:
        """Calculate attraction targets based on pressure differential."""
        cfg = self.config
        self._attraction_targets.clear()
        
        # Find regions broadcasting attraction (high pressure)
        broadcasting = []
        for region_id, manager in self.regions.items():
            if (manager.sdi > cfg.attraction_broadcast_threshold or 
                manager.vdi > cfg.attraction_broadcast_threshold):
                broadcasting.append(region_id)
        
        # Calculate attraction for each region
        for target_id, target_mgr in self.regions.items():
            if target_mgr.state.combined_pressure > cfg.high_pressure_threshold:
                # High pressure regions don't receive attraction
                self._attraction_targets[target_id] = 0.0
                continue
            
            total_attraction = 0.0
            
            for source_id in broadcasting:
                if source_id == target_id:
                    continue
                
                source_mgr = self.regions[source_id]
                
                # Calculate distance
                dx = target_mgr.state.position[0] - source_mgr.state.position[0]
                dy = target_mgr.state.position[1] - source_mgr.state.position[1]
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance > cfg.attraction_radius:
                    continue
                
                # Calculate attraction based on pressure differential and distance
                pressure_diff = source_mgr.state.combined_pressure - target_mgr.state.combined_pressure
                if pressure_diff <= 0:
                    continue
                
                distance_factor = 1.0 - (distance / cfg.attraction_radius)
                attraction = pressure_diff * distance_factor * 0.5
                total_attraction += attraction
            
            self._attraction_targets[target_id] = min(1.0, total_attraction)
    
    def get_attraction(self, region_id: str) -> float:
        """Get attraction boost for a region."""
        return self._attraction_targets.get(region_id, 0.0)
    
    def get_highest_pressure_region(self) -> Optional[str]:
        """Get region with highest combined pressure."""
        if not self.regions:
            return None
        
        return max(
            self.regions.keys(),
            key=lambda r: self.regions[r].state.combined_pressure
        )
    
    def get_lowest_pressure_region(self) -> Optional[str]:
        """Get region with lowest combined pressure."""
        if not self.regions:
            return None
        
        return min(
            self.regions.keys(),
            key=lambda r: self.regions[r].state.combined_pressure
        )
    
    def get_pressure_map(self) -> Dict[str, float]:
        """Get combined pressure for all regions."""
        return {
            region_id: manager.state.combined_pressure
            for region_id, manager in self.regions.items()
        }
    
    def get_phase_map(self) -> Dict[str, PressurePhase]:
        """Get pressure phase for all regions."""
        return {
            region_id: manager.phase
            for region_id, manager in self.regions.items()
        }
    
    def reset(self) -> None:
        """Reset all regions."""
        for manager in self.regions.values():
            manager.reset()
        self._attraction_targets.clear()
        self._time = 0.0
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Generate complete UE5 JSON payload."""
        highest = self.get_highest_pressure_region()
        lowest = self.get_lowest_pressure_region()
        
        return {
            'Timestamp': self._time,
            'Regions': {
                region_id: {
                    'Population': manager.state.population,
                    'SDI': manager.sdi,
                    'VDI': manager.vdi,
                    'Phase': manager.phase.value,
                    'SyncState': manager.state.sync_state.value,
                    'CombinedPressure': manager.state.combined_pressure,
                    'PressureDifferential': manager.state.pressure_differential,
                    'AttractionBoost': self._attraction_targets.get(region_id, 0.0),
                }
                for region_id, manager in self.regions.items()
            },
            'HighestPressureRegion': highest,
            'LowestPressureRegion': lowest,
            'PressureMap': self.get_pressure_map(),
            'AttractionMap': dict(self._attraction_targets),
        }


# =============================================================================
# UE5 Parameters
# =============================================================================

@dataclass
class FPressureParameters:
    """UE5-ready pressure coordination parameters."""
    
    # Indices
    sdi: float = 0.0
    vdi: float = 0.0
    vdi_lagged: float = 0.0
    
    # Phase
    phase: str = "pristine"
    sync_state: str = "normal"
    
    # Derived
    combined_pressure: float = 0.0
    pressure_differential: float = 0.0
    
    # Cross-region
    attraction_boost: float = 0.0
    
    # Flags for systems
    should_broadcast_attraction: bool = False
    is_fully_pressured: bool = False
    is_recovering: bool = False
    audio_leading: bool = False
    visual_trailing: bool = False
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export as JSON for UE5."""
        return {
            'Pressure_SDI': self.sdi,
            'Pressure_VDI': self.vdi,
            'Pressure_VDI_Lagged': self.vdi_lagged,
            'Pressure_Phase': self.phase,
            'Pressure_SyncState': self.sync_state,
            'Pressure_Combined': self.combined_pressure,
            'Pressure_Differential': self.pressure_differential,
            'Pressure_AttractionBoost': self.attraction_boost,
            'Flag_ShouldBroadcastAttraction': self.should_broadcast_attraction,
            'Flag_IsFullyPressured': self.is_fully_pressured,
            'Flag_IsRecovering': self.is_recovering,
            'Flag_AudioLeading': self.audio_leading,
            'Flag_VisualTrailing': self.visual_trailing,
        }
    
    @classmethod
    def from_manager(cls, manager: RegionPressureManager, 
                     attraction: float = 0.0) -> 'FPressureParameters':
        """Create parameters from pressure manager state."""
        params = cls()
        state = manager.state
        cfg = manager.config
        
        params.sdi = state.sdi
        params.vdi = state.vdi
        params.vdi_lagged = state.vdi_lagged
        params.phase = state.phase.value
        params.sync_state = state.sync_state.value
        params.combined_pressure = state.combined_pressure
        params.pressure_differential = state.pressure_differential
        params.attraction_boost = attraction
        
        # Flags
        params.should_broadcast_attraction = (
            state.sdi > cfg.attraction_broadcast_threshold or
            state.vdi_lagged > cfg.attraction_broadcast_threshold
        )
        params.is_fully_pressured = state.phase == PressurePhase.FULLY_PRESSURED
        params.is_recovering = state.phase == PressurePhase.RECOVERING
        params.audio_leading = state.phase == PressurePhase.AUDIO_LEADING
        params.visual_trailing = state.phase == PressurePhase.VISUAL_TRAILING
        
        return params


# =============================================================================
# Scenario Simulator
# =============================================================================

class ScenarioSimulator:
    """
    Simulates pressure scenarios for testing and demonstration.
    
    Recreates the example scenarios from the design document.
    """
    
    @staticmethod
    def simulate_crowding(coordinator: PressureCoordinator, 
                          region_id: str,
                          duration: float = 300.0,
                          peak_population: float = 0.85,
                          ramp_duration: float = 240.0) -> List[PressureSnapshot]:
        """
        Simulate gradual crowding scenario.
        
        Args:
            coordinator: Pressure coordinator
            region_id: Region to simulate
            duration: Total simulation duration
            peak_population: Maximum population to reach
            ramp_duration: Time to reach peak
            
        Returns:
            List of pressure snapshots
        """
        snapshots = []
        dt = 0.5
        
        for t in range(int(duration / dt)):
            time = t * dt
            
            # Calculate population ramp
            if time < ramp_duration:
                pop = 0.10 + (peak_population - 0.10) * (time / ramp_duration)
            else:
                pop = peak_population
            
            coordinator.set_population(region_id, pop)
            result = coordinator.update(dt)
            
            if region_id in result:
                snapshots.append(result[region_id])
        
        return snapshots
    
    @staticmethod
    def simulate_dispersal(coordinator: PressureCoordinator,
                           region_id: str,
                           duration: float = 480.0,
                           start_population: float = 0.90,
                           end_population: float = 0.15,
                           ramp_duration: float = 360.0) -> List[PressureSnapshot]:
        """
        Simulate dispersal after event scenario.
        
        Args:
            coordinator: Pressure coordinator
            region_id: Region to simulate
            duration: Total simulation duration
            start_population: Initial population
            end_population: Final population
            ramp_duration: Time to reach end
            
        Returns:
            List of pressure snapshots
        """
        snapshots = []
        dt = 0.5
        
        # Initialize at high pressure
        coordinator.set_population(region_id, start_population)
        for _ in range(20):
            coordinator.update(dt)
        
        for t in range(int(duration / dt)):
            time = t * dt
            
            # Calculate population drop
            if time < ramp_duration:
                pop = start_population - (start_population - end_population) * (time / ramp_duration)
            else:
                pop = end_population
            
            coordinator.set_population(region_id, pop)
            result = coordinator.update(dt)
            
            if region_id in result:
                snapshots.append(result[region_id])
        
        return snapshots
