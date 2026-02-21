"""
Pattern detection for the Living Soundscape Engine.

Tracks sound occurrence patterns for SDI calculations related to:
- Rhythm instability (drifting patterns cause discomfort)
- Predictable rhythm (stable patterns provide comfort)
- Absence after pattern (broken patterns create tension)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


def _variance(values: list) -> float:
    """Calculate variance of a list of values."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


def _coefficient_of_variation(values: list) -> float:
    """Calculate coefficient of variation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    var = _variance(values)
    std_dev = var ** 0.5
    return std_dev / mean


class PatternType(Enum):
    """Classification of a pattern's behavior."""
    NONE = "none"              # Not enough data to classify
    RANDOM = "random"          # No discernible pattern
    RHYTHMIC = "rhythmic"      # Consistent, predictable intervals
    DRIFTING = "drifting"      # Almost rhythmic, but intervals drift
    BROKEN = "broken"          # Was rhythmic, then stopped unexpectedly


@dataclass
class PatternState:
    """
    Tracks pattern state for a single sound.
    
    Monitors the timing of sound occurrences to detect rhythmic patterns,
    drift, and unexpected absences.
    
    Attributes:
        sound_id: The sound being tracked
        occurrences: Timestamps of each occurrence
        intervals: Time intervals between occurrences
        pattern_type: Current classification of the pattern
        avg_interval: Average interval between occurrences
        cv: Coefficient of variation (lower = more consistent)
        expected_next: Expected time of next occurrence
        is_broken: Whether an expected occurrence was missed
        break_time: When the pattern broke (if broken)
    """
    sound_id: str
    occurrences: List[float] = field(default_factory=list)
    intervals: List[float] = field(default_factory=list)
    pattern_type: PatternType = PatternType.NONE
    avg_interval: float = 0.0
    cv: float = 0.0  # Coefficient of variation
    expected_next: Optional[float] = None
    is_broken: bool = False
    break_time: Optional[float] = None
    
    # Thresholds for pattern classification
    CV_RHYTHMIC = 0.10    # Below this = rhythmic
    CV_DRIFTING_LOW = 0.15   # Above CV_RHYTHMIC and below this = light drift
    CV_DRIFTING_HIGH = 0.40  # Above CV_DRIFTING_LOW and below this = drift
    MIN_OCCURRENCES = 3      # Minimum occurrences to detect a pattern
    BREAK_THRESHOLD = 2.0    # How many expected intervals before "broken"
    
    def add_occurrence(self, timestamp: float) -> PatternType:
        """
        Add a new occurrence and update pattern analysis.
        
        Args:
            timestamp: When the sound occurred
            
        Returns:
            The updated pattern type
        """
        # Check if this resolves a broken pattern
        was_broken = self.is_broken
        if was_broken:
            self.is_broken = False
            self.break_time = None
        
        # Calculate interval if we have previous occurrences
        if self.occurrences:
            interval = timestamp - self.occurrences[-1]
            self.intervals.append(interval)
        
        self.occurrences.append(timestamp)
        
        # Update analysis
        self._analyze()
        
        return self.pattern_type
    
    def _analyze(self) -> None:
        """Analyze the pattern based on current data."""
        if len(self.intervals) < self.MIN_OCCURRENCES - 1:
            self.pattern_type = PatternType.NONE
            self.avg_interval = 0.0
            self.cv = 0.0
            self.expected_next = None
            return
        
        # Calculate statistics
        self.avg_interval = sum(self.intervals) / len(self.intervals)
        self.cv = _coefficient_of_variation(self.intervals)
        
        # Classify pattern
        if self.cv < self.CV_RHYTHMIC:
            self.pattern_type = PatternType.RHYTHMIC
        elif self.cv < self.CV_DRIFTING_HIGH:
            self.pattern_type = PatternType.DRIFTING
        else:
            self.pattern_type = PatternType.RANDOM
        
        # Predict next occurrence
        if self.occurrences and self.avg_interval > 0:
            self.expected_next = self.occurrences[-1] + self.avg_interval
    
    def check_break(self, current_time: float) -> bool:
        """
        Check if the pattern has broken (expected sound didn't occur).
        
        Args:
            current_time: Current simulation time
            
        Returns:
            True if the pattern just broke, False otherwise
        """
        if self.pattern_type in (PatternType.NONE, PatternType.RANDOM):
            return False
        
        if self.expected_next is None:
            return False
        
        if self.is_broken:
            return False  # Already broken
        
        # Check if we've waited too long past expected time
        wait_threshold = self.avg_interval * self.BREAK_THRESHOLD
        if current_time > self.expected_next + wait_threshold:
            self.is_broken = True
            self.break_time = current_time
            self.pattern_type = PatternType.BROKEN
            return True
        
        return False
    
    def get_drift_amount(self) -> float:
        """
        Get the amount of drift in the most recent interval.
        
        Returns:
            Drift ratio (0.0 = perfect, higher = more drift)
        """
        if len(self.intervals) < 2 or self.avg_interval == 0:
            return 0.0
        
        last_interval = self.intervals[-1]
        drift = abs(last_interval - self.avg_interval) / self.avg_interval
        return drift
    
    def get_break_duration(self, current_time: float) -> float:
        """
        Get how long the pattern has been broken.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            Duration in seconds, or 0 if not broken
        """
        if not self.is_broken or self.break_time is None:
            return 0.0
        return current_time - self.break_time
    
    def is_rhythm_stable(self) -> bool:
        """Check if this is a stable rhythmic pattern."""
        return self.pattern_type == PatternType.RHYTHMIC
    
    def is_drifting(self) -> bool:
        """Check if this pattern is drifting."""
        return self.pattern_type == PatternType.DRIFTING
    
    def clear_old(self, current_time: float, retention: float) -> None:
        """
        Remove occurrences older than retention window.
        
        Args:
            current_time: Current simulation time
            retention: How long to keep occurrences
        """
        cutoff = current_time - retention
        
        # Find index of first occurrence to keep
        keep_from = 0
        for i, timestamp in enumerate(self.occurrences):
            if timestamp > cutoff:
                keep_from = i
                break
        else:
            # All occurrences are old
            self.occurrences.clear()
            self.intervals.clear()
            self._analyze()
            return
        
        # Remove old occurrences
        if keep_from > 0:
            self.occurrences = self.occurrences[keep_from:]
            # Intervals array is one shorter than occurrences
            if keep_from - 1 < len(self.intervals):
                self.intervals = self.intervals[keep_from - 1:]
            self._analyze()
    
    def reset(self) -> None:
        """Reset all pattern state."""
        self.occurrences.clear()
        self.intervals.clear()
        self.pattern_type = PatternType.NONE
        self.avg_interval = 0.0
        self.cv = 0.0
        self.expected_next = None
        self.is_broken = False
        self.break_time = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            'sound_id': self.sound_id,
            'occurrences': self.occurrences.copy(),
            'intervals': self.intervals.copy(),
            'pattern_type': self.pattern_type.value,
            'avg_interval': self.avg_interval,
            'cv': self.cv,
            'expected_next': self.expected_next,
            'is_broken': self.is_broken,
            'break_time': self.break_time,
        }


