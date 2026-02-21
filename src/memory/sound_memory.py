"""
Sound event memory for the Living Soundscape Engine.

Tracks recent sound events with querying capabilities for:
- SDI factor calculations
- Pattern detection
- Sound selection decisions (cooldowns, recent plays)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Callable
from enum import Enum


class EndType(Enum):
    """How a sound ended."""
    NATURAL = "natural"      # Completed its expected duration
    FADE_OUT = "fade_out"    # Faded out gracefully
    INTERRUPTED = "interrupted"  # Cut off by another event
    FORCED = "forced"        # Forcibly stopped by system


@dataclass
class SoundEvent:
    """
    A record of a sound that has played or is playing.
    
    Attributes:
        instance_id: Unique ID for this specific play instance
        sound_id: The sound definition ID from config
        timestamp: When the sound started (simulation time)
        layer: Which layer this sound belongs to
        intensity: Playback intensity (0.0-1.0)
        frequency_band: Audio frequency band
        duration: Planned duration in seconds
        tags: Tags from the sound definition
        ended: Whether the sound has finished
        end_time: When the sound ended (if ended)
        end_type: How the sound ended (if ended)
        sdi_contribution: This sound's contribution to SDI
    """
    instance_id: str
    sound_id: str
    timestamp: float
    layer: str
    intensity: float
    frequency_band: str
    duration: float
    tags: List[str] = field(default_factory=list)
    ended: bool = False
    end_time: Optional[float] = None
    end_type: Optional[EndType] = None
    sdi_contribution: float = 0.0
    
    @property
    def expected_end_time(self) -> float:
        """Calculate when this sound should end."""
        return self.timestamp + self.duration
    
    @property
    def actual_duration(self) -> Optional[float]:
        """Get actual duration if ended, None otherwise."""
        if self.end_time is not None:
            return self.end_time - self.timestamp
        return None
    
    def is_active_at(self, time: float) -> bool:
        """Check if this sound is/was active at a given time."""
        if time < self.timestamp:
            return False
        if self.ended and self.end_time is not None:
            return time < self.end_time
        return time < self.expected_end_time
    
    def mark_ended(self, time: float, end_type: EndType = EndType.NATURAL) -> None:
        """Mark this sound as ended."""
        self.ended = True
        self.end_time = time
        self.end_type = end_type
    
    def overstayed(self, current_time: float, natural_duration: Optional[float]) -> float:
        """
        Calculate how long this sound has overstayed its natural duration.
        
        Args:
            current_time: Current simulation time
            natural_duration: Expected natural duration from config
            
        Returns:
            Overstay time in seconds (0 if not overstayed)
        """
        if natural_duration is None:
            return 0.0
        
        actual = current_time - self.timestamp
        if actual > natural_duration * 1.5:  # 50% grace period
            return actual - natural_duration
        return 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            'instance_id': self.instance_id,
            'sound_id': self.sound_id,
            'timestamp': self.timestamp,
            'layer': self.layer,
            'intensity': self.intensity,
            'frequency_band': self.frequency_band,
            'duration': self.duration,
            'tags': self.tags,
            'ended': self.ended,
            'end_time': self.end_time,
            'end_type': self.end_type.value if self.end_type else None,
            'sdi_contribution': self.sdi_contribution,
        }


class SoundMemory:
    """
    Manages the history of sound events.
    
    Provides efficient querying for:
    - Active sounds at a given time
    - Recent sounds by ID, layer, or tag
    - Cooldown checking
    - Layer and frequency band counts
    
    Attributes:
        retention_window: How long to keep events (seconds)
        max_events: Maximum events to store
        
    Example:
        >>> memory = SoundMemory(retention_window=60.0)
        >>> memory.add_event(event)
        >>> active = memory.get_active_sounds(current_time)
        >>> is_ready = not memory.is_on_cooldown("birdsong", current_time)
    """
    
    def __init__(self, retention_window: float = 60.0, max_events: int = 200):
        """
        Initialize sound memory.
        
        Args:
            retention_window: How long to keep events in memory
            max_events: Maximum number of events to store
        """
        self.retention_window = retention_window
        self.max_events = max_events
        
        # Event storage
        self._events: List[SoundEvent] = []
        self._active_events: Dict[str, SoundEvent] = {}  # instance_id -> event
        
        # Cooldown tracking
        self._cooldowns: Dict[str, float] = {}  # sound_id -> cooldown_until
        
        # Cached counts (updated on add/remove)
        self._layer_counts: Dict[str, int] = {
            'background': 0,
            'periodic': 0,
            'reactive': 0,
            'anomalous': 0,
        }
        self._frequency_counts: Dict[str, int] = {
            'low': 0,
            'low_mid': 0,
            'mid': 0,
            'mid_high': 0,
            'high': 0,
            'full': 0,
        }
        
        # Statistics
        self._total_events: int = 0
    
    # =========================================================================
    # Event Management
    # =========================================================================
    
    def add_event(self, event: SoundEvent) -> None:
        """
        Add a new sound event to memory.
        
        Args:
            event: The sound event to add
        """
        self._events.append(event)
        self._active_events[event.instance_id] = event
        self._total_events += 1
        
        # Update counts
        if event.layer in self._layer_counts:
            self._layer_counts[event.layer] += 1
        if event.frequency_band in self._frequency_counts:
            self._frequency_counts[event.frequency_band] += 1
        
        # Enforce max events
        while len(self._events) > self.max_events:
            removed = self._events.pop(0)
            if removed.instance_id in self._active_events:
                del self._active_events[removed.instance_id]
    
    def end_event(self, instance_id: str, time: float, 
                  end_type: EndType = EndType.NATURAL) -> Optional[SoundEvent]:
        """
        Mark an event as ended.
        
        Args:
            instance_id: The instance ID of the event to end
            time: The time the event ended
            end_type: How the event ended
            
        Returns:
            The ended event, or None if not found
        """
        event = self._active_events.get(instance_id)
        if event is None:
            return None
        
        event.mark_ended(time, end_type)
        del self._active_events[instance_id]
        
        # Update counts
        if event.layer in self._layer_counts:
            self._layer_counts[event.layer] = max(0, self._layer_counts[event.layer] - 1)
        if event.frequency_band in self._frequency_counts:
            self._frequency_counts[event.frequency_band] = max(0, self._frequency_counts[event.frequency_band] - 1)
        
        return event
    
    def end_event_by_sound_id(self, sound_id: str, time: float,
                              end_type: EndType = EndType.NATURAL) -> Optional[SoundEvent]:
        """
        End the most recent active event for a sound ID.
        
        Args:
            sound_id: The sound definition ID
            time: The time the event ended
            end_type: How the event ended
            
        Returns:
            The ended event, or None if not found
        """
        # Find the most recent active event for this sound
        for instance_id, event in list(self._active_events.items()):
            if event.sound_id == sound_id:
                return self.end_event(instance_id, time, end_type)
        return None
    
    def cleanup(self, current_time: float) -> int:
        """
        Remove old events and auto-end expired sounds.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            Number of events removed
        """
        cutoff = current_time - self.retention_window
        removed = 0
        
        # Auto-end expired active sounds
        for instance_id, event in list(self._active_events.items()):
            if not event.ended and current_time >= event.expected_end_time:
                self.end_event(instance_id, event.expected_end_time, EndType.NATURAL)
        
        # Remove old events
        old_len = len(self._events)
        self._events = [e for e in self._events if e.timestamp > cutoff]
        removed = old_len - len(self._events)
        
        # Clean up old cooldowns
        self._cooldowns = {k: v for k, v in self._cooldowns.items() if v > current_time}
        
        return removed
    
    # =========================================================================
    # Cooldown Management
    # =========================================================================
    
    def set_cooldown(self, sound_id: str, until: float) -> None:
        """
        Set a cooldown for a sound.
        
        Args:
            sound_id: The sound definition ID
            until: Time when the cooldown expires
        """
        self._cooldowns[sound_id] = until
    
    def is_on_cooldown(self, sound_id: str, current_time: float) -> bool:
        """
        Check if a sound is on cooldown.
        
        Args:
            sound_id: The sound definition ID
            current_time: Current simulation time
            
        Returns:
            True if on cooldown, False otherwise
        """
        if sound_id not in self._cooldowns:
            return False
        return current_time < self._cooldowns[sound_id]
    
    def get_cooldown_remaining(self, sound_id: str, current_time: float) -> float:
        """
        Get remaining cooldown time for a sound.
        
        Args:
            sound_id: The sound definition ID
            current_time: Current simulation time
            
        Returns:
            Remaining cooldown time (0 if not on cooldown)
        """
        if sound_id not in self._cooldowns:
            return 0.0
        remaining = self._cooldowns[sound_id] - current_time
        return max(0.0, remaining)
    
    # =========================================================================
    # Queries
    # =========================================================================
    
    def get_active_sounds(self) -> List[SoundEvent]:
        """Get all currently active sounds."""
        return list(self._active_events.values())
    
    def get_active_by_layer(self, layer: str) -> List[SoundEvent]:
        """Get all active sounds in a specific layer."""
        return [e for e in self._active_events.values() if e.layer == layer]
    
    def get_active_by_sound_id(self, sound_id: str) -> List[SoundEvent]:
        """Get all active instances of a specific sound."""
        return [e for e in self._active_events.values() if e.sound_id == sound_id]
    
    def get_active_by_tag(self, tag: str) -> List[SoundEvent]:
        """Get all active sounds with a specific tag."""
        return [e for e in self._active_events.values() if tag in e.tags]
    
    def get_active_by_frequency(self, frequency_band: str) -> List[SoundEvent]:
        """Get all active sounds in a specific frequency band."""
        return [e for e in self._active_events.values() 
                if e.frequency_band == frequency_band]
    
    def get_recent_events(self, count: int = 10) -> List[SoundEvent]:
        """Get the N most recent events."""
        return self._events[-count:]
    
    def get_events_in_window(self, start_time: float, end_time: float) -> List[SoundEvent]:
        """Get all events that occurred within a time window."""
        return [e for e in self._events 
                if start_time <= e.timestamp <= end_time]
    
    def get_events_by_sound_id(self, sound_id: str, 
                               limit: Optional[int] = None) -> List[SoundEvent]:
        """
        Get all events for a specific sound ID.
        
        Args:
            sound_id: The sound definition ID
            limit: Maximum number of events to return (most recent)
            
        Returns:
            List of events, most recent last
        """
        events = [e for e in self._events if e.sound_id == sound_id]
        if limit is not None:
            events = events[-limit:]
        return events
    
    def get_occurrence_timestamps(self, sound_id: str, 
                                   limit: Optional[int] = None) -> List[float]:
        """
        Get timestamps of occurrences for a sound.
        
        Used for pattern detection.
        
        Args:
            sound_id: The sound definition ID
            limit: Maximum number of timestamps to return
            
        Returns:
            List of timestamps, oldest first
        """
        events = self.get_events_by_sound_id(sound_id, limit)
        return [e.timestamp for e in events]
    
    def count_recent_occurrences(self, sound_id: str, window: float, 
                                  current_time: float) -> int:
        """
        Count how many times a sound has played recently.
        
        Args:
            sound_id: The sound definition ID
            window: Time window in seconds
            current_time: Current simulation time
            
        Returns:
            Number of occurrences in the window
        """
        cutoff = current_time - window
        return sum(1 for e in self._events 
                   if e.sound_id == sound_id and e.timestamp > cutoff)
    
    def get_last_occurrence(self, sound_id: str) -> Optional[SoundEvent]:
        """Get the most recent event for a sound."""
        events = self.get_events_by_sound_id(sound_id)
        return events[-1] if events else None
    
    def time_since_last(self, sound_id: str, current_time: float) -> Optional[float]:
        """
        Get time since the last occurrence of a sound.
        
        Args:
            sound_id: The sound definition ID
            current_time: Current simulation time
            
        Returns:
            Time in seconds, or None if never played
        """
        last = self.get_last_occurrence(sound_id)
        if last is None:
            return None
        return current_time - last.timestamp
    
    def has_active_sound(self, sound_id: str) -> bool:
        """Check if a specific sound is currently active."""
        return any(e.sound_id == sound_id for e in self._active_events.values())
    
    # =========================================================================
    # Counts and Statistics
    # =========================================================================
    
    @property
    def layer_counts(self) -> Dict[str, int]:
        """Get current active sound counts by layer."""
        return self._layer_counts.copy()
    
    @property
    def frequency_counts(self) -> Dict[str, int]:
        """Get current active sound counts by frequency band."""
        return self._frequency_counts.copy()
    
    @property
    def active_count(self) -> int:
        """Get total number of active sounds."""
        return len(self._active_events)
    
    @property
    def total_events(self) -> int:
        """Get total number of events ever recorded."""
        return self._total_events
    
    def get_active_ids(self) -> Set[str]:
        """Get set of currently active sound IDs."""
        return {e.sound_id for e in self._active_events.values()}
    
    def get_active_tags(self) -> Set[str]:
        """Get set of all tags from active sounds."""
        tags = set()
        for event in self._active_events.values():
            tags.update(event.tags)
        return tags
    
    # =========================================================================
    # SDI Helpers
    # =========================================================================
    
    def get_active_with_tag_pair(self, tag_a: str, tag_b: str) -> List[tuple]:
        """
        Find pairs of active sounds where one has tag_a and another has tag_b.
        
        Used for conflict detection.
        
        Returns:
            List of (event_a, event_b) tuples
        """
        sounds_a = self.get_active_by_tag(tag_a)
        sounds_b = self.get_active_by_tag(tag_b)
        
        pairs = []
        for a in sounds_a:
            for b in sounds_b:
                if a.instance_id != b.instance_id:
                    pairs.append((a, b))
        return pairs
    
    def get_active_sound_pairs(self, sound_a: str, sound_b: str) -> List[tuple]:
        """
        Find pairs of active sounds matching specific IDs.
        
        Used for harmony/conflict pair detection.
        
        Returns:
            List of (event_a, event_b) tuples
        """
        events_a = self.get_active_by_sound_id(sound_a)
        events_b = self.get_active_by_sound_id(sound_b)
        
        if not events_a or not events_b:
            return []
        
        return [(a, b) for a in events_a for b in events_b]
    
    def check_sound_pair_active(self, sound_a: str, sound_b: str) -> bool:
        """Check if both sounds in a pair are currently active."""
        has_a = self.has_active_sound(sound_a)
        has_b = self.has_active_sound(sound_b)
        return has_a and has_b
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    def get_state(self) -> Dict:
        """Get full memory state for serialization."""
        return {
            'events': [e.to_dict() for e in self._events],
            'active_ids': list(self._active_events.keys()),
            'cooldowns': self._cooldowns.copy(),
            'layer_counts': self._layer_counts.copy(),
            'frequency_counts': self._frequency_counts.copy(),
            'total_events': self._total_events,
        }
    
    def clear(self) -> None:
        """Clear all memory."""
        self._events.clear()
        self._active_events.clear()
        self._cooldowns.clear()
        self._layer_counts = {k: 0 for k in self._layer_counts}
        self._frequency_counts = {k: 0 for k in self._frequency_counts}
        self._total_events = 0
    
    def __repr__(self) -> str:
        return (f"SoundMemory(events={len(self._events)}, "
                f"active={len(self._active_events)}, "
                f"total={self._total_events})")
