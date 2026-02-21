"""
Main Living Soundscape Engine.

The LSEEngine is the top-level class that integrates all components:
- Configuration loading
- Memory systems (sound, silence, pattern)
- SDI calculation
- Sound selection and orchestration
- Event generation for external playback

This is the primary interface for game engine integration.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import time


@dataclass
class EnvironmentState:
    """
    Current environment state.
    
    Updated by the game engine to reflect player location and conditions.
    """
    biome_id: str = "forest"
    time_of_day: str = "day"
    weather: str = "clear"
    population_ratio: float = 0.0  # 0.0 = empty, 1.0 = max capacity
    features: Dict[str, bool] = field(default_factory=dict)
    
    # Biome parameters (loaded from config)
    biome_parameters: Optional[Any] = None
    
    def update(self, **kwargs) -> None:
        """Update environment state."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


@dataclass
class EngineStats:
    """Engine runtime statistics."""
    total_ticks: int = 0
    total_sounds_started: int = 0
    total_sounds_ended: int = 0
    total_sounds_interrupted: int = 0
    total_events: int = 0
    runtime_seconds: float = 0.0
    current_sdi: float = 0.0
    current_delta: float = 0.0
    active_sounds: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_ticks': self.total_ticks,
            'total_sounds_started': self.total_sounds_started,
            'total_sounds_ended': self.total_sounds_ended,
            'total_sounds_interrupted': self.total_sounds_interrupted,
            'total_events': self.total_events,
            'runtime_seconds': self.runtime_seconds,
            'current_sdi': self.current_sdi,
            'current_delta': self.current_delta,
            'active_sounds': self.active_sounds,
        }


