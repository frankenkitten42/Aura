"""
Debug logging for the Living Soundscape Engine.

Provides detailed debugging output for development and troubleshooting.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TextIO, Callable
from enum import Enum
import sys
import io
import json
from datetime import datetime


class LogLevel(Enum):
    """Log levels for filtering output."""
    TRACE = 0    # Very detailed, every tick
    DEBUG = 1    # Detailed debugging
    INFO = 2     # General information
    WARNING = 3  # Potential issues
    ERROR = 4    # Errors
    NONE = 5     # No logging


@dataclass
class LogEntry:
    """A single log entry."""
    timestamp: float
    level: LogLevel
    category: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def format(self, include_data: bool = True) -> str:
        """Format entry as string."""
        level_str = self.level.name[:5].ljust(5)
        cat_str = self.category[:12].ljust(12)
        line = f"[{self.timestamp:8.2f}] {level_str} {cat_str} {self.message}"
        
        if include_data and self.data:
            data_str = ", ".join(f"{k}={v}" for k, v in self.data.items())
            line += f" ({data_str})"
        
        return line
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'level': self.level.name,
            'category': self.category,
            'message': self.message,
            'data': self.data,
        }


class DebugLogger:
    """
    Debug logger for the Living Soundscape Engine.
    
    Features:
    - Multiple log levels
    - Category filtering
    - Console and file output
    - Structured data logging
    - Performance metrics
    
    Example:
        >>> logger = DebugLogger(level=LogLevel.DEBUG)
        >>> logger.debug("sdi", "Calculated SDI", sdi=0.15, delta=0.05)
        >>> logger.info("sound", "Started sound", sound_id="birdsong")
        >>> 
        >>> # Filter by category
        >>> logger.set_category_filter(["sdi", "sound"])
        >>> 
        >>> # Export
        >>> logger.write_log("debug.log")
    """
    
    # Category colors for terminal output (ANSI codes)
    CATEGORY_COLORS = {
        'engine': '\033[36m',    # Cyan
        'sdi': '\033[33m',       # Yellow
        'sound': '\033[32m',     # Green
        'memory': '\033[35m',    # Magenta
        'layer': '\033[34m',     # Blue
        'event': '\033[37m',     # White
    }
    RESET_COLOR = '\033[0m'
    
    LEVEL_COLORS = {
        LogLevel.TRACE: '\033[90m',   # Gray
        LogLevel.DEBUG: '\033[37m',   # White
        LogLevel.INFO: '\033[32m',    # Green
        LogLevel.WARNING: '\033[33m', # Yellow
        LogLevel.ERROR: '\033[31m',   # Red
    }
    
    def __init__(self, 
                 level: LogLevel = LogLevel.INFO,
                 output: Optional[TextIO] = None,
                 use_colors: bool = True,
                 max_entries: int = 10000):
        """
        Initialize the debug logger.
        
        Args:
            level: Minimum log level to record
            output: Output stream (None = no console output)
            use_colors: Use ANSI colors in output
            max_entries: Maximum entries to store
        """
        self.level = level
        self.output = output
        self.use_colors = use_colors
        self.max_entries = max_entries
        
        self._entries: List[LogEntry] = []
        self._category_filter: Optional[set] = None
        self._callbacks: List[Callable] = []
        
        # Performance tracking
        self._tick_times: List[float] = []
        self._last_tick_start: float = 0.0
    
    def set_level(self, level: LogLevel) -> None:
        """Set the minimum log level."""
        self.level = level
    
    def set_category_filter(self, categories: Optional[List[str]]) -> None:
        """
        Set category filter (only log these categories).
        
        Args:
            categories: List of categories to log, or None to log all
        """
        if categories is None:
            self._category_filter = None
        else:
            self._category_filter = set(categories)
    
    def add_callback(self, callback: Callable) -> None:
        """Add a callback for log entries."""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    # =========================================================================
    # Logging Methods
    # =========================================================================
    
    def log(self, level: LogLevel, category: str, message: str, 
            timestamp: float = 0.0, **data) -> Optional[LogEntry]:
        """
        Log a message.
        
        Args:
            level: Log level
            category: Category (e.g., "sdi", "sound", "engine")
            message: Log message
            timestamp: Simulation timestamp
            **data: Additional structured data
            
        Returns:
            LogEntry if logged, None if filtered
        """
        # Check level
        if level.value < self.level.value:
            return None
        
        # Check category filter
        if self._category_filter and category not in self._category_filter:
            return None
        
        entry = LogEntry(
            timestamp=timestamp,
            level=level,
            category=category,
            message=message,
            data=data,
        )
        
        # Store entry
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]
        
        # Output to console
        if self.output:
            self._write_entry(entry)
        
        # Call callbacks
        for callback in self._callbacks:
            callback(entry)
        
        return entry
    
    def trace(self, category: str, message: str, timestamp: float = 0.0, **data) -> Optional[LogEntry]:
        """Log at TRACE level."""
        return self.log(LogLevel.TRACE, category, message, timestamp, **data)
    
    def debug(self, category: str, message: str, timestamp: float = 0.0, **data) -> Optional[LogEntry]:
        """Log at DEBUG level."""
        return self.log(LogLevel.DEBUG, category, message, timestamp, **data)
    
    def info(self, category: str, message: str, timestamp: float = 0.0, **data) -> Optional[LogEntry]:
        """Log at INFO level."""
        return self.log(LogLevel.INFO, category, message, timestamp, **data)
    
    def warning(self, category: str, message: str, timestamp: float = 0.0, **data) -> Optional[LogEntry]:
        """Log at WARNING level."""
        return self.log(LogLevel.WARNING, category, message, timestamp, **data)
    
    def error(self, category: str, message: str, timestamp: float = 0.0, **data) -> Optional[LogEntry]:
        """Log at ERROR level."""
        return self.log(LogLevel.ERROR, category, message, timestamp, **data)
    
    def _write_entry(self, entry: LogEntry) -> None:
        """Write entry to output stream."""
        if self.use_colors:
            level_color = self.LEVEL_COLORS.get(entry.level, '')
            cat_color = self.CATEGORY_COLORS.get(entry.category, '')
            
            level_str = f"{level_color}{entry.level.name[:5].ljust(5)}{self.RESET_COLOR}"
            cat_str = f"{cat_color}{entry.category[:12].ljust(12)}{self.RESET_COLOR}"
            
            line = f"[{entry.timestamp:8.2f}] {level_str} {cat_str} {entry.message}"
            
            if entry.data:
                data_str = ", ".join(f"{k}={v}" for k, v in entry.data.items())
                line += f" ({data_str})"
        else:
            line = entry.format()
        
        self.output.write(line + "\n")
        self.output.flush()
    
    # =========================================================================
    # Specialized Logging
    # =========================================================================
    
    def log_tick(self, timestamp: float, sdi: float, active_sounds: int,
                 delta: float = 0.0, category: str = "none") -> None:
        """Log a simulation tick."""
        self.trace("engine", "Tick", timestamp,
                   sdi=f"{sdi:.3f}", delta=f"{delta:.3f}",
                   active=active_sounds, cat=category)
    
    def log_sound_start(self, timestamp: float, sound_id: str, 
                        layer: str, duration: float, intensity: float) -> None:
        """Log a sound start event."""
        self.debug("sound", f"START {sound_id}", timestamp,
                   layer=layer, dur=f"{duration:.1f}s", int=f"{intensity:.2f}")
    
    def log_sound_end(self, timestamp: float, sound_id: str,
                      reason: str = "natural") -> None:
        """Log a sound end event."""
        self.debug("sound", f"END {sound_id}", timestamp, reason=reason)
    
    def log_sound_interrupt(self, timestamp: float, sound_id: str,
                            reason: str = "") -> None:
        """Log a sound interrupt."""
        self.info("sound", f"INTERRUPT {sound_id}", timestamp, reason=reason)
    
    def log_sdi_calculation(self, timestamp: float, raw: float, smoothed: float,
                            target: float, delta: float, 
                            top_pos: str = "", top_neg: str = "") -> None:
        """Log an SDI calculation."""
        self.debug("sdi", "Calculated", timestamp,
                   raw=f"{raw:.3f}", smooth=f"{smoothed:.3f}",
                   target=f"{target:.3f}", delta=f"{delta:.3f}",
                   top_pos=top_pos, top_neg=top_neg)
    
    def log_environment_change(self, timestamp: float, field: str,
                               old_value: Any, new_value: Any) -> None:
        """Log an environment change."""
        self.info("engine", f"Environment: {field}", timestamp,
                  old=old_value, new=new_value)
    
    def log_pattern_detected(self, timestamp: float, sound_id: str,
                             pattern_type: str, interval: float) -> None:
        """Log a pattern detection."""
        self.debug("memory", f"Pattern: {sound_id}", timestamp,
                   type=pattern_type, interval=f"{interval:.1f}s")
    
    def log_layer_full(self, timestamp: float, layer: str, 
                       capacity: int) -> None:
        """Log when a layer reaches capacity."""
        self.info("layer", f"Layer full: {layer}", timestamp, capacity=capacity)
    
    # =========================================================================
    # Performance Tracking
    # =========================================================================
    
    def tick_start(self) -> None:
        """Mark the start of a tick for performance tracking."""
        import time
        self._last_tick_start = time.perf_counter()
    
    def tick_end(self) -> float:
        """
        Mark the end of a tick and return duration.
        
        Returns:
            Tick duration in milliseconds
        """
        import time
        duration = (time.perf_counter() - self._last_tick_start) * 1000
        self._tick_times.append(duration)
        
        # Keep last 1000 tick times
        if len(self._tick_times) > 1000:
            self._tick_times = self._tick_times[-1000:]
        
        return duration
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get tick performance statistics."""
        if not self._tick_times:
            return {'avg_ms': 0.0, 'min_ms': 0.0, 'max_ms': 0.0}
        
        return {
            'avg_ms': sum(self._tick_times) / len(self._tick_times),
            'min_ms': min(self._tick_times),
            'max_ms': max(self._tick_times),
            'samples': len(self._tick_times),
        }
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_entries(self, level: Optional[LogLevel] = None,
                    category: Optional[str] = None,
                    count: Optional[int] = None) -> List[LogEntry]:
        """
        Get log entries with optional filtering.
        
        Args:
            level: Filter by minimum level
            category: Filter by category
            count: Maximum entries to return (most recent)
        """
        entries = self._entries
        
        if level:
            entries = [e for e in entries if e.level.value >= level.value]
        
        if category:
            entries = [e for e in entries if e.category == category]
        
        if count:
            entries = entries[-count:]
        
        return entries
    
    def get_recent(self, count: int = 20) -> List[LogEntry]:
        """Get most recent entries."""
        return self._entries[-count:]
    
    def get_errors(self) -> List[LogEntry]:
        """Get all error entries."""
        return [e for e in self._entries if e.level == LogLevel.ERROR]
    
    def get_warnings(self) -> List[LogEntry]:
        """Get all warning entries."""
        return [e for e in self._entries if e.level == LogLevel.WARNING]
    
    def get_by_category(self, category: str) -> List[LogEntry]:
        """Get entries for a category."""
        return [e for e in self._entries if e.category == category]
    
    def search(self, text: str) -> List[LogEntry]:
        """Search entries by message content."""
        text_lower = text.lower()
        return [e for e in self._entries if text_lower in e.message.lower()]
    
    # =========================================================================
    # Export Methods
    # =========================================================================
    
    def to_text(self, include_data: bool = True) -> str:
        """Export log as plain text."""
        lines = [e.format(include_data) for e in self._entries]
        return "\n".join(lines)
    
    def to_json(self, pretty: bool = False) -> str:
        """Export log as JSON."""
        data = [e.to_dict() for e in self._entries]
        if pretty:
            return json.dumps(data, indent=2)
        return json.dumps(data)
    
    def write_log(self, filepath: str, format: str = "text") -> int:
        """
        Write log to file.
        
        Args:
            filepath: Output file path
            format: "text" or "json"
            
        Returns:
            Number of entries written
        """
        with open(filepath, 'w') as f:
            if format == "json":
                f.write(self.to_json(pretty=True))
            else:
                f.write(self.to_text())
        
        return len(self._entries)
    
    def get_summary(self) -> str:
        """Get a summary of logged entries."""
        lines = [
            "Debug Log Summary",
            "=" * 40,
            f"Total entries: {len(self._entries)}",
            "",
            "By level:",
        ]
        
        level_counts = {}
        for e in self._entries:
            level_counts[e.level.name] = level_counts.get(e.level.name, 0) + 1
        
        for level, count in sorted(level_counts.items()):
            lines.append(f"  {level}: {count}")
        
        lines.extend(["", "By category:"])
        
        cat_counts = {}
        for e in self._entries:
            cat_counts[e.category] = cat_counts.get(e.category, 0) + 1
        
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat}: {count}")
        
        # Performance stats
        perf = self.get_performance_stats()
        if perf.get('samples', 0) > 0:
            lines.extend([
                "",
                "Performance:",
                f"  Avg tick: {perf['avg_ms']:.2f}ms",
                f"  Min tick: {perf['min_ms']:.2f}ms",
                f"  Max tick: {perf['max_ms']:.2f}ms",
            ])
        
        return "\n".join(lines)
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    @property
    def count(self) -> int:
        """Get number of stored entries."""
        return len(self._entries)
    
    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._tick_times.clear()
    
    def __len__(self) -> int:
        return len(self._entries)
    
    def __repr__(self) -> str:
        return f"DebugLogger(entries={len(self._entries)}, level={self.level.name})"


def create_console_logger(level: LogLevel = LogLevel.INFO,
                          use_colors: bool = True) -> DebugLogger:
    """Create a logger that outputs to console."""
    return DebugLogger(level=level, output=sys.stdout, use_colors=use_colors)


def create_file_logger(filepath: str, 
                       level: LogLevel = LogLevel.DEBUG) -> DebugLogger:
    """Create a logger that outputs to a file."""
    f = open(filepath, 'w')
    return DebugLogger(level=level, output=f, use_colors=False)
