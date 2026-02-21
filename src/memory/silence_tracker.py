"""
Silence tracking for the Living Soundscape Engine.

Tracks silence gaps (periods with no active non-background sounds)
for SDI calculations related to:
- Silence deprivation (too long without silence)
- Appropriate silence gaps (comfort factor)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class SilenceGap:
    """
    A recorded period of silence.
    
    Attributes:
        start_time: When silence began
        end_time: When silence ended (None if ongoing)
        duration: Duration of the gap (calculated)
        was_appropriate: Whether this gap was in the appropriate range
    """
    start_time: float
    end_time: Optional[float] = None
    was_appropriate: bool = False
    
    @property
    def duration(self) -> float:
        """Get duration of this gap."""
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time
    
    @property
    def is_complete(self) -> bool:
        """Check if this gap has ended."""
        return self.end_time is not None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'was_appropriate': self.was_appropriate,
        }


class SilenceTracker:
    """
    Tracks silence gaps and provides SDI-related metrics.
    
    "Silence" is defined as no active sounds in layers that contribute
    to silence (typically periodic, reactive, anomalous - not background).
    
    The tracker maintains:
    - Current silence state
    - Recent silence gaps history
    - Time since last silence
    - Silence deprivation detection
    
    Example:
        >>> tracker = SilenceTracker()
        >>> tracker.update(timestamp=10.0, sound_count=0)  # Silence starts
        >>> tracker.update(timestamp=12.5, sound_count=1)  # Silence ends
        >>> tracker.last_gap.duration
        2.5
        >>> tracker.is_deprived(current_time=50.0, tolerance=5.0)
        True
    """
    
    # Minimum duration for a gap to count as "real" silence
    MIN_GAP_DURATION = 2.0
    
    # How many gaps to keep in history
    MAX_GAP_HISTORY = 20
    
    def __init__(self):
        """Initialize the silence tracker."""
        # Current state
        self._in_silence: bool = True  # Start in silence
        self._current_gap_start: Optional[float] = 0.0
        
        # History
        self._gaps: List[SilenceGap] = []
        self._last_complete_gap: Optional[SilenceGap] = None
        
        # Last time we had any silence end
        self._last_silence_end: Optional[float] = None
        
        # Statistics
        self._total_gaps: int = 0
        self._appropriate_gaps: int = 0
    
    # =========================================================================
    # State Updates
    # =========================================================================
    
    def update(self, timestamp: float, sound_count: int) -> Optional[SilenceGap]:
        """
        Update silence state based on current sound count.
        
        Call this every tick with the count of sounds that "break" silence
        (typically periodic + reactive + anomalous, not background).
        
        Args:
            timestamp: Current simulation time
            sound_count: Number of silence-breaking sounds currently active
            
        Returns:
            A completed SilenceGap if silence just ended, None otherwise
        """
        is_now_silent = (sound_count == 0)
        
        if is_now_silent and not self._in_silence:
            # Silence is starting
            self._start_silence(timestamp)
            return None
            
        elif not is_now_silent and self._in_silence:
            # Silence is ending
            return self._end_silence(timestamp)
        
        return None
    
    def _start_silence(self, timestamp: float) -> None:
        """Mark the start of a silence period."""
        self._in_silence = True
        self._current_gap_start = timestamp
    
    def _end_silence(self, timestamp: float) -> Optional[SilenceGap]:
        """Mark the end of a silence period."""
        self._in_silence = False
        self._last_silence_end = timestamp
        
        if self._current_gap_start is None:
            return None
        
        # Create the gap record
        gap = SilenceGap(
            start_time=self._current_gap_start,
            end_time=timestamp,
        )
        
        self._current_gap_start = None
        
        # Only record if duration meets minimum
        if gap.duration >= self.MIN_GAP_DURATION:
            self._record_gap(gap)
            return gap
        
        return None
    
    def _record_gap(self, gap: SilenceGap) -> None:
        """Record a completed silence gap."""
        self._gaps.append(gap)
        self._last_complete_gap = gap
        self._total_gaps += 1
        
        if gap.was_appropriate:
            self._appropriate_gaps += 1
        
        # Enforce history limit
        while len(self._gaps) > self.MAX_GAP_HISTORY:
            self._gaps.pop(0)
    
    def force_end_silence(self, timestamp: float) -> Optional[SilenceGap]:
        """
        Force silence to end (e.g., when a sound starts).
        
        Use this when you know a sound is starting and want to
        immediately update the tracker.
        
        Args:
            timestamp: Current simulation time
            
        Returns:
            The completed gap if there was one
        """
        if self._in_silence:
            return self._end_silence(timestamp)
        return None
    
    def force_start_silence(self, timestamp: float) -> None:
        """
        Force silence to start (e.g., when last sound ends).
        
        Args:
            timestamp: Current simulation time
        """
        if not self._in_silence:
            self._start_silence(timestamp)
    
    # =========================================================================
    # Queries
    # =========================================================================
    
    @property
    def in_silence(self) -> bool:
        """Check if currently in a silence period."""
        return self._in_silence
    
    @property
    def last_gap(self) -> Optional[SilenceGap]:
        """Get the most recent complete silence gap."""
        return self._last_complete_gap
    
    @property
    def current_gap_duration(self) -> float:
        """
        Get duration of current ongoing silence.
        
        Returns 0 if not currently in silence.
        """
        # Note: This needs current_time passed in for accurate calculation
        return 0.0 if self._current_gap_start is None else 0.0
    
    def get_current_silence_duration(self, current_time: float) -> float:
        """
        Get duration of current ongoing silence period.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            Duration in seconds, or 0 if not in silence
        """
        if not self._in_silence or self._current_gap_start is None:
            return 0.0
        return current_time - self._current_gap_start
    
    def time_since_silence(self, current_time: float) -> float:
        """
        Get time since the last silence period ended.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            Time in seconds since silence ended.
            Returns 0 if currently in silence.
            Returns current_time if never had silence.
        """
        if self._in_silence:
            return 0.0
        
        if self._last_silence_end is None:
            return current_time  # Never had silence
        
        return current_time - self._last_silence_end
    
    def is_deprived(self, current_time: float, tolerance: float) -> bool:
        """
        Check if we're experiencing silence deprivation.
        
        Silence deprivation occurs when the time since last silence
        exceeds the biome's silence tolerance.
        
        Args:
            current_time: Current simulation time
            tolerance: Biome's silence tolerance in seconds
            
        Returns:
            True if deprived of silence, False otherwise
        """
        return self.time_since_silence(current_time) > tolerance
    
    def get_deprivation_factor(self, current_time: float, tolerance: float) -> float:
        """
        Calculate how much we've exceeded silence tolerance.
        
        Args:
            current_time: Current simulation time
            tolerance: Biome's silence tolerance in seconds
            
        Returns:
            Ratio of (time_since_silence / tolerance), capped at 3.0
            Returns 0 if not deprived.
        """
        time_since = self.time_since_silence(current_time)
        
        if time_since <= tolerance:
            return 0.0
        
        excess = time_since - tolerance
        factor = excess / tolerance  # How many tolerance-lengths past
        return min(factor, 3.0)  # Cap at 3x
    
    def was_gap_appropriate(self, gap: SilenceGap, tolerance: float) -> bool:
        """
        Check if a silence gap was in the "appropriate" range.
        
        Appropriate gaps are between 50% and 150% of the biome's tolerance.
        These contribute to comfort (negative SDI).
        
        Args:
            gap: The silence gap to check
            tolerance: Biome's silence tolerance
            
        Returns:
            True if the gap was appropriately timed
        """
        min_duration = tolerance * 0.5
        max_duration = tolerance * 1.5
        return min_duration <= gap.duration <= max_duration
    
    def mark_gap_appropriate(self, gap: SilenceGap, tolerance: float) -> None:
        """
        Mark a gap as appropriate or not based on tolerance.
        
        Args:
            gap: The gap to mark
            tolerance: Biome's silence tolerance
        """
        gap.was_appropriate = self.was_gap_appropriate(gap, tolerance)
        if gap.was_appropriate:
            self._appropriate_gaps += 1
    
    # =========================================================================
    # Recent Gap Analysis
    # =========================================================================
    
    def get_recent_gaps(self, count: int = 5) -> List[SilenceGap]:
        """Get the N most recent silence gaps."""
        return self._gaps[-count:]
    
    def get_gaps_in_window(self, start_time: float, end_time: float) -> List[SilenceGap]:
        """Get all gaps that started within a time window."""
        return [g for g in self._gaps 
                if start_time <= g.start_time <= end_time]
    
    def count_appropriate_recent(self, window: float, current_time: float) -> int:
        """
        Count appropriate silence gaps in a recent time window.
        
        Args:
            window: Time window in seconds
            current_time: Current simulation time
            
        Returns:
            Number of appropriate gaps in the window
        """
        cutoff = current_time - window
        return sum(1 for g in self._gaps 
                   if g.start_time > cutoff and g.was_appropriate)
    
    def average_gap_duration(self, recent_count: int = 10) -> float:
        """
        Calculate average duration of recent gaps.
        
        Args:
            recent_count: Number of recent gaps to consider
            
        Returns:
            Average duration, or 0 if no gaps
        """
        gaps = self.get_recent_gaps(recent_count)
        if not gaps:
            return 0.0
        return sum(g.duration for g in gaps) / len(gaps)
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    @property
    def total_gaps(self) -> int:
        """Total number of silence gaps recorded."""
        return self._total_gaps
    
    @property
    def appropriate_gap_count(self) -> int:
        """Number of appropriate silence gaps."""
        return self._appropriate_gaps
    
    @property
    def appropriate_ratio(self) -> float:
        """Ratio of appropriate gaps to total gaps."""
        if self._total_gaps == 0:
            return 0.0
        return self._appropriate_gaps / self._total_gaps
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    def get_state(self) -> Dict:
        """Get full tracker state for serialization."""
        return {
            'in_silence': self._in_silence,
            'current_gap_start': self._current_gap_start,
            'last_silence_end': self._last_silence_end,
            'gaps': [g.to_dict() for g in self._gaps],
            'total_gaps': self._total_gaps,
            'appropriate_gaps': self._appropriate_gaps,
        }
    
    def reset(self) -> None:
        """Reset the tracker to initial state."""
        self._in_silence = True
        self._current_gap_start = 0.0
        self._gaps.clear()
        self._last_complete_gap = None
        self._last_silence_end = None
        self._total_gaps = 0
        self._appropriate_gaps = 0
    
    def __repr__(self) -> str:
        status = "in_silence" if self._in_silence else "active"
        return (f"SilenceTracker({status}, "
                f"gaps={self._total_gaps}, "
                f"appropriate={self._appropriate_gaps})")
