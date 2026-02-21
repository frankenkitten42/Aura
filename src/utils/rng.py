"""
Seeded random number generation for the Living Soundscape Engine.

Provides reproducible randomness for testing and debugging. Multiple
independent RNG streams can be created to isolate different aspects
of the simulation (sound selection, timing variance, etc.).
"""

import random
from typing import Optional, List, TypeVar, Sequence

T = TypeVar('T')


class SeededRNG:
    """
    A seeded random number generator wrapper.
    
    Wraps Python's random module with explicit seed management for
    reproducibility. Each instance maintains its own state.
    
    Attributes:
        seed: The seed used to initialize this RNG
        name: Optional name for debugging
        
    Example:
        >>> rng = SeededRNG(seed=42, name="sound_selection")
        >>> rng.random()  # Always returns same value for seed=42
        0.6394267984578837
        >>> rng.probability(0.5)  # 50% chance of True
        True
    """
    
    def __init__(self, seed: Optional[int] = None, name: str = "default"):
        """
        Initialize the RNG with an optional seed.
        
        Args:
            seed: Integer seed for reproducibility. If None, uses system time.
            name: Name for this RNG stream (for debugging)
        """
        self.name = name
        self._random = random.Random()
        
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
        
        self.seed = seed
        self._random.seed(seed)
        self._call_count = 0
    
    def random(self) -> float:
        """
        Return a random float in [0.0, 1.0).
        
        Returns:
            Random float between 0.0 (inclusive) and 1.0 (exclusive)
        """
        self._call_count += 1
        return self._random.random()
    
    def uniform(self, a: float, b: float) -> float:
        """
        Return a random float in [a, b].
        
        Args:
            a: Lower bound
            b: Upper bound
            
        Returns:
            Random float between a and b (inclusive)
        """
        self._call_count += 1
        return self._random.uniform(a, b)
    
    def randint(self, a: int, b: int) -> int:
        """
        Return a random integer in [a, b].
        
        Args:
            a: Lower bound (inclusive)
            b: Upper bound (inclusive)
            
        Returns:
            Random integer between a and b
        """
        self._call_count += 1
        return self._random.randint(a, b)
    
    def probability(self, p: float) -> bool:
        """
        Return True with probability p.
        
        This is the primary method for probability-based decisions
        like whether a sound should play.
        
        Args:
            p: Probability of returning True (0.0 to 1.0)
            
        Returns:
            True with probability p, False otherwise
            
        Example:
            >>> rng = SeededRNG(42)
            >>> rng.probability(0.5)  # 50% chance
            True
            >>> rng.probability(1.0)  # Always True
            True
            >>> rng.probability(0.0)  # Always False
            False
        """
        return self.random() < p
    
    def choice(self, sequence: Sequence[T]) -> T:
        """
        Return a random element from a non-empty sequence.
        
        Args:
            sequence: Non-empty sequence to choose from
            
        Returns:
            Random element from the sequence
            
        Raises:
            IndexError: If sequence is empty
        """
        self._call_count += 1
        return self._random.choice(sequence)
    
    def weighted_choice(self, items: List[T], weights: List[float]) -> T:
        """
        Return a random element using weighted probabilities.
        
        Args:
            items: List of items to choose from
            weights: List of weights (same length as items)
            
        Returns:
            Randomly selected item based on weights
            
        Raises:
            ValueError: If items and weights have different lengths
            ValueError: If items is empty
            
        Example:
            >>> rng = SeededRNG(42)
            >>> rng.weighted_choice(['a', 'b', 'c'], [1, 2, 7])
            'c'  # 'c' has 70% chance
        """
        if len(items) != len(weights):
            raise ValueError("Items and weights must have same length")
        if not items:
            raise ValueError("Cannot choose from empty list")
        
        self._call_count += 1
        total = sum(weights)
        if total == 0:
            return self._random.choice(items)
        
        r = self._random.random() * total
        cumulative = 0.0
        
        for item, weight in zip(items, weights):
            cumulative += weight
            if r < cumulative:
                return item
        
        return items[-1]  # Fallback for floating point edge cases
    
    def shuffle(self, items: List[T]) -> List[T]:
        """
        Return a shuffled copy of the list.
        
        Args:
            items: List to shuffle
            
        Returns:
            New list with items in random order
        """
        self._call_count += 1
        result = items.copy()
        self._random.shuffle(result)
        return result
    
    def gauss(self, mu: float, sigma: float) -> float:
        """
        Return a random value from a Gaussian distribution.
        
        Useful for natural-feeling variation in timing.
        
        Args:
            mu: Mean of the distribution
            sigma: Standard deviation
            
        Returns:
            Random value from the normal distribution
        """
        self._call_count += 1
        return self._random.gauss(mu, sigma)
    
    def vary(self, value: float, variance_ratio: float) -> float:
        """
        Return a value with random variance applied.
        
        Convenience method for adding natural variation to values
        like timing intervals.
        
        Args:
            value: Base value
            variance_ratio: Maximum variance as ratio (e.g., 0.1 = ±10%)
            
        Returns:
            Value with random variance applied
            
        Example:
            >>> rng = SeededRNG(42)
            >>> rng.vary(10.0, 0.1)  # 10.0 ± 10%
            9.27...
        """
        variance = value * variance_ratio
        return self.uniform(value - variance, value + variance)
    
    def reset(self, seed: Optional[int] = None) -> None:
        """
        Reset the RNG to initial state or a new seed.
        
        Args:
            seed: New seed to use. If None, uses the original seed.
        """
        if seed is not None:
            self.seed = seed
        self._random.seed(self.seed)
        self._call_count = 0
    
    def get_state(self) -> dict:
        """
        Get the current state of the RNG for serialization.
        
        Returns:
            Dictionary containing RNG state
        """
        return {
            'name': self.name,
            'seed': self.seed,
            'call_count': self._call_count,
            'state': self._random.getstate()
        }
    
    def set_state(self, state: dict) -> None:
        """
        Restore RNG state from a previous get_state() call.
        
        Args:
            state: State dictionary from get_state()
        """
        self.name = state['name']
        self.seed = state['seed']
        self._call_count = state['call_count']
        self._random.setstate(state['state'])
    
    def __repr__(self) -> str:
        return f"SeededRNG(seed={self.seed}, name='{self.name}', calls={self._call_count})"


