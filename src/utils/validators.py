"""
Input validation helpers for the Living Soundscape Engine.

Provides validation functions for configuration data, runtime inputs,
and state consistency checks.
"""

from typing import Any, List, Optional, Set


class ValidationError(Exception):
    """Raised when validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(f"{field}: {message}" if field else message)


def validate_range(value: float, min_val: float, max_val: float, 
                   field: str = "value") -> float:
    """
    Validate that a value is within a range.
    
    Args:
        value: Value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        field: Field name for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is outside range
    """
    if not min_val <= value <= max_val:
        raise ValidationError(
            f"must be between {min_val} and {max_val}, got {value}",
            field
        )
    return value


def validate_probability(value: float, field: str = "probability") -> float:
    """
    Validate that a value is a valid probability (0.0 to 1.0).
    
    Args:
        value: Value to validate
        field: Field name for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is not a valid probability
    """
    return validate_range(value, 0.0, 1.0, field)


def validate_sdi(value: float, field: str = "sdi") -> float:
    """
    Validate that a value is a valid SDI value (-1.0 to 1.0).
    
    Args:
        value: Value to validate
        field: Field name for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is not a valid SDI
    """
    return validate_range(value, -1.0, 1.0, field)


def validate_positive(value: float, field: str = "value", 
                      allow_zero: bool = True) -> float:
    """
    Validate that a value is positive (or non-negative).
    
    Args:
        value: Value to validate
        field: Field name for error messages
        allow_zero: Whether zero is allowed
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is negative (or zero if not allowed)
    """
    if allow_zero:
        if value < 0:
            raise ValidationError(f"must be non-negative, got {value}", field)
    else:
        if value <= 0:
            raise ValidationError(f"must be positive, got {value}", field)
    return value


def validate_not_empty(value: Any, field: str = "value") -> Any:
    """
    Validate that a value is not empty (for strings, lists, dicts).
    
    Args:
        value: Value to validate
        field: Field name for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is empty or None
    """
    if value is None:
        raise ValidationError("cannot be None", field)
    if hasattr(value, '__len__') and len(value) == 0:
        raise ValidationError("cannot be empty", field)
    return value


def validate_in_set(value: Any, valid_values: Set[Any], 
                    field: str = "value") -> Any:
    """
    Validate that a value is in a set of valid values.
    
    Args:
        value: Value to validate
        valid_values: Set of allowed values
        field: Field name for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is not in valid_values
    """
    if value not in valid_values:
        valid_str = ', '.join(str(v) for v in sorted(valid_values, key=str))
        raise ValidationError(
            f"must be one of [{valid_str}], got '{value}'",
            field
        )
    return value


def validate_id_exists(sound_id: str, valid_ids: Set[str], 
                       field: str = "sound_id") -> str:
    """
    Validate that a sound ID exists in the configuration.
    
    Args:
        sound_id: Sound ID to validate
        valid_ids: Set of valid sound IDs
        field: Field name for error messages
        
    Returns:
        The validated sound ID
        
    Raises:
        ValidationError: If sound ID doesn't exist
    """
    if sound_id not in valid_ids:
        raise ValidationError(f"unknown sound ID '{sound_id}'", field)
    return sound_id


def validate_biome_id(biome_id: str, valid_ids: Set[str],
                      field: str = "biome_id") -> str:
    """
    Validate that a biome ID exists in the configuration.
    
    Args:
        biome_id: Biome ID to validate
        valid_ids: Set of valid biome IDs
        field: Field name for error messages
        
    Returns:
        The validated biome ID
        
    Raises:
        ValidationError: If biome ID doesn't exist
    """
    if biome_id not in valid_ids:
        raise ValidationError(f"unknown biome ID '{biome_id}'", field)
    return biome_id


def validate_list_length(items: List, min_length: int = 0, 
                         max_length: Optional[int] = None,
                         field: str = "list") -> List:
    """
    Validate that a list has an acceptable length.
    
    Args:
        items: List to validate
        min_length: Minimum required length
        max_length: Maximum allowed length (None for unlimited)
        field: Field name for error messages
        
    Returns:
        The validated list
        
    Raises:
        ValidationError: If list length is out of bounds
    """
    if len(items) < min_length:
        raise ValidationError(
            f"must have at least {min_length} items, got {len(items)}",
            field
        )
    if max_length is not None and len(items) > max_length:
        raise ValidationError(
            f"must have at most {max_length} items, got {len(items)}",
            field
        )
    return items


def validate_type(value: Any, expected_type: type, 
                  field: str = "value") -> Any:
    """
    Validate that a value is of the expected type.
    
    Args:
        value: Value to validate
        expected_type: Expected type (or tuple of types)
        field: Field name for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValidationError: If value is not of expected type
    """
    if not isinstance(value, expected_type):
        type_name = expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)
        raise ValidationError(
            f"must be {type_name}, got {type(value).__name__}",
            field
        )
    return value


# Valid enum values for quick validation
VALID_LAYERS = {'background', 'periodic', 'reactive', 'anomalous'}
VALID_FREQUENCY_BANDS = {'low', 'low_mid', 'mid', 'mid_high', 'high', 'full'}
VALID_TIME_OF_DAY = {'dawn', 'day', 'dusk', 'night', 'midnight', 'all'}
VALID_WEATHER = {'clear', 'cloudy', 'rain', 'storm', 'fog', 'wind'}
VALID_END_TYPES = {'natural', 'fade_out', 'interrupted', 'forced'}
VALID_DELTA_CATEGORIES = {'none', 'small', 'medium', 'large', 'critical'}


def validate_layer(layer: str, field: str = "layer") -> str:
    """Validate a sound layer value."""
    return validate_in_set(layer, VALID_LAYERS, field)


def validate_frequency_band(band: str, field: str = "frequency_band") -> str:
    """Validate a frequency band value."""
    return validate_in_set(band, VALID_FREQUENCY_BANDS, field)


def validate_time_of_day(time: str, field: str = "time_of_day") -> str:
    """Validate a time of day value."""
    return validate_in_set(time, VALID_TIME_OF_DAY, field)


def validate_weather(weather: str, field: str = "weather") -> str:
    """Validate a weather value."""
    return validate_in_set(weather, VALID_WEATHER, field)
