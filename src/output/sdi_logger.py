"""
SDI logging for the Living Soundscape Engine.

Captures and stores SDI calculations for analysis and debugging.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import csv
import io
import json


@dataclass
class SDIRecord:
    """
    A single SDI calculation record.
    
    Captures the full state of SDI calculation at a point in time.
    """
    timestamp: float
    
    # Core SDI values
    raw_sdi: float = 0.0
    smoothed_sdi: float = 0.0
    target_sdi: float = 0.0
    delta: float = 0.0
    delta_category: str = "none"
    
    # Environment
    biome_id: str = ""
    time_of_day: str = ""
    weather: str = ""
    population: float = 0.0
    
    # Active sounds
    active_sounds: int = 0
    active_by_layer: Dict[str, int] = field(default_factory=dict)
    
    # Discomfort factors
    discomfort_total: float = 0.0
    density_overload: float = 0.0
    layer_conflict: float = 0.0
    rhythm_instability: float = 0.0
    silence_deprivation: float = 0.0
    contextual_mismatch: float = 0.0
    persistence: float = 0.0
    absence_after_pattern: float = 0.0
    
    # Comfort factors
    comfort_total: float = 0.0
    predictable_rhythm: float = 0.0
    appropriate_silence: float = 0.0
    layer_harmony: float = 0.0
    gradual_transition: float = 0.0
    resolution: float = 0.0
    environmental_coherence: float = 0.0
    
    # Baselines/modifiers
    biome_baseline: float = 0.0
    time_modifier: float = 0.0
    weather_modifier: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'raw_sdi': self.raw_sdi,
            'smoothed_sdi': self.smoothed_sdi,
            'target_sdi': self.target_sdi,
            'delta': self.delta,
            'delta_category': self.delta_category,
            'biome_id': self.biome_id,
            'time_of_day': self.time_of_day,
            'weather': self.weather,
            'population': self.population,
            'active_sounds': self.active_sounds,
            'discomfort_total': self.discomfort_total,
            'density_overload': self.density_overload,
            'layer_conflict': self.layer_conflict,
            'rhythm_instability': self.rhythm_instability,
            'silence_deprivation': self.silence_deprivation,
            'contextual_mismatch': self.contextual_mismatch,
            'persistence': self.persistence,
            'absence_after_pattern': self.absence_after_pattern,
            'comfort_total': self.comfort_total,
            'predictable_rhythm': self.predictable_rhythm,
            'appropriate_silence': self.appropriate_silence,
            'layer_harmony': self.layer_harmony,
            'gradual_transition': self.gradual_transition,
            'resolution': self.resolution,
            'environmental_coherence': self.environmental_coherence,
            'biome_baseline': self.biome_baseline,
            'time_modifier': self.time_modifier,
            'weather_modifier': self.weather_modifier,
        }
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to CSV row."""
        return self.to_dict()


