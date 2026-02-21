"""
Event logging for the Living Soundscape Engine.

Captures and stores all sound events for analysis and debugging.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TextIO
from enum import Enum
import csv
import io
import json


@dataclass
class EventRecord:
    """
    A single recorded event.
    
    Attributes:
        timestamp: Simulation time when event occurred
        event_type: Type of event (sound_start, sound_end, etc.)
        sound_id: The sound definition ID
        instance_id: Unique instance ID
        layer: Sound layer
        duration: Duration for start events
        intensity: Playback intensity
        reason: Why this event occurred
        environment: Environment snapshot at event time
        sdi: SDI value at event time
        metadata: Additional event data
    """
    timestamp: float
    event_type: str
    sound_id: str = ""
    instance_id: str = ""
    layer: str = ""
    duration: float = 0.0
    intensity: float = 0.5
    reason: str = ""
    environment: Dict[str, Any] = field(default_factory=dict)
    sdi: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'sound_id': self.sound_id,
            'instance_id': self.instance_id,
            'layer': self.layer,
            'duration': self.duration,
            'intensity': self.intensity,
            'reason': self.reason,
            'biome': self.environment.get('biome_id', ''),
            'weather': self.environment.get('weather', ''),
            'time_of_day': self.environment.get('time_of_day', ''),
            'population': self.environment.get('population_ratio', 0.0),
            'sdi': self.sdi,
        }
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to CSV row dict."""
        return self.to_dict()
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        data = self.to_dict()
        data['metadata'] = self.metadata
        return json.dumps(data)