class RNGManager:
    """
    Manages multiple named RNG streams.
    
    Provides centralized access to different RNG streams for different
    purposes (sound selection, timing, etc.) while maintaining
    reproducibility.
    
    Example:
        >>> manager = RNGManager(master_seed=42)
        >>> manager.get('sounds').probability(0.5)
        True
        >>> manager.get('timing').uniform(1.0, 5.0)
        3.14...
    """
    
    def __init__(self, master_seed: Optional[int] = None):
        """
        Initialize the RNG manager with a master seed.
        
        Args:
            master_seed: Seed used to derive seeds for all streams
        """
        self._master = SeededRNG(seed=master_seed, name="master")
        self._streams: dict[str, SeededRNG] = {}
        self.master_seed = self._master.seed
    
    def get(self, name: str) -> SeededRNG:
        """
        Get or create a named RNG stream.
        
        Args:
            name: Name of the RNG stream
            
        Returns:
            SeededRNG instance for the named stream
        """
        if name not in self._streams:
            # Derive a seed from the master RNG
            derived_seed = self._master.randint(0, 2**32 - 1)
            self._streams[name] = SeededRNG(seed=derived_seed, name=name)
        return self._streams[name]
    
    def reset_all(self) -> None:
        """Reset all RNG streams to their initial states."""
        self._master.reset()
        self._streams.clear()
    
    def get_state(self) -> dict:
        """Get state of all RNG streams."""
        return {
            'master_seed': self.master_seed,
            'master': self._master.get_state(),
            'streams': {name: rng.get_state() for name, rng in self._streams.items()}
        }
    
    def __repr__(self) -> str:
        streams = ', '.join(self._streams.keys())
        return f"RNGManager(master_seed={self.master_seed}, streams=[{streams}])"