class LSEEngine:
    """
    Main Living Soundscape Engine.
    
    Integrates all subsystems and provides a single interface for:
    - Running simulation ticks
    - Updating environment state
    - Receiving sound events
    - Inspecting engine state
    
    Example:
        >>> engine = LSEEngine(config_path="config/")
        >>> engine.set_environment(biome_id="forest", weather="rain")
        >>> engine.set_population(0.3)
        >>> 
        >>> while running:
        ...     events = engine.tick(delta_time=0.1)
        ...     for event in events:
        ...         play_sound(event)
    """
    
    def __init__(self, 
                 config_path: Optional[str] = None,
                 config: Optional[Any] = None,
                 seed: Optional[int] = None):
        """
        Initialize the engine.
        
        Args:
            config_path: Path to config directory (loads from JSON)
            config: Pre-loaded LSEConfig object
            seed: Random seed for reproducibility (None = random)
        """
        # Load configuration
        if config is not None:
            self.config = config
        elif config_path is not None:
            try:
                from .config import load_config
            except ImportError:
                from config import load_config
            self.config = load_config(config_path)
        else:
            raise ValueError("Must provide either config_path or config")
        
        # Initialize RNG
        try:
            from .utils.rng import SeededRNG
        except ImportError:
            from utils.rng import SeededRNG
        self.rng = SeededRNG(seed=seed)
        
        # Initialize memory systems
        try:
            from .memory import SoundMemory, SilenceTracker, PatternMemory
        except ImportError:
            from memory import SoundMemory, SilenceTracker, PatternMemory
        self.sound_memory = SoundMemory(retention_window=120.0)
        self.silence_tracker = SilenceTracker()
        self.pattern_memory = PatternMemory(retention_window=120.0)
        
        # Initialize SDI calculator
        try:
            from .sdi import SDICalculator
        except ImportError:
            from sdi import SDICalculator
        self.sdi_calculator = SDICalculator(self.config)
        
        # Initialize soundscape
        try:
            from .lse import Soundscape
        except ImportError:
            from lse import Soundscape
        self.soundscape = Soundscape(self.config, self.rng)
        
        # Initialize population pressure system
        try:
            from .lse.population_pressure import PopulationPressure
        except ImportError:
            from audio.population_pressure import PopulationPressure
        self.pressure = PopulationPressure()
        
        # Environment state
        self.environment = EnvironmentState()
        self._update_biome_params()
        
        # Timing
        self._simulation_time: float = 0.0
        self._real_start_time: float = time.time()
        self._last_sdi_result: Optional[Any] = None
        
        # Statistics
        self.stats = EngineStats()
        
        # Event callbacks
        self._event_callbacks: List[Callable] = []
        
        # Transition tracking
        self._recent_transitions: int = 0
        self._recent_resolutions: int = 0
    
    def _update_biome_params(self) -> None:
        """Update biome parameters from config."""
        biome_id = self.environment.biome_id
        if hasattr(self.config, 'biomes') and biome_id in self.config.biomes:
            biome = self.config.biomes[biome_id]
            self.environment.biome_parameters = biome.parameters
    
    # =========================================================================
    # Environment Control
    # =========================================================================
    
    def set_environment(self, **kwargs) -> None:
        """
        Update environment state.
        
        Args:
            biome_id: Current biome
            time_of_day: dawn/day/dusk/night
            weather: clear/rain/storm/fog/snow
            features: Dict of active features
        """
        old_biome = self.environment.biome_id
        self.environment.update(**kwargs)
        
        # Update biome params if biome changed
        if 'biome_id' in kwargs and kwargs['biome_id'] != old_biome:
            self._update_biome_params()
    
    def set_population(self, ratio: float) -> None:
        """
        Set current population ratio.
        
        Args:
            ratio: Population ratio (0.0 = empty, 1.0 = max capacity)
        """
        self.environment.population_ratio = max(0.0, min(1.0, ratio))
    
    def set_biome(self, biome_id: str) -> None:
        """Change the current biome."""
        self.set_environment(biome_id=biome_id)
    
    def set_weather(self, weather: str) -> None:
        """Change the current weather."""
        self.set_environment(weather=weather)
    
    def set_time_of_day(self, time_of_day: str) -> None:
        """Change the time of day."""
        self.set_environment(time_of_day=time_of_day)
    
    # =========================================================================
    # Main Tick
    # =========================================================================
    
    def tick(self, delta_time: float = 1.0) -> List[Any]:
        """
        Run one simulation tick.
        
        This is the main update function that should be called regularly
        (typically every 0.5-1.0 seconds).
        
        Args:
            delta_time: Time elapsed since last tick (seconds)
            
        Returns:
            List of SoundscapeEvents to be processed by playback system
        """
        self._simulation_time += delta_time
        self.stats.total_ticks += 1
        
        # 1. Update population pressure system
        self.pressure.update(self.environment.population_ratio)
        
        # 2. Calculate SDI
        sdi_result = self.sdi_calculator.calculate(
            sound_memory=self.sound_memory,
            silence_tracker=self.silence_tracker,
            pattern_memory=self.pattern_memory,
            environment=self.environment,
            current_time=self._simulation_time,
            population_ratio=self.environment.population_ratio,
            recent_transitions=self._recent_transitions,
            recent_resolutions=self._recent_resolutions,
            pressure_state=self.pressure.state,
        )
        self._last_sdi_result = sdi_result
        
        # Update stats
        self.stats.current_sdi = sdi_result.smoothed_sdi
        self.stats.current_delta = sdi_result.delta
        
        # 3. Run soundscape tick with pressure info
        events = self.soundscape.tick(
            current_time=self._simulation_time,
            environment=self.environment,
            sound_memory=self.sound_memory,
            silence_tracker=self.silence_tracker,
            pattern_memory=self.pattern_memory,
            sdi_result=sdi_result,
            population_ratio=self.environment.population_ratio,
            pressure_state=self.pressure.state,
        )
        
        # 3. Update statistics
        for event in events:
            self.stats.total_events += 1
            if event.event_type.value == "sound_start":
                self.stats.total_sounds_started += 1
            elif event.event_type.value == "sound_end":
                self.stats.total_sounds_ended += 1
            elif event.event_type.value == "sound_interrupt":
                self.stats.total_sounds_interrupted += 1
        
        self.stats.active_sounds = self.soundscape.layer_manager.get_active_count()
        self.stats.runtime_seconds = time.time() - self._real_start_time
        
        # 4. Cleanup old memory data periodically
        if self.stats.total_ticks % 60 == 0:
            self.sound_memory.cleanup(self._simulation_time)
            self.pattern_memory.cleanup(self._simulation_time)
        
        # 5. Call event callbacks
        for callback in self._event_callbacks:
            for event in events:
                callback(event)
        
        # 6. Decay transition/resolution counters
        self._recent_transitions = max(0, self._recent_transitions - 1)
        self._recent_resolutions = max(0, self._recent_resolutions - 1)
        
        return events
    
    # =========================================================================
    # Event Callbacks
    # =========================================================================
    
    def on_event(self, callback: Callable) -> None:
        """
        Register an event callback.
        
        The callback will be called for each event with the event as argument.
        
        Args:
            callback: Function that takes a SoundscapeEvent
        """
        self._event_callbacks.append(callback)
    
    def remove_callback(self, callback: Callable) -> None:
        """Remove an event callback."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    # =========================================================================
    # Manual Sound Control
    # =========================================================================
    
    def trigger_sound(self, sound_id: str, 
                      duration: Optional[float] = None,
                      intensity: Optional[float] = None) -> Optional[Any]:
        """
        Manually trigger a sound (for reactive/scripted events).
        
        Args:
            sound_id: The sound to play
            duration: Override duration
            intensity: Override intensity
            
        Returns:
            SoundscapeEvent if successful, None otherwise
        """
        event = self.soundscape.force_start_sound(
            sound_id=sound_id,
            current_time=self._simulation_time,
            duration=duration,
            intensity=intensity,
        )
        
        if event:
            self.stats.total_sounds_started += 1
            self.stats.total_events += 1
            
            for callback in self._event_callbacks:
                callback(event)
        
        return event
    
    def stop_sound(self, instance_id: str) -> Optional[Any]:
        """
        Manually stop a sound instance.
        
        Args:
            instance_id: The instance to stop
            
        Returns:
            SoundscapeEvent if successful, None otherwise
        """
        event = self.soundscape.force_stop_sound(
            instance_id=instance_id,
            current_time=self._simulation_time,
        )
        
        if event:
            self.stats.total_sounds_interrupted += 1
            self.stats.total_events += 1
            
            for callback in self._event_callbacks:
                callback(event)
        
        return event
    
    def notify_transition(self) -> None:
        """
        Notify the engine that a smooth transition occurred.
        
        Call this when a sound fades in/out smoothly to get comfort credit.
        """
        self._recent_transitions = min(5, self._recent_transitions + 1)
    
    def notify_resolution(self) -> None:
        """
        Notify the engine that tension resolved.
        
        Call this when a tense situation ends (storm passes, threat gone, etc.)
        """
        self._recent_resolutions = min(3, self._recent_resolutions + 1)
    
    # =========================================================================
    # State Inspection
    # =========================================================================
    
    @property
    def simulation_time(self) -> float:
        """Get current simulation time."""
        return self._simulation_time
    
    @property
    def sdi(self) -> float:
        """Get current smoothed SDI value."""
        return self.stats.current_sdi
    
    @property
    def sdi_delta(self) -> float:
        """Get current SDI delta (target - current)."""
        return self.stats.current_delta
    
    @property
    def sdi_result(self) -> Optional[Any]:
        """Get the full SDI calculation result."""
        return self._last_sdi_result
    
    def get_active_sounds(self) -> List[Any]:
        """Get list of currently active sounds."""
        return self.soundscape.get_active_sounds()
    
    def get_state(self) -> Dict[str, Any]:
        """Get complete engine state for inspection/logging."""
        return {
            'simulation_time': self._simulation_time,
            'environment': {
                'biome_id': self.environment.biome_id,
                'time_of_day': self.environment.time_of_day,
                'weather': self.environment.weather,
                'population_ratio': self.environment.population_ratio,
            },
            'sdi': {
                'current': self.stats.current_sdi,
                'delta': self.stats.current_delta,
                'target': self._last_sdi_result.target_sdi if self._last_sdi_result else 0.0,
            },
            'pressure': self.pressure.state.to_dict(),
            'soundscape': self.soundscape.get_state(),
            'stats': self.stats.to_dict(),
            'memory': {
                'sound_events': self.sound_memory.total_events,
                'active_sounds': self.sound_memory.active_count,
                'patterns_tracked': len(self.pattern_memory.get_all_patterns()),
                'silence_gaps': self.silence_tracker.total_gaps,
            },
        }
    
    def get_sdi_breakdown(self) -> Dict[str, float]:
        """Get detailed SDI factor breakdown."""
        if self._last_sdi_result is None:
            return {}
        return self._last_sdi_result.to_csv_row()
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    def reset(self) -> None:
        """Reset the engine to initial state."""
        self._simulation_time = 0.0
        self._real_start_time = time.time()
        self._last_sdi_result = None
        self._recent_transitions = 0
        self._recent_resolutions = 0
        
        self.sound_memory.clear()
        self.silence_tracker.reset()
        self.pattern_memory.clear()
        self.sdi_calculator.reset()
        self.soundscape.reset()
        self.pressure.reset()
        
        self.stats = EngineStats()
    
    @property
    def pressure_state(self):
        """Get current pressure state."""
        return self.pressure.state
    
    @property
    def pressure_phase(self) -> str:
        """Get current pressure phase name."""
        return self.pressure.state.phase.value
    
    def set_simulation_time(self, time: float) -> None:
        """Set simulation time (for save/load)."""
        self._simulation_time = time
    
    def __repr__(self) -> str:
        return (f"LSEEngine(time={self._simulation_time:.1f}s, "
                f"sdi={self.stats.current_sdi:.2f}, "
                f"active={self.stats.active_sounds})")
