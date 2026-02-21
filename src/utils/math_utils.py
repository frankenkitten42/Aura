"""
Mathematical utility functions for the Living Soundscape Engine.

These functions are used throughout the engine for value manipulation,
interpolation, and smoothing operations.
"""

from typing import Union

Number = Union[int, float]


def clamp(value: Number, min_val: Number, max_val: Number) -> Number:
    """
    Constrain a value to a range.
    
    Args:
        value: The value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        The clamped value
        
    Example:
        >>> clamp(1.5, 0.0, 1.0)
        1.0
        >>> clamp(-0.5, 0.0, 1.0)
        0.0
        >>> clamp(0.5, 0.0, 1.0)
        0.5
    """
    return max(min_val, min(max_val, value))


def lerp(a: Number, b: Number, t: float) -> float:
    """
    Linear interpolation between two values.
    
    Args:
        a: Start value
        b: End value
        t: Interpolation factor (0.0 = a, 1.0 = b)
        
    Returns:
        Interpolated value
        
    Example:
        >>> lerp(0.0, 10.0, 0.5)
        5.0
        >>> lerp(0.0, 10.0, 0.25)
        2.5
    """
    return a + (b - a) * t


def inverse_lerp(a: Number, b: Number, value: Number) -> float:
    """
    Inverse linear interpolation - find t given a value between a and b.
    
    Args:
        a: Start value
        b: End value
        value: The value to find t for
        
    Returns:
        The interpolation factor t (may be outside 0-1 if value is outside range)
        
    Example:
        >>> inverse_lerp(0.0, 10.0, 5.0)
        0.5
        >>> inverse_lerp(0.0, 10.0, 2.5)
        0.25
    """
    if b - a == 0:
        return 0.0
    return (value - a) / (b - a)


def smoothstep(edge0: Number, edge1: Number, x: Number) -> float:
    """
    Smooth Hermite interpolation between 0 and 1.
    
    Returns 0 if x <= edge0, 1 if x >= edge1, and smooth interpolation
    between for values in between. Useful for smooth transitions.
    
    Args:
        edge0: Lower edge of transition
        edge1: Upper edge of transition
        x: Input value
        
    Returns:
        Smoothly interpolated value between 0 and 1
        
    Example:
        >>> smoothstep(0.0, 1.0, 0.0)
        0.0
        >>> smoothstep(0.0, 1.0, 0.5)
        0.5
        >>> smoothstep(0.0, 1.0, 1.0)
        1.0
    """
    t = clamp((x - edge0) / (edge1 - edge0) if edge1 != edge0 else 0.0, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def exp_smooth(current: float, target: float, factor: float) -> float:
    """
    Exponential smoothing for gradual value changes.
    
    This is the smoothing function used for SDI calculations to prevent
    jarring changes in the discomfort index.
    
    Args:
        current: Current value
        target: Target value to move towards
        factor: Smoothing factor (0.0-1.0, lower = slower smoothing)
        
    Returns:
        New smoothed value
        
    Example:
        >>> exp_smooth(0.0, 1.0, 0.2)
        0.2
        >>> exp_smooth(0.2, 1.0, 0.2)
        0.36
    """
    return current + (target - current) * factor


def remap(value: Number, in_min: Number, in_max: Number, 
          out_min: Number, out_max: Number) -> float:
    """
    Remap a value from one range to another.
    
    Args:
        value: Input value
        in_min: Input range minimum
        in_max: Input range maximum
        out_min: Output range minimum
        out_max: Output range maximum
        
    Returns:
        Value remapped to output range
        
    Example:
        >>> remap(0.5, 0.0, 1.0, 0.0, 100.0)
        50.0
        >>> remap(50, 0, 100, -1.0, 1.0)
        0.0
    """
    t = inverse_lerp(in_min, in_max, value)
    return lerp(out_min, out_max, t)


def weighted_average(values: list, weights: list) -> float:
    """
    Calculate weighted average of values.
    
    Args:
        values: List of values
        weights: List of weights (same length as values)
        
    Returns:
        Weighted average
        
    Example:
        >>> weighted_average([1.0, 2.0, 3.0], [1, 1, 1])
        2.0
        >>> weighted_average([1.0, 2.0], [1, 3])
        1.75
    """
    if not values or not weights:
        return 0.0
    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")
    
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def variance(values: list) -> float:
    """
    Calculate variance of a list of values.
    
    Used for pattern detection to measure rhythm consistency.
    
    Args:
        values: List of numeric values
        
    Returns:
        Variance of the values
        
    Example:
        >>> variance([1, 2, 3, 4, 5])
        2.0
    """
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


def coefficient_of_variation(values: list) -> float:
    """
    Calculate coefficient of variation (CV) - standard deviation / mean.
    
    Useful for measuring relative variability in pattern intervals.
    Returns 0 if mean is 0 or list is too short.
    
    Args:
        values: List of numeric values
        
    Returns:
        Coefficient of variation (0.0 to inf, lower = more consistent)
        
    Example:
        >>> coefficient_of_variation([10, 10, 10])  # Perfect consistency
        0.0
        >>> coefficient_of_variation([5, 10, 15])  # Some variation
        0.408...
    """
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    
    var = variance(values)
    std_dev = var ** 0.5
    return std_dev / mean