class SDILogger:
    """
    Logs and stores SDI calculations.
    
    Features:
    - Time-series SDI recording
    - Factor breakdown tracking
    - Statistical analysis
    - CSV/JSON export
    - Trend detection
    
    Example:
        >>> logger = SDILogger(sample_interval=1.0)
        >>> logger.log(timestamp, sdi_result, environment, active_count)
        >>> 
        >>> # Analysis
        >>> avg = logger.get_average_sdi()
        >>> range_info = logger.get_sdi_range()
        >>> 
        >>> # Export
        >>> csv_data = logger.to_csv()
    """
    
    # CSV column order
    CSV_COLUMNS = [
        'timestamp', 'raw_sdi', 'smoothed_sdi', 'target_sdi', 'delta', 
        'delta_category', 'biome_id', 'time_of_day', 'weather', 'population',
        'active_sounds', 'discomfort_total', 'comfort_total',
        'density_overload', 'layer_conflict', 'rhythm_instability',
        'silence_deprivation', 'contextual_mismatch', 'persistence',
        'absence_after_pattern', 'predictable_rhythm', 'appropriate_silence',
        'layer_harmony', 'gradual_transition', 'resolution', 
        'environmental_coherence', 'biome_baseline', 'time_modifier',
        'weather_modifier'
    ]
    
    def __init__(self, sample_interval: float = 1.0, max_records: int = 10000):
        """
        Initialize the SDI logger.
        
        Args:
            sample_interval: Minimum time between samples (0 = log everything)
            max_records: Maximum records to store
        """
        self.sample_interval = sample_interval
        self.max_records = max_records
        
        self._records: List[SDIRecord] = []
        self._last_sample_time: float = -float('inf')
        
        # Running statistics
        self._sum_sdi: float = 0.0
        self._sum_sdi_sq: float = 0.0
        self._min_sdi: float = float('inf')
        self._max_sdi: float = float('-inf')
        self._total_samples: int = 0
    
    def log(self, timestamp: float, sdi_result: Any, 
            environment: Any = None, active_count: int = 0,
            active_by_layer: Dict[str, int] = None) -> Optional[SDIRecord]:
        """
        Log an SDI calculation.
        
        Args:
            timestamp: Simulation time
            sdi_result: SDIResult object from calculator
            environment: Current environment state
            active_count: Number of active sounds
            active_by_layer: Active sounds per layer
            
        Returns:
            SDIRecord if logged, None if skipped due to interval
        """
        # Check sample interval
        if timestamp - self._last_sample_time < self.sample_interval:
            return None
        
        self._last_sample_time = timestamp
        
        # Extract environment info
        biome_id = ""
        time_of_day = ""
        weather = ""
        population = 0.0
        
        if environment is not None:
            biome_id = getattr(environment, 'biome_id', '')
            time_of_day = getattr(environment, 'time_of_day', '')
            weather = getattr(environment, 'weather', '')
            population = getattr(environment, 'population_ratio', 0.0)
        
        # Extract SDI result values
        discomfort = getattr(sdi_result, 'discomfort', None)
        comfort = getattr(sdi_result, 'comfort', None)
        
        record = SDIRecord(
            timestamp=timestamp,
            raw_sdi=sdi_result.raw_sdi,
            smoothed_sdi=sdi_result.smoothed_sdi,
            target_sdi=sdi_result.target_sdi,
            delta=sdi_result.delta,
            delta_category=sdi_result.delta_category,
            biome_id=biome_id,
            time_of_day=time_of_day,
            weather=weather,
            population=population,
            active_sounds=active_count,
            active_by_layer=active_by_layer or {},
            biome_baseline=sdi_result.biome_baseline,
            time_modifier=sdi_result.time_modifier,
            weather_modifier=sdi_result.weather_modifier,
        )
        
        # Extract discomfort factors
        if discomfort:
            record.discomfort_total = discomfort.total
            record.density_overload = discomfort.density_overload
            record.layer_conflict = discomfort.layer_conflict
            record.rhythm_instability = discomfort.rhythm_instability
            record.silence_deprivation = discomfort.silence_deprivation
            record.contextual_mismatch = discomfort.contextual_mismatch
            record.persistence = discomfort.persistence
            record.absence_after_pattern = discomfort.absence_after_pattern
        
        # Extract comfort factors
        if comfort:
            record.comfort_total = comfort.total
            record.predictable_rhythm = comfort.predictable_rhythm
            record.appropriate_silence = comfort.appropriate_silence
            record.layer_harmony = comfort.layer_harmony
            record.gradual_transition = comfort.gradual_transition
            record.resolution = comfort.resolution
            record.environmental_coherence = comfort.environmental_coherence
        
        # Store record
        self._records.append(record)
        
        if len(self._records) > self.max_records:
            self._records = self._records[-self.max_records:]
        
        # Update running stats
        sdi = record.smoothed_sdi
        self._sum_sdi += sdi
        self._sum_sdi_sq += sdi * sdi
        self._min_sdi = min(self._min_sdi, sdi)
        self._max_sdi = max(self._max_sdi, sdi)
        self._total_samples += 1
        
        return record
    
    def log_raw(self, timestamp: float, smoothed_sdi: float, 
                target_sdi: float = 0.0, delta: float = 0.0) -> SDIRecord:
        """Log SDI from raw values (minimal logging)."""
        record = SDIRecord(
            timestamp=timestamp,
            smoothed_sdi=smoothed_sdi,
            target_sdi=target_sdi,
            delta=delta,
        )
        
        self._records.append(record)
        
        if len(self._records) > self.max_records:
            self._records = self._records[-self.max_records:]
        
        self._sum_sdi += smoothed_sdi
        self._sum_sdi_sq += smoothed_sdi * smoothed_sdi
        self._min_sdi = min(self._min_sdi, smoothed_sdi)
        self._max_sdi = max(self._max_sdi, smoothed_sdi)
        self._total_samples += 1
        
        return record
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_all(self) -> List[SDIRecord]:
        """Get all stored records."""
        return list(self._records)
    
    def get_recent(self, count: int = 10) -> List[SDIRecord]:
        """Get most recent records."""
        return self._records[-count:]
    
    def get_in_range(self, start_time: float, end_time: float) -> List[SDIRecord]:
        """Get records within a time range."""
        return [r for r in self._records if start_time <= r.timestamp <= end_time]
    
    def get_sdi_values(self) -> List[float]:
        """Get list of smoothed SDI values."""
        return [r.smoothed_sdi for r in self._records]
    
    def get_timestamps(self) -> List[float]:
        """Get list of timestamps."""
        return [r.timestamp for r in self._records]
    
    def get_timeline(self) -> List[tuple]:
        """Get (timestamp, sdi) pairs."""
        return [(r.timestamp, r.smoothed_sdi) for r in self._records]
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    @property
    def count(self) -> int:
        """Get number of stored records."""
        return len(self._records)
    
    def get_average_sdi(self) -> float:
        """Get average SDI across all samples."""
        if self._total_samples == 0:
            return 0.0
        return self._sum_sdi / self._total_samples
    
    def get_sdi_range(self) -> Dict[str, float]:
        """Get SDI range statistics."""
        if self._total_samples == 0:
            return {'min': 0.0, 'max': 0.0, 'range': 0.0}
        return {
            'min': self._min_sdi,
            'max': self._max_sdi,
            'range': self._max_sdi - self._min_sdi,
        }
    
    def get_variance(self) -> float:
        """Get SDI variance."""
        if self._total_samples < 2:
            return 0.0
        mean = self._sum_sdi / self._total_samples
        mean_sq = self._sum_sdi_sq / self._total_samples
        return mean_sq - mean * mean
    
    def get_std_dev(self) -> float:
        """Get SDI standard deviation."""
        import math
        return math.sqrt(max(0, self.get_variance()))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            'total_samples': self._total_samples,
            'stored_samples': len(self._records),
            'average_sdi': self.get_average_sdi(),
            'std_dev': self.get_std_dev(),
            **self.get_sdi_range(),
        }
    
    def get_factor_averages(self) -> Dict[str, float]:
        """Get average values for each factor."""
        if not self._records:
            return {}
        
        n = len(self._records)
        return {
            'density_overload': sum(r.density_overload for r in self._records) / n,
            'layer_conflict': sum(r.layer_conflict for r in self._records) / n,
            'rhythm_instability': sum(r.rhythm_instability for r in self._records) / n,
            'silence_deprivation': sum(r.silence_deprivation for r in self._records) / n,
            'contextual_mismatch': sum(r.contextual_mismatch for r in self._records) / n,
            'persistence': sum(r.persistence for r in self._records) / n,
            'absence_after_pattern': sum(r.absence_after_pattern for r in self._records) / n,
            'predictable_rhythm': sum(r.predictable_rhythm for r in self._records) / n,
            'appropriate_silence': sum(r.appropriate_silence for r in self._records) / n,
            'layer_harmony': sum(r.layer_harmony for r in self._records) / n,
            'gradual_transition': sum(r.gradual_transition for r in self._records) / n,
            'resolution': sum(r.resolution for r in self._records) / n,
            'environmental_coherence': sum(r.environmental_coherence for r in self._records) / n,
        }
    
    def get_top_discomfort_factors(self, count: int = 3) -> List[tuple]:
        """Get factors contributing most to discomfort."""
        avgs = self.get_factor_averages()
        discomfort = {
            'density_overload': avgs.get('density_overload', 0),
            'layer_conflict': avgs.get('layer_conflict', 0),
            'rhythm_instability': avgs.get('rhythm_instability', 0),
            'silence_deprivation': avgs.get('silence_deprivation', 0),
            'contextual_mismatch': avgs.get('contextual_mismatch', 0),
            'persistence': avgs.get('persistence', 0),
            'absence_after_pattern': avgs.get('absence_after_pattern', 0),
        }
        sorted_factors = sorted(discomfort.items(), key=lambda x: -x[1])
        return sorted_factors[:count]
    
    def get_top_comfort_factors(self, count: int = 3) -> List[tuple]:
        """Get factors contributing most to comfort."""
        avgs = self.get_factor_averages()
        comfort = {
            'predictable_rhythm': avgs.get('predictable_rhythm', 0),
            'appropriate_silence': avgs.get('appropriate_silence', 0),
            'layer_harmony': avgs.get('layer_harmony', 0),
            'gradual_transition': avgs.get('gradual_transition', 0),
            'resolution': avgs.get('resolution', 0),
            'environmental_coherence': avgs.get('environmental_coherence', 0),
        }
        sorted_factors = sorted(comfort.items(), key=lambda x: x[1])  # Most negative first
        return sorted_factors[:count]
    
    # =========================================================================
    # Export Methods
    # =========================================================================
    
    def to_csv(self, include_header: bool = True) -> str:
        """Export records to CSV string."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.CSV_COLUMNS,
                                extrasaction='ignore')
        
        if include_header:
            writer.writeheader()
        
        for record in self._records:
            writer.writerow(record.to_csv_row())
        
        return output.getvalue()
    
    def write_csv(self, filepath: str) -> int:
        """Write records to CSV file."""
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS,
                                    extrasaction='ignore')
            writer.writeheader()
            
            for record in self._records:
                writer.writerow(record.to_csv_row())
        
        return len(self._records)
    
    def to_json(self, pretty: bool = False) -> str:
        """Export records to JSON string."""
        data = [r.to_dict() for r in self._records]
        if pretty:
            return json.dumps(data, indent=2)
        return json.dumps(data)
    
    def write_json(self, filepath: str, pretty: bool = True) -> int:
        """Write records to JSON file."""
        with open(filepath, 'w') as f:
            data = [r.to_dict() for r in self._records]
            if pretty:
                json.dump(data, f, indent=2)
            else:
                json.dump(data, f)
        
        return len(self._records)
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    def clear(self) -> None:
        """Clear stored records (keeps running stats)."""
        self._records.clear()
    
    def reset(self) -> None:
        """Reset logger completely."""
        self._records.clear()
        self._last_sample_time = -float('inf')
        self._sum_sdi = 0.0
        self._sum_sdi_sq = 0.0
        self._min_sdi = float('inf')
        self._max_sdi = float('-inf')
        self._total_samples = 0
    
    def __len__(self) -> int:
        return len(self._records)
    
    def __repr__(self) -> str:
        avg = self.get_average_sdi()
        return f"SDILogger(samples={self._total_samples}, avg_sdi={avg:.3f})"