class PatternMemory:
    """
    Manages pattern tracking for all sounds.
    
    Provides:
    - Per-sound pattern tracking
    - Global pattern statistics
    - SDI-related queries
    
    Example:
        >>> memory = PatternMemory()
        >>> memory.record_occurrence("birdsong", 0.0)
        >>> memory.record_occurrence("birdsong", 5.0)
        >>> memory.record_occurrence("birdsong", 10.0)
        >>> memory.record_occurrence("birdsong", 15.2)
        >>> state = memory.get_pattern("birdsong")
        >>> state.pattern_type
        <PatternType.RHYTHMIC: 'rhythmic'>
    """
    
    def __init__(self, retention_window: float = 120.0):
        """
        Initialize pattern memory.
        
        Args:
            retention_window: How long to keep occurrence data
        """
        self.retention_window = retention_window
        self._patterns: Dict[str, PatternState] = {}
    
    # =========================================================================
    # Recording
    # =========================================================================
    
    def record_occurrence(self, sound_id: str, timestamp: float) -> PatternState:
        """
        Record a sound occurrence.
        
        Args:
            sound_id: The sound that occurred
            timestamp: When it occurred
            
        Returns:
            The updated pattern state
        """
        if sound_id not in self._patterns:
            self._patterns[sound_id] = PatternState(sound_id=sound_id)
        
        pattern = self._patterns[sound_id]
        pattern.add_occurrence(timestamp)
        return pattern
    
    def check_all_breaks(self, current_time: float) -> List[PatternState]:
        """
        Check all patterns for breaks.
        
        Args:
            current_time: Current simulation time
            
        Returns:
            List of patterns that just broke
        """
        broken = []
        for pattern in self._patterns.values():
            if pattern.check_break(current_time):
                broken.append(pattern)
        return broken
    
    def cleanup(self, current_time: float) -> None:
        """
        Clean up old data from all patterns.
        
        Args:
            current_time: Current simulation time
        """
        for pattern in self._patterns.values():
            pattern.clear_old(current_time, self.retention_window)
    
    # =========================================================================
    # Queries
    # =========================================================================
    
    def get_pattern(self, sound_id: str) -> Optional[PatternState]:
        """Get pattern state for a sound."""
        return self._patterns.get(sound_id)
    
    def has_pattern(self, sound_id: str) -> bool:
        """Check if a sound has any recorded pattern."""
        return sound_id in self._patterns
    
    def get_all_patterns(self) -> List[PatternState]:
        """Get all pattern states."""
        return list(self._patterns.values())
    
    def get_patterns_by_type(self, pattern_type: PatternType) -> List[PatternState]:
        """Get all patterns of a specific type."""
        return [p for p in self._patterns.values() if p.pattern_type == pattern_type]
    
    # =========================================================================
    # SDI Queries
    # =========================================================================
    
    def get_rhythmic_patterns(self) -> List[PatternState]:
        """Get all stable rhythmic patterns (comfort contributors)."""
        return self.get_patterns_by_type(PatternType.RHYTHMIC)
    
    def get_drifting_patterns(self) -> List[PatternState]:
        """Get all drifting patterns (discomfort contributors)."""
        return self.get_patterns_by_type(PatternType.DRIFTING)
    
    def get_broken_patterns(self) -> List[PatternState]:
        """Get all currently broken patterns."""
        return [p for p in self._patterns.values() if p.is_broken]
    
    def count_rhythmic(self) -> int:
        """Count stable rhythmic patterns."""
        return len(self.get_rhythmic_patterns())
    
    def count_drifting(self) -> int:
        """Count drifting patterns."""
        return len(self.get_drifting_patterns())
    
    def count_broken(self) -> int:
        """Count broken patterns."""
        return len(self.get_broken_patterns())
    
    def get_total_drift_contribution(self) -> float:
        """
        Calculate total drift contribution for SDI.
        
        Returns:
            Sum of drift amounts from all drifting patterns
        """
        total = 0.0
        for pattern in self.get_drifting_patterns():
            total += pattern.get_drift_amount()
        return total
    
    def get_rhythm_stability_score(self) -> float:
        """
        Calculate overall rhythm stability score.
        
        Returns:
            Score from -1.0 (all broken) to 1.0 (all rhythmic)
        """
        patterns = [p for p in self._patterns.values() 
                    if p.pattern_type != PatternType.NONE]
        
        if not patterns:
            return 0.0
        
        score = 0.0
        for p in patterns:
            if p.pattern_type == PatternType.RHYTHMIC:
                score += 1.0
            elif p.pattern_type == PatternType.DRIFTING:
                score -= 0.3
            elif p.pattern_type == PatternType.BROKEN:
                score -= 0.6
        
        return score / len(patterns)
    
    def get_break_contributions(self, current_time: float, decay_time: float) -> List[Tuple[str, float]]:
        """
        Get SDI contributions from broken patterns with decay.
        
        Args:
            current_time: Current simulation time
            decay_time: How long before contribution fades
            
        Returns:
            List of (sound_id, contribution) tuples
        """
        contributions = []
        
        for pattern in self.get_broken_patterns():
            duration = pattern.get_break_duration(current_time)
            
            if duration > decay_time:
                # Fully decayed, clear the break
                pattern.is_broken = False
                pattern.break_time = None
                continue
            
            # Linear decay
            factor = 1.0 - (duration / decay_time)
            contributions.append((pattern.sound_id, factor))
        
        return contributions
    
    # =========================================================================
    # Predictions
    # =========================================================================
    
    def get_expected_sounds(self, current_time: float, 
                            window: float) -> List[Tuple[str, float]]:
        """
        Get sounds expected to occur within a time window.
        
        Args:
            current_time: Current simulation time
            window: How far ahead to look
            
        Returns:
            List of (sound_id, expected_time) tuples
        """
        expected = []
        end_time = current_time + window
        
        for pattern in self._patterns.values():
            if pattern.expected_next is None:
                continue
            if pattern.is_broken:
                continue
            if current_time <= pattern.expected_next <= end_time:
                expected.append((pattern.sound_id, pattern.expected_next))
        
        return sorted(expected, key=lambda x: x[1])
    
    def predict_next_occurrence(self, sound_id: str) -> Optional[float]:
        """
        Predict when a sound will next occur.
        
        Args:
            sound_id: The sound to predict
            
        Returns:
            Expected timestamp, or None if unpredictable
        """
        pattern = self._patterns.get(sound_id)
        if pattern is None:
            return None
        return pattern.expected_next
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    def get_state(self) -> Dict:
        """Get full memory state for serialization."""
        return {
            'patterns': {k: v.to_dict() for k, v in self._patterns.items()},
            'retention_window': self.retention_window,
        }
    
    def get_summary(self) -> Dict:
        """Get a summary of pattern states."""
        return {
            'total_patterns': len(self._patterns),
            'rhythmic': self.count_rhythmic(),
            'drifting': self.count_drifting(),
            'broken': self.count_broken(),
            'random': len(self.get_patterns_by_type(PatternType.RANDOM)),
            'stability_score': self.get_rhythm_stability_score(),
        }
    
    def clear(self) -> None:
        """Clear all pattern data."""
        self._patterns.clear()
    
    def clear_pattern(self, sound_id: str) -> None:
        """Clear pattern data for a specific sound."""
        if sound_id in self._patterns:
            del self._patterns[sound_id]
    
    def __repr__(self) -> str:
        return (f"PatternMemory(patterns={len(self._patterns)}, "
                f"rhythmic={self.count_rhythmic()}, "
                f"drifting={self.count_drifting()}, "
                f"broken={self.count_broken()})")
