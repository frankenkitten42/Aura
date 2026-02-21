"""
Session recording for the Living Soundscape Engine.

Records complete sessions including events, SDI, and state changes
for later analysis and replay.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TextIO
import json
import csv
import io
import time
from datetime import datetime


@dataclass
class StateSnapshot:
    """A snapshot of engine state at a point in time."""
    timestamp: float
    simulation_time: float
    
    # Environment
    biome_id: str = ""
    time_of_day: str = ""
    weather: str = ""
    population: float = 0.0
    
    # SDI
    sdi: float = 0.0
    target_sdi: float = 0.0
    delta: float = 0.0
    
    # Sounds
    active_sounds: int = 0
    sounds_started: int = 0
    sounds_ended: int = 0
    
    # Memory
    patterns_tracked: int = 0
    silence_gaps: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'simulation_time': self.simulation_time,
            'biome_id': self.biome_id,
            'time_of_day': self.time_of_day,
            'weather': self.weather,
            'population': self.population,
            'sdi': self.sdi,
            'target_sdi': self.target_sdi,
            'delta': self.delta,
            'active_sounds': self.active_sounds,
            'sounds_started': self.sounds_started,
            'sounds_ended': self.sounds_ended,
            'patterns_tracked': self.patterns_tracked,
            'silence_gaps': self.silence_gaps,
        }


@dataclass
class SessionData:
    """
    Complete recorded session data.
    
    Contains all information needed to analyze or replay a session.
    """
    # Metadata
    session_id: str = ""
    start_time: str = ""
    end_time: str = ""
    duration: float = 0.0
    seed: Optional[int] = None
    
    # Configuration
    config_summary: Dict[str, Any] = field(default_factory=dict)
    
    # Events
    events: List[Dict] = field(default_factory=list)
    
    # SDI timeline
    sdi_timeline: List[Dict] = field(default_factory=list)
    
    # State snapshots
    snapshots: List[Dict] = field(default_factory=list)
    
    # Environment changes
    environment_changes: List[Dict] = field(default_factory=list)
    
    # Statistics
    stats: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'metadata': {
                'session_id': self.session_id,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'duration': self.duration,
                'seed': self.seed,
            },
            'config_summary': self.config_summary,
            'events': self.events,
            'sdi_timeline': self.sdi_timeline,
            'snapshots': self.snapshots,
            'environment_changes': self.environment_changes,
            'stats': self.stats,
        }
    
    def to_json(self, pretty: bool = True) -> str:
        """Convert to JSON string."""
        if pretty:
            return json.dumps(self.to_dict(), indent=2)
        return json.dumps(self.to_dict())
    
    def save(self, filepath: str) -> None:
        """Save session to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'SessionData':
        """Load session from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        session = cls()
        meta = data.get('metadata', {})
        session.session_id = meta.get('session_id', '')
        session.start_time = meta.get('start_time', '')
        session.end_time = meta.get('end_time', '')
        session.duration = meta.get('duration', 0.0)
        session.seed = meta.get('seed')
        
        session.config_summary = data.get('config_summary', {})
        session.events = data.get('events', [])
        session.sdi_timeline = data.get('sdi_timeline', [])
        session.snapshots = data.get('snapshots', [])
        session.environment_changes = data.get('environment_changes', [])
        session.stats = data.get('stats', {})
        
        return session
    
    def get_summary(self) -> str:
        """Get text summary of session."""
        lines = [
            "=" * 60,
            "SESSION SUMMARY",
            "=" * 60,
            "",
            f"Session ID: {self.session_id}",
            f"Duration: {self.duration:.1f}s",
            f"Start: {self.start_time}",
            f"End: {self.end_time}",
            f"Seed: {self.seed}",
            "",
            "--- Events ---",
            f"Total events: {len(self.events)}",
        ]
        
        # Count event types
        event_counts = {}
        for e in self.events:
            t = e.get('event_type', 'unknown')
            event_counts[t] = event_counts.get(t, 0) + 1
        
        for event_type, count in event_counts.items():
            lines.append(f"  {event_type}: {count}")
        
        lines.extend([
            "",
            "--- SDI ---",
            f"Samples: {len(self.sdi_timeline)}",
        ])
        
        if self.sdi_timeline:
            sdi_values = [s.get('sdi', 0) for s in self.sdi_timeline]
            lines.append(f"Min: {min(sdi_values):.3f}")
            lines.append(f"Max: {max(sdi_values):.3f}")
            lines.append(f"Avg: {sum(sdi_values)/len(sdi_values):.3f}")
        
        lines.extend([
            "",
            "--- Environment Changes ---",
            f"Total changes: {len(self.environment_changes)}",
        ])
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def events_to_csv(self) -> str:
        """Export events to CSV."""
        if not self.events:
            return ""
        
        output = io.StringIO()
        fieldnames = list(self.events[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(self.events)
        return output.getvalue()
    
    def sdi_to_csv(self) -> str:
        """Export SDI timeline to CSV."""
        if not self.sdi_timeline:
            return ""
        
        output = io.StringIO()
        fieldnames = list(self.sdi_timeline[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(self.sdi_timeline)
        return output.getvalue()


class SessionRecorder:
    """
    Records complete engine sessions.
    
    Captures:
    - All sound events
    - SDI calculations
    - State snapshots
    - Environment changes
    
    Example:
        >>> recorder = SessionRecorder()
        >>> recorder.start(seed=42)
        >>> 
        >>> # During simulation
        >>> recorder.record_event(event, environment, sdi)
        >>> recorder.record_sdi(timestamp, sdi_result, environment)
        >>> recorder.record_snapshot(engine.get_state())
        >>> 
        >>> # End session
        >>> session = recorder.stop()
        >>> session.save("session.json")
    """
    
    def __init__(self, snapshot_interval: float = 10.0, 
                 sdi_interval: float = 1.0):
        """
        Initialize the recorder.
        
        Args:
            snapshot_interval: Seconds between automatic state snapshots
            sdi_interval: Seconds between SDI samples
        """
        self.snapshot_interval = snapshot_interval
        self.sdi_interval = sdi_interval
        
        self._recording = False
        self._session: Optional[SessionData] = None
        self._start_real_time: float = 0.0
        self._last_snapshot_time: float = 0.0
        self._last_sdi_time: float = -float('inf')
        self._last_environment: Dict[str, Any] = {}
        
        # Counters
        self._event_count = 0
        self._sdi_count = 0
    
    def start(self, seed: Optional[int] = None, 
              config_summary: Dict[str, Any] = None) -> None:
        """
        Start recording a new session.
        
        Args:
            seed: Random seed used for the session
            config_summary: Summary of configuration used
        """
        self._recording = True
        self._start_real_time = time.time()
        self._last_snapshot_time = 0.0
        self._last_sdi_time = -float('inf')
        self._last_environment = {}
        self._event_count = 0
        self._sdi_count = 0
        
        self._session = SessionData(
            session_id=self._generate_session_id(),
            start_time=datetime.now().isoformat(),
            seed=seed,
            config_summary=config_summary or {},
        )
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def stop(self) -> SessionData:
        """
        Stop recording and return session data.
        
        Returns:
            Complete SessionData object
        """
        if not self._recording or self._session is None:
            raise RuntimeError("No active recording to stop")
        
        self._recording = False
        self._session.end_time = datetime.now().isoformat()
        self._session.duration = time.time() - self._start_real_time
        
        # Compile stats
        self._session.stats = self._compile_stats()
        
        session = self._session
        self._session = None
        return session
    
    def _compile_stats(self) -> Dict[str, Any]:
        """Compile session statistics."""
        session = self._session
        
        # Event counts
        event_counts = {}
        sound_counts = {}
        for e in session.events:
            t = e.get('event_type', 'unknown')
            event_counts[t] = event_counts.get(t, 0) + 1
            
            if t == 'sound_start':
                s = e.get('sound_id', 'unknown')
                sound_counts[s] = sound_counts.get(s, 0) + 1
        
        # SDI stats
        sdi_stats = {}
        if session.sdi_timeline:
            sdi_values = [s.get('sdi', 0) for s in session.sdi_timeline]
            sdi_stats = {
                'min': min(sdi_values),
                'max': max(sdi_values),
                'avg': sum(sdi_values) / len(sdi_values),
            }
        
        return {
            'total_events': len(session.events),
            'event_counts': event_counts,
            'unique_sounds': len(sound_counts),
            'top_sounds': sorted(sound_counts.items(), key=lambda x: -x[1])[:10],
            'sdi_samples': len(session.sdi_timeline),
            'sdi_stats': sdi_stats,
            'snapshots': len(session.snapshots),
            'environment_changes': len(session.environment_changes),
        }
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording
    
    # =========================================================================
    # Recording Methods
    # =========================================================================
    
    def record_event(self, event: Any, environment: Any = None,
                     sdi: float = 0.0) -> None:
        """
        Record a sound event.
        
        Args:
            event: SoundscapeEvent object
            environment: Current environment state
            sdi: Current SDI value
        """
        if not self._recording or self._session is None:
            return
        
        event_type = event.event_type
        if hasattr(event_type, 'value'):
            event_type = event_type.value
        
        record = {
            'timestamp': event.timestamp,
            'event_type': event_type,
            'sound_id': event.sound_id,
            'instance_id': event.instance_id,
            'layer': event.layer,
            'duration': event.duration,
            'intensity': event.intensity,
            'reason': event.reason,
            'sdi': sdi,
        }
        
        if environment:
            record['biome_id'] = getattr(environment, 'biome_id', '')
            record['weather'] = getattr(environment, 'weather', '')
            record['population'] = getattr(environment, 'population_ratio', 0.0)
        
        self._session.events.append(record)
        self._event_count += 1
    
    def record_sdi(self, timestamp: float, sdi_result: Any,
                   environment: Any = None, 
                   active_count: int = 0) -> bool:
        """
        Record an SDI calculation.
        
        Args:
            timestamp: Simulation time
            sdi_result: SDIResult object
            environment: Current environment state
            active_count: Number of active sounds
            
        Returns:
            True if recorded, False if skipped due to interval
        """
        if not self._recording or self._session is None:
            return False
        
        if timestamp - self._last_sdi_time < self.sdi_interval:
            return False
        
        self._last_sdi_time = timestamp
        
        record = {
            'timestamp': timestamp,
            'sdi': sdi_result.smoothed_sdi,
            'target': sdi_result.target_sdi,
            'delta': sdi_result.delta,
            'category': sdi_result.delta_category,
            'active_sounds': active_count,
        }
        
        if environment:
            record['biome_id'] = getattr(environment, 'biome_id', '')
            record['population'] = getattr(environment, 'population_ratio', 0.0)
        
        # Add factor breakdown
        if hasattr(sdi_result, 'discomfort'):
            record['discomfort'] = sdi_result.discomfort.total
        if hasattr(sdi_result, 'comfort'):
            record['comfort'] = sdi_result.comfort.total
        
        self._session.sdi_timeline.append(record)
        self._sdi_count += 1
        return True
    
    def record_snapshot(self, state: Dict[str, Any], 
                        timestamp: float = None) -> None:
        """
        Record a state snapshot.
        
        Args:
            state: Engine state dictionary
            timestamp: Simulation time (uses state time if not provided)
        """
        if not self._recording or self._session is None:
            return
        
        sim_time = timestamp or state.get('simulation_time', 0.0)
        
        if sim_time - self._last_snapshot_time < self.snapshot_interval:
            return
        
        self._last_snapshot_time = sim_time
        
        snapshot = StateSnapshot(
            timestamp=time.time() - self._start_real_time,
            simulation_time=sim_time,
            biome_id=state.get('environment', {}).get('biome_id', ''),
            time_of_day=state.get('environment', {}).get('time_of_day', ''),
            weather=state.get('environment', {}).get('weather', ''),
            population=state.get('environment', {}).get('population_ratio', 0.0),
            sdi=state.get('sdi', {}).get('current', 0.0),
            target_sdi=state.get('sdi', {}).get('target', 0.0),
            delta=state.get('sdi', {}).get('delta', 0.0),
            active_sounds=state.get('stats', {}).get('active_sounds', 0),
            sounds_started=state.get('stats', {}).get('total_sounds_started', 0),
            sounds_ended=state.get('stats', {}).get('total_sounds_ended', 0),
            patterns_tracked=state.get('memory', {}).get('patterns_tracked', 0),
            silence_gaps=state.get('memory', {}).get('silence_gaps', 0),
        )
        
        self._session.snapshots.append(snapshot.to_dict())
    
    def record_environment_change(self, timestamp: float, 
                                   change_type: str,
                                   old_value: Any, 
                                   new_value: Any) -> None:
        """
        Record an environment change.
        
        Args:
            timestamp: When the change occurred
            change_type: Type of change (biome, weather, time, population)
            old_value: Previous value
            new_value: New value
        """
        if not self._recording or self._session is None:
            return
        
        self._session.environment_changes.append({
            'timestamp': timestamp,
            'change_type': change_type,
            'old_value': old_value,
            'new_value': new_value,
        })
    
    def check_environment_change(self, timestamp: float, 
                                  environment: Any) -> None:
        """
        Check for and record any environment changes.
        
        Args:
            timestamp: Current simulation time
            environment: Current environment state
        """
        if not self._recording or environment is None:
            return
        
        current = {
            'biome_id': getattr(environment, 'biome_id', ''),
            'weather': getattr(environment, 'weather', ''),
            'time_of_day': getattr(environment, 'time_of_day', ''),
            'population': round(getattr(environment, 'population_ratio', 0.0), 2),
        }
        
        for key, new_val in current.items():
            old_val = self._last_environment.get(key)
            if old_val is not None and old_val != new_val:
                self.record_environment_change(timestamp, key, old_val, new_val)
        
        self._last_environment = current
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get statistics for the current recording."""
        if not self._recording or self._session is None:
            return {}
        
        return {
            'events_recorded': self._event_count,
            'sdi_samples': self._sdi_count,
            'snapshots': len(self._session.snapshots),
            'environment_changes': len(self._session.environment_changes),
            'recording_time': time.time() - self._start_real_time,
        }
    
    def __repr__(self) -> str:
        if self._recording:
            return f"SessionRecorder(recording, events={self._event_count})"
        return "SessionRecorder(stopped)"
