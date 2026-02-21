"""
Simulation clock and time management for the Living Soundscape Engine.

Handles simulation time advancement, time-of-day calculations, and
provides utilities for time-based events.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from enum import Enum


class TimeOfDay(Enum):
    """Time of day periods with their hour ranges."""
    MIDNIGHT = "midnight"  # 0-5
    DAWN = "dawn"          # 5-7
    DAY = "day"            # 7-17
    DUSK = "dusk"          # 17-20
    NIGHT = "night"        # 20-24
    
    @classmethod
    def from_hour(cls, hour: float) -> 'TimeOfDay':
        """Get time of day from hour (0-24)."""
        hour = hour % 24  # Wrap around
        
        if 0 <= hour < 5:
            return cls.MIDNIGHT
        elif 5 <= hour < 7:
            return cls.DAWN
        elif 7 <= hour < 17:
            return cls.DAY
        elif 17 <= hour < 20:
            return cls.DUSK
        else:  # 20-24
            return cls.NIGHT


@dataclass
class SimulationClock:
    """
    Manages simulation time and time-of-day calculations.
    
    The clock can run in two modes:
    1. Simulated time: Time advances at a configurable rate per tick
    2. Game time: A separate "game hour" that can advance at different rates
    
    Attributes:
        simulation_time: Total elapsed simulation time in seconds
        tick_rate: Seconds per tick (default 1.0)
        game_hour: Current hour in game time (0-24)
        hours_per_minute: Game hours that pass per real minute (for time scaling)
        
    Example:
        >>> clock = SimulationClock(game_hour=6.0)
        >>> clock.time_of_day
        <TimeOfDay.DAWN: 'dawn'>
        >>> clock.tick()
        >>> clock.simulation_time
        1.0
    """
    
    simulation_time: float = 0.0
    tick_rate: float = 1.0  # Seconds per tick
    
    game_hour: float = 12.0  # Start at noon
    hours_per_minute: float = 1.0  # 1 game hour per real minute (fast)
    
    _tick_count: int = 0
    _paused: bool = False
    
    @property
    def time_of_day(self) -> TimeOfDay:
        """Get current time of day based on game hour."""
        return TimeOfDay.from_hour(self.game_hour)
    
    @property
    def time_of_day_str(self) -> str:
        """Get current time of day as string."""
        return self.time_of_day.value
    
    @property
    def tick_count(self) -> int:
        """Get total number of ticks elapsed."""
        return self._tick_count
    
    @property
    def is_day(self) -> bool:
        """Check if it's currently daytime (dawn, day, or dusk)."""
        return self.time_of_day in (TimeOfDay.DAWN, TimeOfDay.DAY, TimeOfDay.DUSK)
    
    @property
    def is_night(self) -> bool:
        """Check if it's currently nighttime (night or midnight)."""
        return self.time_of_day in (TimeOfDay.NIGHT, TimeOfDay.MIDNIGHT)
    
    def tick(self) -> float:
        """
        Advance the clock by one tick.
        
        Returns:
            The new simulation time
        """
        if self._paused:
            return self.simulation_time
        
        self._tick_count += 1
        self.simulation_time += self.tick_rate
        
        # Advance game time
        # hours_per_minute / 60 = hours per second
        # hours per second * tick_rate = hours per tick
        hours_per_tick = (self.hours_per_minute / 60.0) * self.tick_rate
        self.game_hour = (self.game_hour + hours_per_tick) % 24.0
        
        return self.simulation_time
    
    def advance(self, seconds: float) -> float:
        """
        Advance the clock by a specific number of seconds.
        
        Args:
            seconds: Number of seconds to advance
            
        Returns:
            The new simulation time
        """
        if self._paused:
            return self.simulation_time
        
        num_ticks = int(seconds / self.tick_rate)
        for _ in range(num_ticks):
            self.tick()
        
        return self.simulation_time
    
    def set_game_hour(self, hour: float) -> None:
        """
        Set the game hour directly.
        
        Args:
            hour: Hour to set (0-24, will be wrapped)
        """
        self.game_hour = hour % 24.0
    
    def set_time_of_day(self, time_of_day: TimeOfDay) -> None:
        """
        Set the clock to the middle of a time of day period.
        
        Args:
            time_of_day: The time of day to set
        """
        middle_hours = {
            TimeOfDay.MIDNIGHT: 2.5,
            TimeOfDay.DAWN: 6.0,
            TimeOfDay.DAY: 12.0,
            TimeOfDay.DUSK: 18.5,
            TimeOfDay.NIGHT: 22.0,
        }
        self.game_hour = middle_hours.get(time_of_day, 12.0)
    
    def pause(self) -> None:
        """Pause the clock."""
        self._paused = True
    
    def resume(self) -> None:
        """Resume the clock."""
        self._paused = False
    
    def reset(self, game_hour: float = 12.0) -> None:
        """
        Reset the clock to initial state.
        
        Args:
            game_hour: Starting game hour (default noon)
        """
        self.simulation_time = 0.0
        self.game_hour = game_hour
        self._tick_count = 0
        self._paused = False
    
    def get_time_progress(self) -> float:
        """
        Get progress through the current time of day period (0.0 to 1.0).
        
        Useful for smooth transitions between periods.
        
        Returns:
            Progress from 0.0 (start of period) to 1.0 (end of period)
        """
        hour = self.game_hour
        
        if 0 <= hour < 5:  # Midnight
            return hour / 5.0
        elif 5 <= hour < 7:  # Dawn
            return (hour - 5) / 2.0
        elif 7 <= hour < 17:  # Day
            return (hour - 7) / 10.0
        elif 17 <= hour < 20:  # Dusk
            return (hour - 17) / 3.0
        else:  # Night (20-24)
            return (hour - 20) / 4.0
    
    def is_transitioning(self, threshold: float = 0.1) -> bool:
        """
        Check if we're near a time-of-day transition.
        
        Args:
            threshold: How close to the transition (0.0-0.5)
            
        Returns:
            True if within threshold of start or end of current period
        """
        progress = self.get_time_progress()
        return progress < threshold or progress > (1.0 - threshold)
    
    def hours_until(self, target_time: TimeOfDay) -> float:
        """
        Calculate hours until a specific time of day.
        
        Args:
            target_time: The target time of day
            
        Returns:
            Hours until the target (may be up to 24)
        """
        target_hours = {
            TimeOfDay.MIDNIGHT: 0.0,
            TimeOfDay.DAWN: 5.0,
            TimeOfDay.DAY: 7.0,
            TimeOfDay.DUSK: 17.0,
            TimeOfDay.NIGHT: 20.0,
        }
        
        target = target_hours.get(target_time, 0.0)
        current = self.game_hour
        
        if target > current:
            return target - current
        else:
            return (24.0 - current) + target
    
    def matches_constraint(self, constraint: str) -> bool:
        """
        Check if current time matches a time constraint.
        
        Args:
            constraint: Time constraint string ("all", "day", "night", etc.)
            
        Returns:
            True if current time matches the constraint
        """
        if constraint == "all":
            return True
        
        current = self.time_of_day_str
        
        # Direct match
        if constraint == current:
            return True
        
        # Special cases
        if constraint == "day" and current in ("dawn", "day"):
            return True
        if constraint == "night" and current in ("dusk", "night", "midnight"):
            return True
        
        return False
    
    def get_state(self) -> Dict:
        """Get clock state for serialization."""
        return {
            'simulation_time': self.simulation_time,
            'tick_rate': self.tick_rate,
            'game_hour': self.game_hour,
            'hours_per_minute': self.hours_per_minute,
            'tick_count': self._tick_count,
            'paused': self._paused,
            'time_of_day': self.time_of_day_str,
        }
    
    def set_state(self, state: Dict) -> None:
        """Restore clock state from serialization."""
        self.simulation_time = state.get('simulation_time', 0.0)
        self.tick_rate = state.get('tick_rate', 1.0)
        self.game_hour = state.get('game_hour', 12.0)
        self.hours_per_minute = state.get('hours_per_minute', 1.0)
        self._tick_count = state.get('tick_count', 0)
        self._paused = state.get('paused', False)
    
    def format_time(self) -> str:
        """Format current game time as HH:MM string."""
        hours = int(self.game_hour)
        minutes = int((self.game_hour % 1.0) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def __repr__(self) -> str:
        return (
            f"SimulationClock(time={self.simulation_time:.1f}s, "
            f"game_time={self.format_time()}, "
            f"period={self.time_of_day_str})"
        )