class EventLogger:
    """
    Logs and stores sound events.
    
    Features:
    - In-memory event storage with configurable limit
    - CSV export
    - JSON export
    - Filtering and queries
    - Statistics
    
    Example:
        >>> logger = EventLogger(max_events=10000)
        >>> logger.log_event(event, environment, sdi)
        >>> 
        >>> # Query events
        >>> starts = logger.get_by_type("sound_start")
        >>> recent = logger.get_recent(count=10)
        >>> 
        >>> # Export
        >>> csv_data = logger.to_csv()
        >>> json_data = logger.to_json()
    """
    
    # CSV column order
    CSV_COLUMNS = [
        'timestamp', 'event_type', 'sound_id', 'instance_id', 'layer',
        'duration', 'intensity', 'reason', 'biome', 'weather', 
        'time_of_day', 'population', 'sdi'
    ]
    
    def __init__(self, max_events: int = 10000):
        """
        Initialize the event logger.
        
        Args:
            max_events: Maximum events to store (oldest removed when exceeded)
        """
        self.max_events = max_events
        self._events: List[EventRecord] = []
        
        # Statistics
        self._stats = {
            'total_logged': 0,
            'by_type': {},
            'by_layer': {},
            'by_sound': {},
        }
    
    def log_event(self, event: Any, environment: Any = None, 
                  sdi: float = 0.0) -> EventRecord:
        """
        Log a sound event.
        
        Args:
            event: SoundscapeEvent object
            environment: Current environment state
            sdi: Current SDI value
            
        Returns:
            The created EventRecord
        """
        # Build environment dict
        env_dict = {}
        if environment is not None:
            env_dict = {
                'biome_id': getattr(environment, 'biome_id', ''),
                'weather': getattr(environment, 'weather', ''),
                'time_of_day': getattr(environment, 'time_of_day', ''),
                'population_ratio': getattr(environment, 'population_ratio', 0.0),
            }
        
        # Get event type as string
        event_type = event.event_type
        if hasattr(event_type, 'value'):
            event_type = event_type.value
        
        # Create record
        record = EventRecord(
            timestamp=event.timestamp,
            event_type=event_type,
            sound_id=event.sound_id,
            instance_id=event.instance_id,
            layer=event.layer,
            duration=event.duration,
            intensity=event.intensity,
            reason=event.reason,
            environment=env_dict,
            sdi=sdi,
            metadata=getattr(event, 'metadata', {}),
        )
        
        # Add to storage
        self._events.append(record)
        
        # Enforce limit
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]
        
        # Update stats
        self._stats['total_logged'] += 1
        self._stats['by_type'][event_type] = self._stats['by_type'].get(event_type, 0) + 1
        self._stats['by_layer'][event.layer] = self._stats['by_layer'].get(event.layer, 0) + 1
        self._stats['by_sound'][event.sound_id] = self._stats['by_sound'].get(event.sound_id, 0) + 1
        
        return record
    
    def log_raw(self, timestamp: float, event_type: str, sound_id: str = "",
                instance_id: str = "", layer: str = "", duration: float = 0.0,
                intensity: float = 0.5, reason: str = "", 
                environment: Dict = None, sdi: float = 0.0) -> EventRecord:
        """Log an event from raw parameters."""
        record = EventRecord(
            timestamp=timestamp,
            event_type=event_type,
            sound_id=sound_id,
            instance_id=instance_id,
            layer=layer,
            duration=duration,
            intensity=intensity,
            reason=reason,
            environment=environment or {},
            sdi=sdi,
        )
        
        self._events.append(record)
        
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]
        
        self._stats['total_logged'] += 1
        self._stats['by_type'][event_type] = self._stats['by_type'].get(event_type, 0) + 1
        
        return record
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_all(self) -> List[EventRecord]:
        """Get all stored events."""
        return list(self._events)
    
    def get_recent(self, count: int = 10) -> List[EventRecord]:
        """Get most recent events."""
        return self._events[-count:]
    
    def get_by_type(self, event_type: str) -> List[EventRecord]:
        """Get events of a specific type."""
        return [e for e in self._events if e.event_type == event_type]
    
    def get_by_sound(self, sound_id: str) -> List[EventRecord]:
        """Get events for a specific sound."""
        return [e for e in self._events if e.sound_id == sound_id]
    
    def get_by_layer(self, layer: str) -> List[EventRecord]:
        """Get events for a specific layer."""
        return [e for e in self._events if e.layer == layer]
    
    def get_in_range(self, start_time: float, end_time: float) -> List[EventRecord]:
        """Get events within a time range."""
        return [e for e in self._events if start_time <= e.timestamp <= end_time]
    
    def get_starts(self) -> List[EventRecord]:
        """Get all sound_start events."""
        return self.get_by_type("sound_start")
    
    def get_ends(self) -> List[EventRecord]:
        """Get all sound_end events."""
        return self.get_by_type("sound_end")
    
    def get_interrupts(self) -> List[EventRecord]:
        """Get all sound_interrupt events."""
        return self.get_by_type("sound_interrupt")
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    @property
    def count(self) -> int:
        """Get number of stored events."""
        return len(self._events)
    
    @property
    def total_logged(self) -> int:
        """Get total events logged (including removed)."""
        return self._stats['total_logged']
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        return {
            'stored_events': len(self._events),
            'total_logged': self._stats['total_logged'],
            'by_type': dict(self._stats['by_type']),
            'by_layer': dict(self._stats['by_layer']),
            'top_sounds': self._get_top_sounds(10),
        }
    
    def _get_top_sounds(self, count: int = 10) -> List[tuple]:
        """Get most frequently played sounds."""
        by_sound = self._stats['by_sound']
        sorted_sounds = sorted(by_sound.items(), key=lambda x: -x[1])
        return sorted_sounds[:count]
    
    def get_sound_histogram(self) -> Dict[str, int]:
        """Get play count for each sound."""
        return dict(self._stats['by_sound'])
    
    def get_layer_histogram(self) -> Dict[str, int]:
        """Get event count for each layer."""
        return dict(self._stats['by_layer'])
    
    # =========================================================================
    # Export Methods
    # =========================================================================
    
    def to_csv(self, include_header: bool = True) -> str:
        """
        Export events to CSV string.
        
        Args:
            include_header: Whether to include column headers
            
        Returns:
            CSV formatted string
        """
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.CSV_COLUMNS, 
                                extrasaction='ignore')
        
        if include_header:
            writer.writeheader()
        
        for event in self._events:
            writer.writerow(event.to_csv_row())
        
        return output.getvalue()
    
    def write_csv(self, filepath: str) -> int:
        """
        Write events to CSV file.
        
        Args:
            filepath: Path to output file
            
        Returns:
            Number of events written
        """
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS,
                                    extrasaction='ignore')
            writer.writeheader()
            
            for event in self._events:
                writer.writerow(event.to_csv_row())
        
        return len(self._events)
    
    def to_json(self, pretty: bool = False) -> str:
        """
        Export events to JSON string.
        
        Args:
            pretty: Whether to format with indentation
            
        Returns:
            JSON formatted string
        """
        data = [e.to_dict() for e in self._events]
        if pretty:
            return json.dumps(data, indent=2)
        return json.dumps(data)
    
    def write_json(self, filepath: str, pretty: bool = True) -> int:
        """
        Write events to JSON file.
        
        Args:
            filepath: Path to output file
            pretty: Whether to format with indentation
            
        Returns:
            Number of events written
        """
        with open(filepath, 'w') as f:
            data = [e.to_dict() for e in self._events]
            if pretty:
                json.dump(data, f, indent=2)
            else:
                json.dump(data, f)
        
        return len(self._events)
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    def clear(self) -> None:
        """Clear all stored events (keeps stats)."""
        self._events.clear()
    
    def reset(self) -> None:
        """Reset logger completely (clears events and stats)."""
        self._events.clear()
        self._stats = {
            'total_logged': 0,
            'by_type': {},
            'by_layer': {},
            'by_sound': {},
        }
    
    def __len__(self) -> int:
        return len(self._events)
    
    def __repr__(self) -> str:
        return f"EventLogger(stored={len(self._events)}, total={self._stats['total_logged']})"
