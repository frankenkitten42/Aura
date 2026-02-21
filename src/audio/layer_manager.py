"""
Layer management for the Living Soundscape Engine.

Manages the active sounds in each layer, enforces capacity limits,
and handles sound lifecycle (starting, ending, interrupting).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum


class LayerType(Enum):
    """Sound layer types with their characteristics."""
    BACKGROUND = "background"  # Continuous ambient sounds
    PERIODIC = "periodic"      # Interval-based sounds
    REACTIVE = "reactive"      # Event-triggered sounds
    ANOMALOUS = "anomalous"    # Rare/context-breaking sounds


@dataclass
class ActiveSoundInfo:
    """Information about an active sound in a layer."""
    instance_id: str
    sound_id: str
    layer: str
    start_time: float
    expected_end_time: float
    intensity: float
    frequency_band: str
    is_continuous: bool
    priority: float = 1.0
    tags: List[str] = field(default_factory=list)
    sdi_contribution: float = 0.0
    
    def time_remaining(self, current_time: float) -> float:
        """Get time remaining for this sound."""
        if self.is_continuous:
            return float('inf')
        return max(0.0, self.expected_end_time - current_time)
    
    def is_expired(self, current_time: float) -> bool:
        """Check if this sound has expired."""
        if self.is_continuous:
            return False
        return current_time >= self.expected_end_time


@dataclass
class LayerState:
    """
    State of a single layer.
    
    Attributes:
        layer_type: Type of this layer
        capacity: Maximum concurrent sounds
        active_sounds: Currently active sounds
        total_started: Total sounds started in this layer
        total_ended: Total sounds ended
    """
    layer_type: str
    capacity: int
    active_sounds: Dict[str, ActiveSoundInfo] = field(default_factory=dict)
    total_started: int = 0
    total_ended: int = 0
    
    @property
    def count(self) -> int:
        """Get current number of active sounds."""
        return len(self.active_sounds)
    
    @property
    def is_full(self) -> bool:
        """Check if layer is at capacity."""
        return self.count >= self.capacity
    
    @property
    def available_slots(self) -> int:
        """Get number of available slots."""
        return max(0, self.capacity - self.count)
    
    def get_oldest(self) -> Optional[ActiveSoundInfo]:
        """Get the oldest active sound."""
        if not self.active_sounds:
            return None
        return min(self.active_sounds.values(), key=lambda s: s.start_time)
    
    def get_lowest_priority(self) -> Optional[ActiveSoundInfo]:
        """Get the lowest priority active sound."""
        if not self.active_sounds:
            return None
        return min(self.active_sounds.values(), key=lambda s: s.priority)
    
    def get_by_sound_id(self, sound_id: str) -> List[ActiveSoundInfo]:
        """Get all active instances of a sound."""
        return [s for s in self.active_sounds.values() if s.sound_id == sound_id]


@dataclass
class LayerAction:
    """An action to take on the layer system."""
    action: str  # "start", "end", "interrupt"
    instance_id: str
    sound_id: str
    layer: str
    reason: str = ""
    priority: float = 1.0


class LayerManager:
    """
    Manages sound layers and their capacity.
    
    Responsibilities:
    - Track active sounds per layer
    - Enforce layer capacity limits
    - Handle sound lifecycle
    - Decide which sounds to interrupt when over capacity
    
    Example:
        >>> manager = LayerManager(config)
        >>> can_add = manager.can_add_sound("periodic")
        >>> if can_add:
        ...     manager.add_sound(sound_info)
        >>> expired = manager.get_expired_sounds(current_time)
        >>> for sound in expired:
        ...     manager.remove_sound(sound.instance_id)
    """
    
    # Default capacities per layer
    DEFAULT_CAPACITIES = {
        'background': 2,
        'periodic': 4,
        'reactive': 3,
        'anomalous': 1,
    }
    
    # Layer priorities for interruption decisions
    LAYER_INTERRUPT_PRIORITY = {
        'background': 1,   # Least likely to interrupt
        'periodic': 2,
        'reactive': 3,
        'anomalous': 4,    # Most likely to interrupt others
    }
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize the layer manager.
        
        Args:
            config: LSEConfig object (optional)
        """
        self.config = config
        
        # Initialize layers
        self.layers: Dict[str, LayerState] = {}
        self._init_layers()
        
        # Frequency band limits
        self.frequency_limits: Dict[str, int] = {
            'low': 2,
            'low_mid': 3,
            'mid': 4,
            'mid_high': 3,
            'high': 2,
            'full': 2,
        }
        
        # Statistics
        self.total_interruptions: int = 0
    
    def _init_layers(self) -> None:
        """Initialize layer states."""
        capacities = self.DEFAULT_CAPACITIES.copy()
        
        # Override from config if available
        # (Biome-specific capacities would be applied at runtime)
        
        for layer_type, capacity in capacities.items():
            self.layers[layer_type] = LayerState(
                layer_type=layer_type,
                capacity=capacity,
            )
    
    def set_biome_capacity(self, biome_params: Any) -> None:
        """
        Update capacities based on biome parameters.
        
        Args:
            biome_params: BiomeParameters object with layer_capacity
        """
        if biome_params is None:
            return
        
        total_capacity = getattr(biome_params, 'layer_capacity', 10)
        
        # Distribute capacity across layers
        # Background gets ~20%, periodic ~40%, reactive ~30%, anomalous ~10%
        self.layers['background'].capacity = max(1, int(total_capacity * 0.2))
        self.layers['periodic'].capacity = max(1, int(total_capacity * 0.4))
        self.layers['reactive'].capacity = max(1, int(total_capacity * 0.3))
        self.layers['anomalous'].capacity = max(1, int(total_capacity * 0.1))
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def can_add_sound(self, layer: str) -> bool:
        """Check if a sound can be added to a layer."""
        if layer not in self.layers:
            return False
        return not self.layers[layer].is_full
    
    def get_layer_state(self, layer: str) -> Optional[LayerState]:
        """Get the state of a layer."""
        return self.layers.get(layer)
    
    def get_all_active_sounds(self) -> List[ActiveSoundInfo]:
        """Get all active sounds across all layers."""
        sounds = []
        for layer_state in self.layers.values():
            sounds.extend(layer_state.active_sounds.values())
        return sounds
    
    def get_active_count(self, layer: Optional[str] = None) -> int:
        """Get count of active sounds, optionally filtered by layer."""
        if layer:
            state = self.layers.get(layer)
            return state.count if state else 0
        return sum(state.count for state in self.layers.values())
    
    def get_active_by_frequency(self, frequency_band: str) -> List[ActiveSoundInfo]:
        """Get all active sounds in a frequency band."""
        return [s for s in self.get_all_active_sounds() 
                if s.frequency_band == frequency_band]
    
    def get_frequency_count(self, frequency_band: str) -> int:
        """Get count of active sounds in a frequency band."""
        return len(self.get_active_by_frequency(frequency_band))
    
    def is_frequency_available(self, frequency_band: str) -> bool:
        """Check if there's room for another sound in this frequency band."""
        limit = self.frequency_limits.get(frequency_band, 3)
        return self.get_frequency_count(frequency_band) < limit
    
    def get_active_sound_ids(self) -> Set[str]:
        """Get set of all active sound IDs."""
        return {s.sound_id for s in self.get_all_active_sounds()}
    
    def get_active_tags(self) -> Set[str]:
        """Get set of all tags from active sounds."""
        tags = set()
        for sound in self.get_all_active_sounds():
            tags.update(sound.tags)
        return tags
    
    def has_active_sound(self, sound_id: str) -> bool:
        """Check if a sound is currently playing."""
        return sound_id in self.get_active_sound_ids()
    
    def get_sound_info(self, instance_id: str) -> Optional[ActiveSoundInfo]:
        """Get info about an active sound by instance ID."""
        for layer_state in self.layers.values():
            if instance_id in layer_state.active_sounds:
                return layer_state.active_sounds[instance_id]
        return None
    
    # =========================================================================
    # Lifecycle Methods
    # =========================================================================
    
    def add_sound(self, sound_info: ActiveSoundInfo) -> Tuple[bool, str]:
        """
        Add a sound to its layer.
        
        Args:
            sound_info: Information about the sound to add
            
        Returns:
            Tuple of (success, reason)
        """
        layer = sound_info.layer
        
        if layer not in self.layers:
            return False, f"Unknown layer: {layer}"
        
        layer_state = self.layers[layer]
        
        # Check capacity
        if layer_state.is_full:
            return False, f"Layer {layer} is at capacity ({layer_state.capacity})"
        
        # Check frequency band
        if not self.is_frequency_available(sound_info.frequency_band):
            return False, f"Frequency band {sound_info.frequency_band} is full"
        
        # Add to layer
        layer_state.active_sounds[sound_info.instance_id] = sound_info
        layer_state.total_started += 1
        
        return True, "Added successfully"
    
    def remove_sound(self, instance_id: str) -> Optional[ActiveSoundInfo]:
        """
        Remove a sound from its layer.
        
        Args:
            instance_id: Instance ID of the sound to remove
            
        Returns:
            The removed sound info, or None if not found
        """
        for layer_state in self.layers.values():
            if instance_id in layer_state.active_sounds:
                sound = layer_state.active_sounds.pop(instance_id)
                layer_state.total_ended += 1
                return sound
        return None
    
    def get_expired_sounds(self, current_time: float) -> List[ActiveSoundInfo]:
        """
        Get all sounds that have expired.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            List of expired sound infos
        """
        expired = []
        for layer_state in self.layers.values():
            for sound in layer_state.active_sounds.values():
                if sound.is_expired(current_time):
                    expired.append(sound)
        return expired
    
    def cleanup_expired(self, current_time: float) -> List[ActiveSoundInfo]:
        """
        Remove and return all expired sounds.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            List of removed sound infos
        """
        expired = self.get_expired_sounds(current_time)
        for sound in expired:
            self.remove_sound(sound.instance_id)
        return expired
    
    def interrupt_for_priority(self, layer: str, 
                                new_priority: float) -> Optional[ActiveSoundInfo]:
        """
        Interrupt a lower-priority sound to make room for a new one.
        
        Args:
            layer: Layer to make room in
            new_priority: Priority of the new sound
            
        Returns:
            The interrupted sound, or None if no interruption possible
        """
        layer_state = self.layers.get(layer)
        if not layer_state or not layer_state.is_full:
            return None
        
        # Find lowest priority sound
        lowest = layer_state.get_lowest_priority()
        if lowest and lowest.priority < new_priority:
            self.remove_sound(lowest.instance_id)
            self.total_interruptions += 1
            return lowest
        
        return None
    
    def interrupt_oldest(self, layer: str) -> Optional[ActiveSoundInfo]:
        """
        Interrupt the oldest sound in a layer.
        
        Args:
            layer: Layer to interrupt in
            
        Returns:
            The interrupted sound, or None if layer is empty
        """
        layer_state = self.layers.get(layer)
        if not layer_state or layer_state.count == 0:
            return None
        
        oldest = layer_state.get_oldest()
        if oldest:
            self.remove_sound(oldest.instance_id)
            self.total_interruptions += 1
            return oldest
        
        return None
    
    # =========================================================================
    # SDI-Aware Methods
    # =========================================================================
    
    def get_sounds_to_reduce(self, count: int = 1) -> List[ActiveSoundInfo]:
        """
        Get sounds that should be reduced to lower SDI.
        
        Prefers to end:
        - Anomalous sounds (high SDI impact)
        - Sounds in over-capacity frequency bands
        - Lowest priority sounds
        
        Args:
            count: Number of sounds to suggest for removal
            
        Returns:
            List of sounds suggested for removal
        """
        to_remove = []
        all_sounds = self.get_all_active_sounds()
        
        if not all_sounds:
            return []
        
        # Sort by removal priority (highest removal priority first)
        def removal_priority(sound: ActiveSoundInfo) -> float:
            priority = 0.0
            
            # Anomalous sounds first
            if sound.layer == 'anomalous':
                priority += 10.0
            
            # Over-capacity frequency bands
            if self.get_frequency_count(sound.frequency_band) > self.frequency_limits.get(sound.frequency_band, 3):
                priority += 5.0
            
            # Lower priority sounds
            priority -= sound.priority
            
            return priority
        
        all_sounds.sort(key=removal_priority, reverse=True)
        
        return all_sounds[:count]
    
    def get_layer_utilization(self) -> Dict[str, float]:
        """Get utilization ratio for each layer."""
        utilization = {}
        for layer_type, layer_state in self.layers.items():
            if layer_state.capacity > 0:
                utilization[layer_type] = layer_state.count / layer_state.capacity
            else:
                utilization[layer_type] = 0.0
        return utilization
    
    def get_total_capacity(self) -> int:
        """Get total capacity across all layers."""
        return sum(state.capacity for state in self.layers.values())
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    def get_state(self) -> Dict[str, Any]:
        """Get full manager state for serialization."""
        return {
            'layers': {
                layer_type: {
                    'capacity': state.capacity,
                    'count': state.count,
                    'total_started': state.total_started,
                    'total_ended': state.total_ended,
                    'active_sounds': [
                        {
                            'instance_id': s.instance_id,
                            'sound_id': s.sound_id,
                            'start_time': s.start_time,
                            'intensity': s.intensity,
                        }
                        for s in state.active_sounds.values()
                    ]
                }
                for layer_type, state in self.layers.items()
            },
            'total_interruptions': self.total_interruptions,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of current state."""
        return {
            'total_active': self.get_active_count(),
            'total_capacity': self.get_total_capacity(),
            'utilization': self.get_layer_utilization(),
            'by_layer': {k: v.count for k, v in self.layers.items()},
            'interruptions': self.total_interruptions,
        }
    
    def clear(self) -> None:
        """Clear all active sounds."""
        for layer_state in self.layers.values():
            layer_state.active_sounds.clear()
    
    def reset(self) -> None:
        """Reset to initial state."""
        self._init_layers()
        self.total_interruptions = 0
    
    def __repr__(self) -> str:
        counts = ', '.join(f"{k}={v.count}" for k, v in self.layers.items())
        return f"LayerManager({counts}, total={self.get_active_count()})"
