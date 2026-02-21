"""
Soundscape orchestration for the Living Soundscape Engine.

The Soundscape class is the main coordinator that:
- Decides when to add or remove sounds
- Coordinates with SDI calculations
- Manages the overall soundscape state
- Produces events for external playback systems
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
import uuid

from .sound_selector import SoundSelector, SelectionResult
from .layer_manager import LayerManager, ActiveSoundInfo


class EventType(Enum):
    """Types of soundscape events."""
    SOUND_START = "sound_start"
    SOUND_END = "sound_end"
    SOUND_INTERRUPT = "sound_interrupt"
    INTENSITY_CHANGE = "intensity_change"
    LAYER_FULL = "layer_full"
    SDI_ADJUSTMENT = "sdi_adjustment"


@dataclass
class SoundscapeEvent:
    """
    An event produced by the soundscape system.
    
    Events are consumed by external playback systems (e.g., UE5 MetaSounds).
    
    Attributes:
        event_type: Type of event
        timestamp: When the event occurred
        instance_id: Unique ID for the sound instance
        sound_id: The sound definition ID
        layer: Which layer this affects
        duration: Duration for SOUND_START events
        intensity: Playback intensity
        reason: Why this event occurred
        metadata: Additional event-specific data
    """
    event_type: EventType
    timestamp: float
    instance_id: str = ""
    sound_id: str = ""
    layer: str = ""
    duration: float = 0.0
    intensity: float = 0.5
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp,
            'instance_id': self.instance_id,
            'sound_id': self.sound_id,
            'layer': self.layer,
            'duration': self.duration,
            'intensity': self.intensity,
            'reason': self.reason,
            'metadata': self.metadata,
        }


@dataclass
class SoundscapeState:
    """Current state of the soundscape."""
    total_events: int = 0
    sounds_started: int = 0
    sounds_ended: int = 0
    sounds_interrupted: int = 0
    last_sdi: float = 0.0
    last_delta: float = 0.0
    last_delta_category: str = "none"


class Soundscape:
    """
    Main soundscape orchestration class.
    
    Coordinates between:
    - SoundSelector: Choosing which sounds to play
    - LayerManager: Tracking active sounds and capacity
    - SDI System: Adjusting behavior based on discomfort targets
    - Memory Systems: Tracking history for pattern/conflict detection
    
    Example:
        >>> soundscape = Soundscape(config, rng)
        >>> events = soundscape.tick(
        ...     current_time=100.0,
        ...     environment=env,
        ...     sound_memory=memory,
        ...     sdi_result=sdi_result
        ... )
        >>> for event in events:
        ...     if event.event_type == EventType.SOUND_START:
        ...         play_sound(event.sound_id, event.duration, event.intensity)
    """
    
    # Tick behavior settings
    MIN_TICK_INTERVAL = 0.5  # Minimum time between selection attempts
    
    # SDI-based behavior thresholds
    AGGRESSIVE_REDUCTION_THRESHOLD = -0.3  # Delta below this = aggressively reduce sounds
    AGGRESSIVE_ADDITION_THRESHOLD = 0.3    # Delta above this = aggressively add sounds
    
    def __init__(self, config: Optional[Any] = None, rng: Optional[Any] = None):
        """
        Initialize the soundscape.
        
        Args:
            config: LSEConfig object
            rng: SeededRNG for reproducible behavior
        """
        self.config = config
        self.rng = rng
        
        # Components
        self.selector = SoundSelector(config, rng)
        self.layer_manager = LayerManager(config)
        
        # State
        self.state = SoundscapeState()
        self._last_tick_time: float = 0.0
        self._pending_events: List[SoundscapeEvent] = []
        
        # Layer tick schedules (different layers update at different rates)
        self._layer_schedules: Dict[str, float] = {
            'background': 10.0,  # Check every 10 seconds
            'periodic': 2.0,     # Check every 2 seconds
            'reactive': 0.5,     # Check every 0.5 seconds
            'anomalous': 5.0,    # Check every 5 seconds
        }
        self._last_layer_tick: Dict[str, float] = {k: 0.0 for k in self._layer_schedules}
    
    def tick(self,
             current_time: float,
             environment: Any,
             sound_memory: Any,
             silence_tracker: Any,
             pattern_memory: Any,
             sdi_result: Optional[Any] = None,
             population_ratio: float = 0.0,
             pressure_state: Optional[Any] = None) -> List[SoundscapeEvent]:
        """
        Main tick function - update the soundscape.
        
        Args:
            current_time: Current simulation time
            environment: Current environment state
            sound_memory: Sound memory for history tracking
            silence_tracker: Silence tracker
            pattern_memory: Pattern memory
            sdi_result: Result from SDI calculation (if available)
            population_ratio: Current population ratio
            pressure_state: Population pressure state
            
        Returns:
            List of events to be processed by playback system
        """
        events = []
        
        # Get SDI info
        sdi_delta = 0.0
        delta_category = "none"
        if sdi_result:
            sdi_delta = sdi_result.delta
            delta_category = sdi_result.delta_category
            self.state.last_sdi = sdi_result.smoothed_sdi
            self.state.last_delta = sdi_delta
            self.state.last_delta_category = delta_category
        
        # Update biome capacity
        biome_params = getattr(environment, 'biome_parameters', None)
        if biome_params:
            self.layer_manager.set_biome_capacity(biome_params)
        
        # 1. Handle expired sounds
        expired_events = self._handle_expired_sounds(current_time, sound_memory)
        events.extend(expired_events)
        
        # 2. Update silence tracker
        active_count = self.layer_manager.get_active_count()
        non_background = active_count - self.layer_manager.get_active_count('background')
        silence_tracker.update(current_time, sound_count=non_background)
        
        # 3. Handle pressure-based discomfort sounds
        if pressure_state:
            pressure_events = self._handle_pressure_sounds(
                current_time, pressure_state, sound_memory
            )
            events.extend(pressure_events)
        
        # 4. Check if we need to aggressively adjust (only if not already pressured)
        if delta_category in ('large', 'critical') and not self._pressure_active(pressure_state):
            adjustment_events = self._handle_sdi_adjustment(
                current_time, sdi_delta, delta_category, sound_memory
            )
            events.extend(adjustment_events)
        
        # 5. Process each layer on its schedule
        for layer, schedule in self._layer_schedules.items():
            time_since = current_time - self._last_layer_tick[layer]
            
            if time_since >= schedule:
                layer_events = self._tick_layer(
                    layer=layer,
                    current_time=current_time,
                    environment=environment,
                    sound_memory=sound_memory,
                    pattern_memory=pattern_memory,
                    sdi_delta=sdi_delta,
                    delta_category=delta_category,
                    pressure_state=pressure_state,
                )
                events.extend(layer_events)
                self._last_layer_tick[layer] = current_time
        
        # 6. Record events
        self.state.total_events += len(events)
        self._last_tick_time = current_time
        
        return events
    
    def _handle_expired_sounds(self, current_time: float, 
                                sound_memory: Any) -> List[SoundscapeEvent]:
        """Handle sounds that have naturally ended."""
        events = []
        expired = self.layer_manager.cleanup_expired(current_time)
        
        for sound in expired:
            # Update sound memory
            if sound_memory:
                sound_memory.end_event(sound.instance_id, current_time)
            
            # Create end event
            event = SoundscapeEvent(
                event_type=EventType.SOUND_END,
                timestamp=current_time,
                instance_id=sound.instance_id,
                sound_id=sound.sound_id,
                layer=sound.layer,
                reason="natural_end",
            )
            events.append(event)
            self.state.sounds_ended += 1
        
        return events
    
    def _handle_sdi_adjustment(self, current_time: float, sdi_delta: float,
                                delta_category: str, 
                                sound_memory: Any) -> List[SoundscapeEvent]:
        """Handle aggressive SDI adjustments when delta is large."""
        events = []
        
        if sdi_delta < self.AGGRESSIVE_REDUCTION_THRESHOLD:
            # Need to reduce SDI - remove discomfort-causing sounds
            to_remove = self.layer_manager.get_sounds_to_reduce(count=1)
            
            for sound in to_remove:
                self.layer_manager.remove_sound(sound.instance_id)
                
                if sound_memory:
                    sound_memory.end_event(sound.instance_id, current_time)
                
                event = SoundscapeEvent(
                    event_type=EventType.SOUND_INTERRUPT,
                    timestamp=current_time,
                    instance_id=sound.instance_id,
                    sound_id=sound.sound_id,
                    layer=sound.layer,
                    reason=f"sdi_reduction (delta={sdi_delta:.2f})",
                )
                events.append(event)
                self.state.sounds_interrupted += 1
        
        # Note: aggressive addition is handled in _tick_layer with force_selection
        
        return events
    
    def _pressure_active(self, pressure_state: Any) -> bool:
        """Check if pressure system is actively adding discomfort."""
        if pressure_state is None:
            return False
        return pressure_state.discomfort_boost > 0.2
    
    def _handle_pressure_sounds(self, current_time: float, pressure_state: Any,
                                 sound_memory: Any) -> List[SoundscapeEvent]:
        """Handle pressure-based discomfort sounds."""
        events = []
        
        # Only process periodically (every 3 seconds)
        if not hasattr(self, '_last_pressure_tick'):
            self._last_pressure_tick = 0.0
        
        if current_time - self._last_pressure_tick < 3.0:
            return events
        
        self._last_pressure_tick = current_time
        
        # Import pressure system for sound definitions
        try:
            from .population_pressure import DISCOMFORT_SOUNDS, PressurePhase
        except ImportError:
            from audio.population_pressure import DISCOMFORT_SOUNDS, PressurePhase
        
        phase = pressure_state.phase
        
        # Map phase to available sounds
        phase_sounds = {
            PressurePhase.SUBTLE: ["subtle"],
            PressurePhase.MODERATE: ["subtle", "moderate"],
            PressurePhase.INTENSE: ["subtle", "moderate", "intense"],
            PressurePhase.CRITICAL: ["subtle", "moderate", "intense", "critical"],
        }
        
        if phase not in phase_sounds:
            return events
        
        # Get available discomfort sounds
        available_sounds = []
        for category in phase_sounds[phase]:
            available_sounds.extend(DISCOMFORT_SOUNDS.get(category, []))
        
        if not available_sounds:
            return events
        
        # Probability of adding discomfort sound based on boost level
        add_probability = pressure_state.discomfort_boost * 0.5
        
        if self.rng.random() > add_probability:
            return events
        
        # Select a sound randomly weighted by phase
        weights = []
        for sound in available_sounds:
            # Higher weight for sounds matching current phase severity
            tags = sound.get("tags", [])
            if phase.value in tags:
                weights.append(2.0)
            else:
                weights.append(1.0)
        
        # Weighted selection
        total = sum(weights)
        roll = self.rng.random() * total
        cumulative = 0
        selected_sound = available_sounds[0]
        
        for i, sound in enumerate(available_sounds):
            cumulative += weights[i]
            if roll <= cumulative:
                selected_sound = sound
                break
        
        # Check if this sound is on cooldown (using layer_manager)
        sound_id = selected_sound["id"]
        if self.layer_manager.has_active_sound(sound_id):
            return events
        
        # Create the sound event
        instance_id = str(uuid.uuid4())
        duration_range = selected_sound.get("duration", {"min": 5.0, "max": 15.0})
        duration = self.rng.uniform(duration_range["min"], duration_range["max"])
        
        intensity_range = selected_sound.get("intensity", {"min": 0.3, "max": 0.5})
        # Scale intensity by pressure boost
        base_intensity = self.rng.uniform(intensity_range["min"], intensity_range["max"])
        intensity = base_intensity * (0.5 + pressure_state.discomfort_boost * 0.5)
        intensity = min(1.0, intensity)
        
        layer = selected_sound.get("layer", "background")
        freq_band = selected_sound.get("frequency_band", "low")
        tags = selected_sound.get("tags", [])
        
        # Add to layer manager
        sound_info = ActiveSoundInfo(
            instance_id=instance_id,
            sound_id=sound_id,
            layer=layer,
            start_time=current_time,
            expected_end_time=current_time + duration,
            intensity=intensity,
            frequency_band=freq_band,
            is_continuous=False,
            tags=tags,
            sdi_contribution=selected_sound.get("sdi_contribution", 0.1),
        )
        
        success, _ = self.layer_manager.add_sound(sound_info)
        
        if success:
            event = SoundscapeEvent(
                event_type=EventType.SOUND_START,
                timestamp=current_time,
                instance_id=instance_id,
                sound_id=sound_id,
                layer=layer,
                duration=duration,
                intensity=intensity,
                reason=f"pressure_{phase.value}",
                metadata={"pressure_phase": phase.value, "sdi_contribution": selected_sound.get("sdi_contribution", 0.1)},
            )
            events.append(event)
            self.state.sounds_started += 1
        
        return events
    
    def _tick_layer(self, layer: str, current_time: float,
                    environment: Any, sound_memory: Any,
                    pattern_memory: Any, sdi_delta: float,
                    delta_category: str,
                    pressure_state: Any = None) -> List[SoundscapeEvent]:
        """Process a single layer tick."""
        events = []
        
        # Check if layer can accept more sounds
        if not self.layer_manager.can_add_sound(layer):
            return events
        
        # Should we force selection? (aggressive addition)
        force = (sdi_delta > self.AGGRESSIVE_ADDITION_THRESHOLD and 
                 delta_category in ('large', 'critical'))
        
        # Attempt selection
        result = self.selector.select(
            layer=layer,
            environment=environment,
            sound_memory=sound_memory,
            current_time=current_time,
            sdi_delta=sdi_delta,
            delta_category=delta_category,
            force_selection=force,
        )
        
        if result.selected:
            # Check wildlife suppression from pressure system
            if pressure_state and pressure_state.wildlife_suppression > 0:
                sound_config = self.selector.get_sound_config(result.sound_id)
                if sound_config:
                    tags = list(sound_config.tags) if sound_config.tags else []
                    wildlife_tags = ["bird", "fauna", "insect", "animal", "organic"]
                    is_wildlife = any(tag in wildlife_tags for tag in tags)
                    
                    if is_wildlife:
                        # Roll against suppression chance
                        if self.rng.random() < pressure_state.wildlife_suppression:
                            # Wildlife sound suppressed - animals have fled
                            return events
            
            # Add to layer manager
            sound_config = self.selector.get_sound_config(result.sound_id)
            tags = list(sound_config.tags) if sound_config else []
            freq_band = sound_config.frequency_band if sound_config else "mid"
            
            sound_info = ActiveSoundInfo(
                instance_id=result.instance_id,
                sound_id=result.sound_id,
                layer=layer,
                start_time=current_time,
                expected_end_time=current_time + result.duration,
                intensity=result.intensity,
                frequency_band=freq_band,
                is_continuous=False,
                tags=tags,
            )
            
            success, reason = self.layer_manager.add_sound(sound_info)
            
            if success:
                # Update memories
                if sound_memory:
                    # Create a SoundEvent-like object using the memory's own class
                    # Import at module level would cause circular imports, so we
                    # use duck typing - sound_memory.add_event accepts anything with
                    # the right attributes
                    class SoundEventData:
                        def __init__(self):
                            self.instance_id = result.instance_id
                            self.sound_id = result.sound_id
                            self.timestamp = current_time
                            self.layer = layer
                            self.intensity = result.intensity
                            self.frequency_band = freq_band
                            self.duration = result.duration
                            self.tags = tags
                            self.ended = False
                            self.end_time = None
                            self.end_type = None
                            self.sdi_contribution = 0.0
                        
                        @property
                        def expected_end_time(self):
                            return self.timestamp + self.duration
                        
                        def is_active_at(self, time):
                            if time < self.timestamp:
                                return False
                            if self.ended and self.end_time is not None:
                                return time < self.end_time
                            return time < self.expected_end_time
                        
                        def mark_ended(self, time, end_type=None):
                            self.ended = True
                            self.end_time = time
                            self.end_type = end_type
                        
                        def overstayed(self, current_time, natural_duration):
                            if natural_duration is None:
                                return 0.0
                            actual = current_time - self.timestamp
                            if actual > natural_duration * 1.5:
                                return actual - natural_duration
                            return 0.0
                        
                        def to_dict(self):
                            return {
                                'instance_id': self.instance_id,
                                'sound_id': self.sound_id,
                                'timestamp': self.timestamp,
                                'layer': self.layer,
                                'intensity': self.intensity,
                                'frequency_band': self.frequency_band,
                                'duration': self.duration,
                                'tags': self.tags,
                            }
                    
                    event_data = SoundEventData()
                    sound_memory.add_event(event_data)
                    
                    # Set cooldown
                    if sound_config:
                        cooldown = getattr(sound_config, 'cooldown', 5.0)
                        sound_memory.set_cooldown(
                            result.sound_id, 
                            current_time + cooldown
                        )
                
                if pattern_memory:
                    pattern_memory.record_occurrence(result.sound_id, current_time)
                
                # Create start event
                event = SoundscapeEvent(
                    event_type=EventType.SOUND_START,
                    timestamp=current_time,
                    instance_id=result.instance_id,
                    sound_id=result.sound_id,
                    layer=layer,
                    duration=result.duration,
                    intensity=result.intensity,
                    reason=result.reason,
                    metadata={
                        'candidates_considered': result.candidates_considered,
                        'sdi_delta': sdi_delta,
                    }
                )
                events.append(event)
                self.state.sounds_started += 1
        
        return events
    
    def force_start_sound(self, sound_id: str, current_time: float,
                          duration: Optional[float] = None,
                          intensity: Optional[float] = None) -> Optional[SoundscapeEvent]:
        """
        Force start a specific sound (for reactive/scripted events).
        
        Args:
            sound_id: The sound to start
            current_time: Current simulation time
            duration: Override duration (uses config if None)
            intensity: Override intensity (uses config if None)
            
        Returns:
            SoundscapeEvent if successful, None otherwise
        """
        sound_config = self.selector.get_sound_config(sound_id)
        if not sound_config:
            return None
        
        layer = sound_config.layer
        
        # Get duration and intensity
        if duration is None:
            dur_config = sound_config.duration
            if self.rng:
                duration = self.rng.uniform(dur_config.min, dur_config.max)
            else:
                duration = (dur_config.min + dur_config.max) / 2
        
        if intensity is None:
            int_config = sound_config.intensity
            if self.rng:
                intensity = self.rng.uniform(int_config.min, int_config.max)
            else:
                intensity = (int_config.min + int_config.max) / 2
        
        instance_id = str(uuid.uuid4())
        
        # Create sound info
        sound_info = ActiveSoundInfo(
            instance_id=instance_id,
            sound_id=sound_id,
            layer=layer,
            start_time=current_time,
            expected_end_time=current_time + duration,
            intensity=intensity,
            frequency_band=sound_config.frequency_band,
            is_continuous=(sound_config.duration.type == "continuous"),
            tags=list(sound_config.tags),
        )
        
        # Try to add (may need to interrupt)
        if self.layer_manager.layers[layer].is_full:
            # Interrupt lowest priority
            self.layer_manager.interrupt_oldest(layer)
        
        success, _ = self.layer_manager.add_sound(sound_info)
        
        if success:
            event = SoundscapeEvent(
                event_type=EventType.SOUND_START,
                timestamp=current_time,
                instance_id=instance_id,
                sound_id=sound_id,
                layer=layer,
                duration=duration,
                intensity=intensity,
                reason="forced_start",
            )
            self.state.sounds_started += 1
            return event
        
        return None
    
    def force_stop_sound(self, instance_id: str, 
                         current_time: float) -> Optional[SoundscapeEvent]:
        """
        Force stop a specific sound instance.
        
        Args:
            instance_id: The instance to stop
            current_time: Current simulation time
            
        Returns:
            SoundscapeEvent if successful, None otherwise
        """
        sound = self.layer_manager.remove_sound(instance_id)
        
        if sound:
            event = SoundscapeEvent(
                event_type=EventType.SOUND_INTERRUPT,
                timestamp=current_time,
                instance_id=instance_id,
                sound_id=sound.sound_id,
                layer=sound.layer,
                reason="forced_stop",
            )
            self.state.sounds_interrupted += 1
            return event
        
        return None
    
    def get_active_sounds(self) -> List[ActiveSoundInfo]:
        """Get all currently active sounds."""
        return self.layer_manager.get_all_active_sounds()
    
    def get_state(self) -> Dict[str, Any]:
        """Get current soundscape state."""
        return {
            'state': {
                'total_events': self.state.total_events,
                'sounds_started': self.state.sounds_started,
                'sounds_ended': self.state.sounds_ended,
                'sounds_interrupted': self.state.sounds_interrupted,
                'last_sdi': self.state.last_sdi,
                'last_delta': self.state.last_delta,
                'last_delta_category': self.state.last_delta_category,
            },
            'layers': self.layer_manager.get_summary(),
            'active_sounds': [
                {
                    'instance_id': s.instance_id,
                    'sound_id': s.sound_id,
                    'layer': s.layer,
                    'intensity': s.intensity,
                }
                for s in self.get_active_sounds()
            ],
        }
    
    def reset(self) -> None:
        """Reset the soundscape to initial state."""
        self.layer_manager.reset()
        self.state = SoundscapeState()
        self._last_tick_time = 0.0
        self._last_layer_tick = {k: 0.0 for k in self._layer_schedules}
    
    def __repr__(self) -> str:
        active = self.layer_manager.get_active_count()
        return f"Soundscape(active={active}, started={self.state.sounds_started})"
