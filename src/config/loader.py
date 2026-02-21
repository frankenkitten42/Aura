"""
Configuration loader for the Living Soundscape Engine.

Loads JSON configuration files and converts them to typed dataclass objects.
Provides validation and helpful error messages for malformed configs.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from .models import (
    LSEConfig,
    BiomeConfig,
    BiomeParameters,
    BiomeBlend,
    SoundConfig,
    DurationConfig,
    IntensityConfig,
    WeatherConstraints,
    RhythmInterval,
    SDIConfig,
    SDIGlobalSettings,
    SDIFactorConfig,
    PopulationConfig,
    PopulationCurve,
    PopulationPoint,
    DeltaThresholds,
    HysteresisConfig,
    RegionOverride,
    ConflictConfig,
    ConflictPair,
    TagConflict,
    HarmonyPair,
    WeatherModifier,
    TimeOfDayModifier,
)


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""
    
    def __init__(self, message: str, file: Optional[str] = None, 
                 path: Optional[str] = None):
        self.message = message
        self.file = file
        self.path = path
        
        full_msg = message
        if file:
            full_msg = f"[{file}] {full_msg}"
        if path:
            full_msg = f"{full_msg} (at {path})"
        
        super().__init__(full_msg)


class ConfigLoader:
    """
    Loads and parses LSE configuration files.
    
    Usage:
        loader = ConfigLoader("./config")
        config = loader.load_all()
        
        # Or load individual files:
        biomes = loader.load_biomes()
        sounds = loader.load_sounds()
    """
    
    def __init__(self, config_dir: str):
        """
        Initialize the config loader.
        
        Args:
            config_dir: Path to directory containing config JSON files
        """
        self.config_dir = Path(config_dir)
        
        if not self.config_dir.exists():
            raise ConfigError(f"Config directory not found: {config_dir}")
    
    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Load a JSON file from the config directory."""
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            raise ConfigError(f"Config file not found: {filepath}", file=filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON: {e}", file=filename)
    
    def _get(self, data: dict, key: str, default: Any = None, 
             required: bool = False, file: str = "") -> Any:
        """Get a value from a dict with optional requirement check."""
        if key not in data:
            if required:
                raise ConfigError(f"Missing required field: {key}", file=file)
            return default
        return data[key]
    
    # =========================================================================
    # Biome Loading
    # =========================================================================
    
    def load_biomes(self) -> tuple:
        """
        Load biomes.json.
        
        Returns:
            Tuple of (biomes dict, weather modifiers dict, time modifiers dict)
        """
        data = self._load_json("biomes.json")
        
        biomes = {}
        for biome_id, biome_data in data.get("biomes", {}).items():
            biomes[biome_id] = self._parse_biome(biome_id, biome_data)
        
        weather_mods = {}
        for mod_id, mod_data in data.get("weather_modifiers", {}).items():
            weather_mods[mod_id] = self._parse_weather_modifier(mod_id, mod_data)
        
        time_mods = {}
        for mod_id, mod_data in data.get("time_of_day_modifiers", {}).items():
            time_mods[mod_id] = self._parse_time_modifier(mod_id, mod_data)
        
        return biomes, weather_mods, time_mods
    
    def _parse_biome(self, biome_id: str, data: dict) -> BiomeConfig:
        """Parse a single biome configuration."""
        params_data = data.get("parameters", {})
        parameters = BiomeParameters(
            baseline_density=params_data.get("baseline_density", 5.0),
            silence_tolerance=params_data.get("silence_tolerance", 5.0),
            sdi_baseline=params_data.get("sdi_baseline", 0.0),
            frequency_band=params_data.get("frequency_band", "mid"),
            layer_capacity=params_data.get("layer_capacity", 4),
        )
        
        blend = None
        if "blend" in data:
            blend_data = data["blend"]
            blend = BiomeBlend(
                primary=blend_data.get("primary", ""),
                primary_weight=blend_data.get("primary_weight", 0.5),
                secondary=blend_data.get("secondary"),
                secondary_weight=blend_data.get("secondary_weight", 0.5),
                secondary_from_adjacent=blend_data.get("secondary_from_adjacent", False),
            )
        
        return BiomeConfig(
            id=biome_id,
            name=data.get("name", biome_id),
            description=data.get("description", ""),
            parameters=parameters,
            sound_pool=data.get("sound_pool", []),
            tags=data.get("tags", []),
            blend=blend,
        )
    
    def _parse_weather_modifier(self, mod_id: str, data: dict) -> WeatherModifier:
        """Parse a weather modifier."""
        return WeatherModifier(
            id=mod_id,
            density_modifier=data.get("density_modifier", 1.0),
            silence_modifier=data.get("silence_modifier", 1.0),
            sdi_modifier=data.get("sdi_modifier", 0.0),
            adds_sounds=data.get("adds_sounds", []),
            removes_sounds=data.get("removes_sounds", []),
            amplifies_sounds=data.get("amplifies_sounds", []),
        )
    
    def _parse_time_modifier(self, mod_id: str, data: dict) -> TimeOfDayModifier:
        """Parse a time of day modifier."""
        hour_range = data.get("hour_range", [0, 24])
        return TimeOfDayModifier(
            id=mod_id,
            hour_range=tuple(hour_range),
            density_modifier=data.get("density_modifier", 1.0),
            sdi_modifier=data.get("sdi_modifier", 0.0),
            active_tags=data.get("active_tags", []),
            transitions_from=data.get("transitions_from"),
            transitions_to=data.get("transitions_to"),
        )
    
    # =========================================================================
    # Sound Loading
    # =========================================================================
    
    def load_sounds(self) -> Dict[str, SoundConfig]:
        """Load sounds.json."""
        data = self._load_json("sounds.json")
        
        sounds = {}
        for sound_id, sound_data in data.get("sounds", {}).items():
            sounds[sound_id] = self._parse_sound(sound_id, sound_data)
        
        return sounds
    
    def _parse_sound(self, sound_id: str, data: dict) -> SoundConfig:
        """Parse a single sound configuration."""
        duration_data = data.get("duration", {})
        duration = DurationConfig(
            min=duration_data.get("min", 1.0),
            max=duration_data.get("max", 5.0),
            type=duration_data.get("type", "single"),
        )
        
        intensity_data = data.get("intensity", {})
        intensity = IntensityConfig(
            min=intensity_data.get("min", 0.3),
            max=intensity_data.get("max", 0.7),
        )
        
        weather_data = data.get("weather_constraints", {})
        weather = WeatherConstraints(
            required=weather_data.get("required", []),
            excluded=weather_data.get("excluded", []),
            amplified_by=weather_data.get("amplified_by", []),
        )
        
        rhythm_interval = None
        if "rhythm_interval" in data:
            ri_data = data["rhythm_interval"]
            rhythm_interval = RhythmInterval(
                min=ri_data.get("min", 5.0),
                max=ri_data.get("max", 10.0),
            )
        
        return SoundConfig(
            id=sound_id,
            name=data.get("name", sound_id),
            layer=data.get("layer", "periodic"),
            frequency_band=data.get("frequency_band", "mid"),
            base_probability=data.get("base_probability", 0.5),
            time_constraints=data.get("time_constraints", ["all"]),
            weather_constraints=weather,
            duration=duration,
            intensity=intensity,
            cooldown=data.get("cooldown", 5.0),
            natural_duration=data.get("natural_duration"),
            tags=data.get("tags", []),
            rhythm_capable=data.get("rhythm_capable", False),
            is_rhythmic=data.get("is_rhythmic", False),
            is_silence=data.get("is_silence", False),
            reverb=data.get("reverb", False),
            harmony_pairs=data.get("harmony_pairs", []),
            conflict_pairs=data.get("conflict_pairs", []),
            rhythm_interval=rhythm_interval,
            requires_feature=data.get("requires_feature"),
        )
    
    # =========================================================================
    # SDI Loading
    # =========================================================================
    
    def load_sdi(self) -> SDIConfig:
        """Load sdi_factors.json."""
        data = self._load_json("sdi_factors.json")
        
        global_data = data.get("global_settings", {})
        global_settings = SDIGlobalSettings(
            sdi_min=global_data.get("sdi_min", -1.0),
            sdi_max=global_data.get("sdi_max", 1.0),
            operational_max=global_data.get("operational_max", 0.8),
            smoothing_factor=global_data.get("smoothing_factor", 0.2),
            tick_rate=global_data.get("tick_rate", 1.0),
        )
        
        discomfort = {}
        for factor_id, factor_data in data.get("discomfort_factors", {}).items():
            discomfort[factor_id] = self._parse_sdi_factor(factor_id, factor_data)
        
        comfort = {}
        for factor_id, factor_data in data.get("comfort_factors", {}).items():
            comfort[factor_id] = self._parse_sdi_factor(factor_id, factor_data)
        
        biome_adj = data.get("biome_factor_adjustments", {})
        
        return SDIConfig(
            global_settings=global_settings,
            discomfort_factors=discomfort,
            comfort_factors=comfort,
            biome_adjustments=biome_adj,
        )
    
    def _parse_sdi_factor(self, factor_id: str, data: dict) -> SDIFactorConfig:
        """Parse a single SDI factor configuration."""
        return SDIFactorConfig(
            id=factor_id,
            name=data.get("name", factor_id),
            description=data.get("description", ""),
            base_weight=data.get("base_weight", 0.1),
            calculation=data.get("calculation", ""),
            cap=data.get("cap"),
            modifiers=data.get("modifiers", {}),
            detection=data.get("detection", {}),
            formula=data.get("formula"),
            decay_time=data.get("decay_time"),
        )
    
    # =========================================================================
    # Population Loading
    # =========================================================================
    
    def load_population(self) -> PopulationConfig:
        """Load population.json."""
        data = self._load_json("population.json")
        
        # Curve
        curve_data = data.get("population_mapping", {}).get("curve", {})
        points = [
            PopulationPoint(p["population"], p["target_sdi"])
            for p in curve_data.get("points", [])
        ]
        curve = PopulationCurve(
            type=curve_data.get("type", "piecewise_linear"),
            points=points,
        )
        
        # Thresholds
        thresh_data = data.get("adjustment_behavior", {}).get("delta_thresholds", {})
        thresholds = DeltaThresholds(
            small=thresh_data.get("small", 0.1),
            medium=thresh_data.get("medium", 0.2),
            large=thresh_data.get("large", 0.3),
            critical=thresh_data.get("critical", 0.4),
        )
        
        # Hysteresis
        hyst_data = data.get("hysteresis", {})
        hysteresis = HysteresisConfig(
            enabled=hyst_data.get("enabled", True),
            dead_zone=hyst_data.get("dead_zone", 0.05),
            ramp_up_speed=hyst_data.get("ramp_up_speed", 0.1),
            ramp_down_speed=hyst_data.get("ramp_down_speed", 0.15),
            min_hold_time=hyst_data.get("min_hold_time", 5.0),
        )
        
        # Region overrides
        overrides = {}
        for region_id, override_data in data.get("region_overrides", {}).items():
            # Skip description fields
            if region_id.startswith('_'):
                continue
            overrides[region_id] = RegionOverride(
                curve_modifier=override_data.get("curve_modifier", 0.0),
                min_sdi=override_data.get("min_sdi", -1.0),
                max_sdi=override_data.get("max_sdi", 1.0),
                fixed_sdi=override_data.get("fixed_sdi"),
                ignore_population=override_data.get("ignore_population", False),
                reason=override_data.get("reason", ""),
            )
        
        # Actions (filter out description fields)
        adj_behavior = data.get("adjustment_behavior", {})
        increase_raw = adj_behavior.get("increase_sdi_actions", {})
        decrease_raw = adj_behavior.get("decrease_sdi_actions", {})
        
        increase_actions = {k: v for k, v in increase_raw.items() if not k.startswith('_')}
        decrease_actions = {k: v for k, v in decrease_raw.items() if not k.startswith('_')}
        
        return PopulationConfig(
            curve=curve,
            delta_thresholds=thresholds,
            hysteresis=hysteresis,
            region_overrides=overrides,
            increase_actions=increase_actions,
            decrease_actions=decrease_actions,
        )
    
    # =========================================================================
    # Conflicts Loading
    # =========================================================================
    
    def load_conflicts(self) -> ConflictConfig:
        """Load conflicts.json."""
        data = self._load_json("conflicts.json")
        
        # Sound conflicts
        sound_conflicts = []
        for conflict in data.get("conflicts", {}).get("by_sound_id", []):
            sound_conflicts.append(ConflictPair(
                sound_a=conflict["sound_a"],
                sound_b=conflict["sound_b"],
                severity=conflict.get("severity", "medium"),
                reason=conflict.get("reason", ""),
            ))
        
        # Tag conflicts
        tag_conflicts = []
        for conflict in data.get("conflicts", {}).get("by_tag", []):
            tag_conflicts.append(TagConflict(
                tag_a=conflict["tag_a"],
                tag_b=conflict["tag_b"],
                severity=conflict.get("severity", "medium"),
                reason=conflict.get("reason", ""),
            ))
        
        # Harmony pairs
        harmony_pairs = []
        for harmony in data.get("harmony", {}).get("pairs", []):
            harmony_pairs.append(HarmonyPair(
                sound_a=harmony["sound_a"],
                sound_b=harmony["sound_b"],
                strength=harmony.get("strength", "medium"),
                context=harmony.get("context", ""),
            ))
        
        # Time/weather violations
        time_violations = data.get("time_conflicts", {}).get("violations", [])
        weather_violations = data.get("weather_conflicts", {}).get("violations", [])
        
        return ConflictConfig(
            sound_conflicts=sound_conflicts,
            tag_conflicts=tag_conflicts,
            harmony_pairs=harmony_pairs,
            time_violations=time_violations,
            weather_violations=weather_violations,
        )
    
    # =========================================================================
    # Load All
    # =========================================================================
    
    def load_all(self) -> LSEConfig:
        """
        Load all configuration files and return a complete LSEConfig.
        
        Returns:
            Fully populated LSEConfig object
            
        Raises:
            ConfigError: If any config file is missing or malformed
        """
        biomes, weather_mods, time_mods = self.load_biomes()
        sounds = self.load_sounds()
        sdi = self.load_sdi()
        population = self.load_population()
        conflicts = self.load_conflicts()
        
        config = LSEConfig(
            biomes=biomes,
            sounds=sounds,
            sdi=sdi,
            population=population,
            conflicts=conflicts,
            weather_modifiers=weather_mods,
            time_modifiers=time_mods,
        )
        
        # Validate cross-references
        self._validate_references(config)
        
        return config
    
    def _validate_references(self, config: LSEConfig) -> None:
        """Validate that all ID references are valid."""
        valid_sounds = config.get_valid_sound_ids()
        valid_biomes = config.get_valid_biome_ids()
        
        # Check biome sound pools
        for biome_id, biome in config.biomes.items():
            for sound_id in biome.sound_pool:
                if sound_id not in valid_sounds:
                    raise ConfigError(
                        f"Biome '{biome_id}' references unknown sound: {sound_id}",
                        file="biomes.json"
                    )
        
        # Check harmony/conflict pairs
        for pair in config.conflicts.sound_conflicts:
            if pair.sound_a not in valid_sounds:
                raise ConfigError(
                    f"Conflict references unknown sound: {pair.sound_a}",
                    file="conflicts.json"
                )
            if pair.sound_b not in valid_sounds:
                raise ConfigError(
                    f"Conflict references unknown sound: {pair.sound_b}",
                    file="conflicts.json"
                )
        
        for pair in config.conflicts.harmony_pairs:
            if pair.sound_a not in valid_sounds:
                raise ConfigError(
                    f"Harmony pair references unknown sound: {pair.sound_a}",
                    file="conflicts.json"
                )
            if pair.sound_b not in valid_sounds:
                raise ConfigError(
                    f"Harmony pair references unknown sound: {pair.sound_b}",
                    file="conflicts.json"
                )


def load_config(config_dir: str) -> LSEConfig:
    """
    Convenience function to load all configuration.
    
    Args:
        config_dir: Path to config directory
        
    Returns:
        Fully populated LSEConfig object
    """
    loader = ConfigLoader(config_dir)
    return loader.load_all()
