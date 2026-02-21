"""
VDE Phase 4: NPC Modulation System

NPCs provide social proof - their discomfort is contagious.

This module handles:
- NPC comfort levels based on population
- Per-type behavior modulation (Vendor, Guard, Ambient)
- Idle behavior repertoire management
- Repositioning frequency
- Interaction radius changes
- Social clustering at region edges
- UE5-ready behavior commands

Key insight: Players read NPC behavior subconsciously. Uncomfortable NPCs
make players uncomfortable without any explicit messaging.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum, Flag, auto
import math
import random


# =============================================================================
# Enums and Constants
# =============================================================================

class NPCType(Enum):
    """Types of NPCs with different behavior profiles."""
    VENDOR = "vendor"           # Shop keepers, merchants
    GUARD = "guard"             # Guards, soldiers, watchmen
    AMBIENT = "ambient"         # General townsfolk
    WORKER = "worker"           # Craftsmen, laborers
    NOBLE = "noble"             # Upper class, officials
    CHILD = "child"             # Children (most sensitive to crowds)
    ELDER = "elder"             # Elderly NPCs
    ENTERTAINER = "entertainer" # Bards, performers


class ComfortLevel(Enum):
    """NPC comfort levels based on population."""
    RELAXED = "relaxed"         # Pop 0-20%: Full comfort
    COMFORTABLE = "comfortable" # Pop 20-40%: Mostly comfortable
    UNEASY = "uneasy"           # Pop 40-60%: Starting to feel crowded
    STRESSED = "stressed"       # Pop 60-80%: Clearly uncomfortable
    OVERWHELMED = "overwhelmed" # Pop 80%+: Maximum discomfort


class IdleBehavior(Flag):
    """Idle behavior flags - can be combined."""
    NONE = 0
    
    # Stationary behaviors
    STAND = auto()              # Basic standing
    STAND_SHIFT = auto()        # Standing with weight shifts
    LEAN = auto()               # Leaning against objects
    SIT = auto()                # Sitting on benches/ground
    KNEEL = auto()              # Kneeling
    
    # Active behaviors  
    STRETCH = auto()            # Stretching, yawning
    LOOK_AROUND = auto()        # Looking around casually
    FIDGET = auto()             # Nervous fidgeting
    CHECK_ITEMS = auto()        # Checking belongings
    
    # Social behaviors
    CHAT = auto()               # Talking to nearby NPCs
    WAVE = auto()               # Waving, greeting
    LAUGH = auto()              # Laughing, smiling
    ARGUE = auto()              # Heated discussion
    
    # Comfort behaviors
    EAT = auto()                # Eating, drinking
    SMOKE = auto()              # Smoking pipe
    READ = auto()               # Reading book/scroll
    SLEEP = auto()              # Dozing off
    
    # Activity behaviors
    WORK = auto()               # Type-specific work
    PATROL = auto()             # Walking patrol route
    BROWSE = auto()             # Looking at wares
    PLAY = auto()               # Playing (children)
    
    # All behaviors combined
    ALL = (STAND | STAND_SHIFT | LEAN | SIT | KNEEL | STRETCH | 
           LOOK_AROUND | FIDGET | CHECK_ITEMS | CHAT | WAVE | LAUGH |
           ARGUE | EAT | SMOKE | READ | SLEEP | WORK | PATROL | BROWSE | PLAY)


class RepositionReason(Enum):
    """Why an NPC is repositioning."""
    NONE = "none"
    COMFORT = "comfort"         # Finding more comfortable spot
    CROWDING = "crowding"       # Too many people nearby
    EDGE_SEEKING = "edge"       # Moving toward region edges
    SOCIAL = "social"           # Moving toward/away from others
    PATROL = "patrol"           # Normal patrol behavior
    RANDOM = "random"           # Random movement


# =============================================================================
# Behavior Profiles per NPC Type
# =============================================================================

@dataclass
class NPCBehaviorProfile:
    """Behavior profile for an NPC type."""
    npc_type: NPCType
    
    # Idle behaviors available at each comfort level
    idle_behaviors: Dict[ComfortLevel, IdleBehavior] = field(default_factory=dict)
    
    # Base interaction radius (cm)
    base_interaction_radius: float = 200.0
    
    # How sensitive to crowds (multiplier)
    crowd_sensitivity: float = 1.0
    
    # Preferred position (0 = center, 1 = edges)
    edge_preference_base: float = 0.0
    
    # Can this NPC leave entirely when overwhelmed?
    can_leave: bool = False
    
    # Work-related settings
    has_station: bool = False  # Tied to a specific location
    station_radius: float = 100.0  # How far they'll move from station


# Default profiles per NPC type
DEFAULT_PROFILES: Dict[NPCType, NPCBehaviorProfile] = {
    NPCType.VENDOR: NPCBehaviorProfile(
        npc_type=NPCType.VENDOR,
        idle_behaviors={
            ComfortLevel.RELAXED: (
                IdleBehavior.STAND | IdleBehavior.LEAN | IdleBehavior.CHAT |
                IdleBehavior.WAVE | IdleBehavior.LAUGH | IdleBehavior.EAT |
                IdleBehavior.WORK | IdleBehavior.STRETCH
            ),
            ComfortLevel.COMFORTABLE: (
                IdleBehavior.STAND | IdleBehavior.STAND_SHIFT | IdleBehavior.CHAT |
                IdleBehavior.WAVE | IdleBehavior.WORK | IdleBehavior.LOOK_AROUND
            ),
            ComfortLevel.UNEASY: (
                IdleBehavior.STAND | IdleBehavior.STAND_SHIFT | IdleBehavior.WORK |
                IdleBehavior.LOOK_AROUND | IdleBehavior.CHECK_ITEMS
            ),
            ComfortLevel.STRESSED: (
                IdleBehavior.STAND | IdleBehavior.FIDGET | IdleBehavior.WORK |
                IdleBehavior.CHECK_ITEMS
            ),
            ComfortLevel.OVERWHELMED: (
                IdleBehavior.STAND | IdleBehavior.FIDGET
            ),
        },
        base_interaction_radius=250.0,
        crowd_sensitivity=0.8,  # Vendors tolerate crowds better
        has_station=True,
        station_radius=150.0,
    ),
    
    NPCType.GUARD: NPCBehaviorProfile(
        npc_type=NPCType.GUARD,
        idle_behaviors={
            ComfortLevel.RELAXED: (
                IdleBehavior.STAND | IdleBehavior.PATROL | IdleBehavior.LEAN |
                IdleBehavior.CHAT | IdleBehavior.LOOK_AROUND | IdleBehavior.STRETCH
            ),
            ComfortLevel.COMFORTABLE: (
                IdleBehavior.STAND | IdleBehavior.PATROL | IdleBehavior.LOOK_AROUND |
                IdleBehavior.STAND_SHIFT
            ),
            ComfortLevel.UNEASY: (
                IdleBehavior.STAND | IdleBehavior.LOOK_AROUND | IdleBehavior.STAND_SHIFT
            ),
            ComfortLevel.STRESSED: (
                IdleBehavior.STAND | IdleBehavior.LOOK_AROUND
            ),
            ComfortLevel.OVERWHELMED: (
                IdleBehavior.STAND  # Alert, stationary
            ),
        },
        base_interaction_radius=300.0,
        crowd_sensitivity=0.6,  # Guards are trained for crowds
        has_station=True,
        station_radius=500.0,  # Larger patrol area
    ),
    
    NPCType.AMBIENT: NPCBehaviorProfile(
        npc_type=NPCType.AMBIENT,
        idle_behaviors={
            ComfortLevel.RELAXED: (
                IdleBehavior.ALL  # Full repertoire
            ),
            ComfortLevel.COMFORTABLE: (
                IdleBehavior.STAND | IdleBehavior.SIT | IdleBehavior.LEAN |
                IdleBehavior.CHAT | IdleBehavior.LOOK_AROUND | IdleBehavior.BROWSE |
                IdleBehavior.WAVE | IdleBehavior.STRETCH
            ),
            ComfortLevel.UNEASY: (
                IdleBehavior.STAND | IdleBehavior.STAND_SHIFT | IdleBehavior.LOOK_AROUND |
                IdleBehavior.BROWSE | IdleBehavior.CHECK_ITEMS
            ),
            ComfortLevel.STRESSED: (
                IdleBehavior.STAND | IdleBehavior.STAND_SHIFT | IdleBehavior.FIDGET |
                IdleBehavior.CHECK_ITEMS
            ),
            ComfortLevel.OVERWHELMED: (
                IdleBehavior.STAND | IdleBehavior.FIDGET
            ),
        },
        base_interaction_radius=200.0,
        crowd_sensitivity=1.0,
        can_leave=True,  # Ambient NPCs can leave
    ),
    
    NPCType.WORKER: NPCBehaviorProfile(
        npc_type=NPCType.WORKER,
        idle_behaviors={
            ComfortLevel.RELAXED: (
                IdleBehavior.STAND | IdleBehavior.SIT | IdleBehavior.WORK |
                IdleBehavior.CHAT | IdleBehavior.EAT | IdleBehavior.STRETCH |
                IdleBehavior.SMOKE
            ),
            ComfortLevel.COMFORTABLE: (
                IdleBehavior.STAND | IdleBehavior.WORK | IdleBehavior.CHAT |
                IdleBehavior.LOOK_AROUND
            ),
            ComfortLevel.UNEASY: (
                IdleBehavior.STAND | IdleBehavior.WORK | IdleBehavior.LOOK_AROUND
            ),
            ComfortLevel.STRESSED: (
                IdleBehavior.STAND | IdleBehavior.WORK | IdleBehavior.FIDGET
            ),
            ComfortLevel.OVERWHELMED: (
                IdleBehavior.STAND | IdleBehavior.WORK  # Just keep working
            ),
        },
        base_interaction_radius=150.0,
        crowd_sensitivity=0.9,
        has_station=True,
        station_radius=200.0,
    ),
    
    NPCType.NOBLE: NPCBehaviorProfile(
        npc_type=NPCType.NOBLE,
        idle_behaviors={
            ComfortLevel.RELAXED: (
                IdleBehavior.STAND | IdleBehavior.SIT | IdleBehavior.CHAT |
                IdleBehavior.WAVE | IdleBehavior.LAUGH | IdleBehavior.READ |
                IdleBehavior.BROWSE
            ),
            ComfortLevel.COMFORTABLE: (
                IdleBehavior.STAND | IdleBehavior.CHAT | IdleBehavior.LOOK_AROUND |
                IdleBehavior.BROWSE
            ),
            ComfortLevel.UNEASY: (
                IdleBehavior.STAND | IdleBehavior.LOOK_AROUND | IdleBehavior.CHECK_ITEMS
            ),
            ComfortLevel.STRESSED: (
                IdleBehavior.STAND | IdleBehavior.FIDGET  # Nobles hate crowds
            ),
            ComfortLevel.OVERWHELMED: (
                IdleBehavior.NONE  # Leave entirely
            ),
        },
        base_interaction_radius=300.0,  # Nobles expect space
        crowd_sensitivity=1.5,  # Very sensitive to crowds
        can_leave=True,
    ),
    
    NPCType.CHILD: NPCBehaviorProfile(
        npc_type=NPCType.CHILD,
        idle_behaviors={
            ComfortLevel.RELAXED: (
                IdleBehavior.STAND | IdleBehavior.SIT | IdleBehavior.PLAY |
                IdleBehavior.CHAT | IdleBehavior.LAUGH | IdleBehavior.WAVE
            ),
            ComfortLevel.COMFORTABLE: (
                IdleBehavior.STAND | IdleBehavior.PLAY | IdleBehavior.CHAT |
                IdleBehavior.LOOK_AROUND
            ),
            ComfortLevel.UNEASY: (
                IdleBehavior.STAND | IdleBehavior.LOOK_AROUND | IdleBehavior.FIDGET
            ),
            ComfortLevel.STRESSED: (
                IdleBehavior.STAND | IdleBehavior.FIDGET
            ),
            ComfortLevel.OVERWHELMED: (
                IdleBehavior.NONE  # Children leave with parents
            ),
        },
        base_interaction_radius=150.0,
        crowd_sensitivity=1.3,  # Children are sensitive
        can_leave=True,
    ),
    
    NPCType.ELDER: NPCBehaviorProfile(
        npc_type=NPCType.ELDER,
        idle_behaviors={
            ComfortLevel.RELAXED: (
                IdleBehavior.STAND | IdleBehavior.SIT | IdleBehavior.CHAT |
                IdleBehavior.READ | IdleBehavior.SLEEP | IdleBehavior.SMOKE
            ),
            ComfortLevel.COMFORTABLE: (
                IdleBehavior.STAND | IdleBehavior.SIT | IdleBehavior.CHAT |
                IdleBehavior.LOOK_AROUND
            ),
            ComfortLevel.UNEASY: (
                IdleBehavior.STAND | IdleBehavior.SIT | IdleBehavior.LOOK_AROUND
            ),
            ComfortLevel.STRESSED: (
                IdleBehavior.SIT | IdleBehavior.STAND  # Find somewhere to sit
            ),
            ComfortLevel.OVERWHELMED: (
                IdleBehavior.NONE
            ),
        },
        base_interaction_radius=250.0,
        crowd_sensitivity=1.2,
        can_leave=True,
    ),
    
    NPCType.ENTERTAINER: NPCBehaviorProfile(
        npc_type=NPCType.ENTERTAINER,
        idle_behaviors={
            ComfortLevel.RELAXED: (
                IdleBehavior.STAND | IdleBehavior.WORK | IdleBehavior.CHAT |
                IdleBehavior.LAUGH | IdleBehavior.WAVE | IdleBehavior.STRETCH
            ),
            ComfortLevel.COMFORTABLE: (
                IdleBehavior.STAND | IdleBehavior.WORK | IdleBehavior.WAVE |
                IdleBehavior.LOOK_AROUND
            ),
            ComfortLevel.UNEASY: (
                IdleBehavior.STAND | IdleBehavior.WORK | IdleBehavior.LOOK_AROUND
            ),
            ComfortLevel.STRESSED: (
                IdleBehavior.STAND | IdleBehavior.WORK  # The show must go on
            ),
            ComfortLevel.OVERWHELMED: (
                IdleBehavior.STAND  # Too crowded to perform
            ),
        },
        base_interaction_radius=400.0,  # Need audience space
        crowd_sensitivity=0.7,  # Used to crowds
        has_station=True,
        station_radius=300.0,
    ),
}


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class NPCConfig:
    """Configuration for NPC modulation system."""
    
    # Population thresholds for comfort levels
    relaxed_max_pop: float = 0.20
    comfortable_max_pop: float = 0.40
    uneasy_max_pop: float = 0.60
    stressed_max_pop: float = 0.80
    # Above stressed_max_pop = OVERWHELMED
    
    # Repositioning settings
    base_reposition_interval: float = 30.0  # Seconds between repositions (relaxed)
    min_reposition_interval: float = 5.0    # Minimum interval (overwhelmed)
    
    # Edge preference scaling
    edge_preference_max: float = 0.8  # Maximum edge preference
    
    # Interaction radius scaling
    interaction_radius_min: float = 0.5  # Minimum radius multiplier
    
    # Social clustering
    social_cluster_radius: float = 300.0  # cm
    social_cluster_chance: float = 0.3    # Chance to cluster when relaxed
    
    # Smoothing
    comfort_smoothing: float = 0.1  # How fast comfort changes


# =============================================================================
# NPC State
# =============================================================================

@dataclass
class NPCState:
    """State tracking for a single NPC."""
    npc_id: str
    npc_type: NPCType
    profile: NPCBehaviorProfile
    
    # Comfort
    comfort_level: ComfortLevel = ComfortLevel.RELAXED
    comfort_value: float = 1.0  # 0-1, smoothed
    target_comfort: float = 1.0
    
    # Current behavior
    current_idle: IdleBehavior = IdleBehavior.STAND
    idle_duration: float = 0.0
    idle_target_duration: float = 5.0
    
    # Position
    edge_preference: float = 0.0
    interaction_radius: float = 200.0
    
    # Repositioning
    time_since_reposition: float = 0.0
    reposition_interval: float = 30.0
    wants_to_reposition: bool = False
    reposition_reason: RepositionReason = RepositionReason.NONE
    
    # Social
    nearby_npc_count: int = 0
    is_clustered: bool = False
    
    # Activity
    is_active: bool = True  # False if NPC has "left"
    activity_level: float = 1.0  # Animation speed/intensity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'npc_id': self.npc_id,
            'npc_type': self.npc_type.value,
            'comfort_level': self.comfort_level.value,
            'comfort_value': self.comfort_value,
            'current_idle': self.current_idle.name if self.current_idle else 'NONE',
            'edge_preference': self.edge_preference,
            'interaction_radius': self.interaction_radius,
            'wants_to_reposition': self.wants_to_reposition,
            'reposition_reason': self.reposition_reason.value,
            'is_active': self.is_active,
            'activity_level': self.activity_level,
        }


# =============================================================================
# NPC Manager
# =============================================================================

class NPCManager:
    """
    Manages NPC behavior modulation for a region.
    
    Tracks comfort levels, selects appropriate behaviors, and generates
    behavior commands for UE5.
    
    Example:
        >>> manager = NPCManager()
        >>> manager.register_npc("vendor_01", NPCType.VENDOR)
        >>> manager.register_npc("guard_01", NPCType.GUARD)
        >>> manager.set_population(0.65)
        >>> 
        >>> snapshot = manager.update(delta_time=0.5)
        >>> commands = manager.get_behavior_commands()
    """
    
    COMFORT_ORDER = [
        ComfortLevel.RELAXED,
        ComfortLevel.COMFORTABLE,
        ComfortLevel.UNEASY,
        ComfortLevel.STRESSED,
        ComfortLevel.OVERWHELMED,
    ]
    
    def __init__(self, config: Optional[NPCConfig] = None,
                 profiles: Optional[Dict[NPCType, NPCBehaviorProfile]] = None):
        """
        Initialize NPC manager.
        
        Args:
            config: NPC configuration
            profiles: Custom behavior profiles per type
        """
        self.config = config or NPCConfig()
        self.profiles = profiles or DEFAULT_PROFILES
        
        # NPCs
        self.npcs: Dict[str, NPCState] = {}
        
        # Global state
        self._population = 0.0
        self._global_comfort = ComfortLevel.RELAXED
        self._time = 0.0
        
        # Random seed for deterministic behavior selection
        self._rng = random.Random(42)
    
    def register_npc(self, npc_id: str, npc_type: NPCType,
                     custom_profile: Optional[NPCBehaviorProfile] = None) -> None:
        """Register an NPC to be managed."""
        profile = custom_profile or self.profiles.get(npc_type, DEFAULT_PROFILES[NPCType.AMBIENT])
        
        self.npcs[npc_id] = NPCState(
            npc_id=npc_id,
            npc_type=npc_type,
            profile=profile,
            interaction_radius=profile.base_interaction_radius,
        )
    
    def unregister_npc(self, npc_id: str) -> None:
        """Remove an NPC from management."""
        if npc_id in self.npcs:
            del self.npcs[npc_id]
    
    def set_population(self, population: float) -> None:
        """Set current population ratio (0.0 to 1.0)."""
        self._population = max(0.0, min(1.0, population))
    
    def update(self, delta_time: float) -> 'NPCSnapshot':
        """
        Update all NPC states for one tick.
        
        Args:
            delta_time: Time since last update in seconds
            
        Returns:
            Current NPC snapshot
        """
        self._time += delta_time
        
        # Determine global comfort from population
        self._global_comfort = self._get_comfort_level(self._population)
        
        # Update each NPC
        for npc in self.npcs.values():
            self._update_npc(npc, delta_time)
        
        return self._create_snapshot()
    
    def _get_comfort_level(self, population: float) -> ComfortLevel:
        """Determine comfort level from population."""
        cfg = self.config
        
        if population < cfg.relaxed_max_pop:
            return ComfortLevel.RELAXED
        elif population < cfg.comfortable_max_pop:
            return ComfortLevel.COMFORTABLE
        elif population < cfg.uneasy_max_pop:
            return ComfortLevel.UNEASY
        elif population < cfg.stressed_max_pop:
            return ComfortLevel.STRESSED
        else:
            return ComfortLevel.OVERWHELMED
    
    def _update_npc(self, npc: NPCState, delta_time: float) -> None:
        """Update a single NPC's state."""
        cfg = self.config
        profile = npc.profile
        
        # Calculate NPC-specific comfort (affected by sensitivity)
        adjusted_pop = self._population * profile.crowd_sensitivity
        npc_comfort_level = self._get_comfort_level(adjusted_pop)
        
        # Smooth comfort value
        comfort_idx = self.COMFORT_ORDER.index(npc_comfort_level)
        npc.target_comfort = 1.0 - (comfort_idx / (len(self.COMFORT_ORDER) - 1))
        
        diff = npc.target_comfort - npc.comfort_value
        npc.comfort_value += diff * min(1.0, delta_time * cfg.comfort_smoothing * 10)
        npc.comfort_level = npc_comfort_level
        
        # Handle NPCs that can leave
        if profile.can_leave and npc_comfort_level == ComfortLevel.OVERWHELMED:
            behaviors = profile.idle_behaviors.get(ComfortLevel.OVERWHELMED, IdleBehavior.NONE)
            if behaviors == IdleBehavior.NONE:
                npc.is_active = False
                return
        
        npc.is_active = True
        
        # Update edge preference
        base_edge = profile.edge_preference_base
        comfort_edge = (1.0 - npc.comfort_value) * cfg.edge_preference_max
        npc.edge_preference = min(1.0, base_edge + comfort_edge)
        
        # Update interaction radius
        radius_mult = cfg.interaction_radius_min + npc.comfort_value * (1.0 - cfg.interaction_radius_min)
        npc.interaction_radius = profile.base_interaction_radius * radius_mult
        
        # Update repositioning
        self._update_repositioning(npc, delta_time)
        
        # Update idle behavior
        self._update_idle_behavior(npc, delta_time)
        
        # Update activity level
        npc.activity_level = 0.5 + npc.comfort_value * 0.5
    
    def _update_repositioning(self, npc: NPCState, delta_time: float) -> None:
        """Update NPC repositioning state."""
        cfg = self.config
        
        npc.time_since_reposition += delta_time
        
        # Calculate reposition interval based on comfort
        comfort_factor = npc.comfort_value
        npc.reposition_interval = (
            cfg.min_reposition_interval + 
            comfort_factor * (cfg.base_reposition_interval - cfg.min_reposition_interval)
        )
        
        # Check if NPC wants to reposition
        if npc.time_since_reposition >= npc.reposition_interval:
            npc.wants_to_reposition = True
            
            # Determine reason
            if npc.comfort_level in [ComfortLevel.STRESSED, ComfortLevel.OVERWHELMED]:
                npc.reposition_reason = RepositionReason.CROWDING
            elif npc.edge_preference > 0.5:
                npc.reposition_reason = RepositionReason.EDGE_SEEKING
            elif npc.comfort_level == ComfortLevel.RELAXED and self._rng.random() < cfg.social_cluster_chance:
                npc.reposition_reason = RepositionReason.SOCIAL
            else:
                npc.reposition_reason = RepositionReason.COMFORT
    
    def _update_idle_behavior(self, npc: NPCState, delta_time: float) -> None:
        """Update NPC idle behavior."""
        profile = npc.profile
        
        npc.idle_duration += delta_time
        
        # Check if we need a new behavior
        if npc.idle_duration >= npc.idle_target_duration:
            # Get available behaviors for current comfort
            available = profile.idle_behaviors.get(npc.comfort_level, IdleBehavior.STAND)
            
            # Select a random behavior from available
            npc.current_idle = self._select_random_behavior(available)
            npc.idle_duration = 0.0
            
            # Random duration based on comfort
            base_duration = 5.0 + npc.comfort_value * 10.0
            npc.idle_target_duration = base_duration * (0.5 + self._rng.random())
    
    def _select_random_behavior(self, available: IdleBehavior) -> IdleBehavior:
        """Select a random behavior from available flags."""
        if available == IdleBehavior.NONE:
            return IdleBehavior.STAND
        
        # Get individual behaviors
        behaviors = []
        for behavior in IdleBehavior:
            if behavior != IdleBehavior.NONE and behavior != IdleBehavior.ALL:
                if behavior in available:
                    behaviors.append(behavior)
        
        if not behaviors:
            return IdleBehavior.STAND
        
        return self._rng.choice(behaviors)
    
    def _create_snapshot(self) -> 'NPCSnapshot':
        """Create a snapshot of current NPC state."""
        snapshot = NPCSnapshot()
        snapshot.population = self._population
        snapshot.global_comfort = self._global_comfort
        snapshot.npc_states = dict(self.npcs)
        
        # Calculate aggregates
        active_npcs = [n for n in self.npcs.values() if n.is_active]
        
        if active_npcs:
            snapshot.active_count = len(active_npcs)
            snapshot.inactive_count = len(self.npcs) - len(active_npcs)
            snapshot.average_comfort = sum(n.comfort_value for n in active_npcs) / len(active_npcs)
            snapshot.average_edge_preference = sum(n.edge_preference for n in active_npcs) / len(active_npcs)
            snapshot.repositioning_count = sum(1 for n in active_npcs if n.wants_to_reposition)
        
        # Comfort distribution
        for level in ComfortLevel:
            count = sum(1 for n in active_npcs if n.comfort_level == level)
            snapshot.comfort_distribution[level] = count
        
        return snapshot
    
    def acknowledge_reposition(self, npc_id: str) -> None:
        """Acknowledge that an NPC has repositioned (called by UE5)."""
        if npc_id in self.npcs:
            npc = self.npcs[npc_id]
            npc.time_since_reposition = 0.0
            npc.wants_to_reposition = False
            npc.reposition_reason = RepositionReason.NONE
    
    def get_behavior_commands(self) -> List[Dict[str, Any]]:
        """Generate behavior commands for UE5."""
        commands = []
        
        for npc_id, npc in self.npcs.items():
            cmd = {
                'npc_id': npc_id,
                'npc_type': npc.npc_type.value,
                'is_active': npc.is_active,
            }
            
            if npc.is_active:
                cmd.update({
                    'comfort_level': npc.comfort_level.value,
                    'comfort_value': npc.comfort_value,
                    'current_idle': npc.current_idle.name if npc.current_idle else 'STAND',
                    'idle_behaviors_mask': npc.profile.idle_behaviors.get(
                        npc.comfort_level, IdleBehavior.STAND
                    ).value,
                    'edge_preference': npc.edge_preference,
                    'interaction_radius': npc.interaction_radius,
                    'activity_level': npc.activity_level,
                    'wants_reposition': npc.wants_to_reposition,
                    'reposition_reason': npc.reposition_reason.value,
                })
            
            commands.append(cmd)
        
        return commands
    
    def reset(self) -> None:
        """Reset all NPC states."""
        for npc in self.npcs.values():
            npc.comfort_level = ComfortLevel.RELAXED
            npc.comfort_value = 1.0
            npc.target_comfort = 1.0
            npc.current_idle = IdleBehavior.STAND
            npc.idle_duration = 0.0
            npc.edge_preference = npc.profile.edge_preference_base
            npc.interaction_radius = npc.profile.base_interaction_radius
            npc.time_since_reposition = 0.0
            npc.wants_to_reposition = False
            npc.is_active = True
            npc.activity_level = 1.0
        
        self._population = 0.0
        self._global_comfort = ComfortLevel.RELAXED
        self._time = 0.0
    
    @property
    def global_comfort(self) -> ComfortLevel:
        """Current global comfort level."""
        return self._global_comfort
    
    @property
    def population(self) -> float:
        """Current population."""
        return self._population


# =============================================================================
# Snapshot
# =============================================================================

@dataclass
class NPCSnapshot:
    """Snapshot of NPC system state."""
    population: float = 0.0
    global_comfort: ComfortLevel = ComfortLevel.RELAXED
    
    # Per-NPC states
    npc_states: Dict[str, NPCState] = field(default_factory=dict)
    
    # Aggregates
    active_count: int = 0
    inactive_count: int = 0
    average_comfort: float = 1.0
    average_edge_preference: float = 0.0
    repositioning_count: int = 0
    
    # Distribution
    comfort_distribution: Dict[ComfortLevel, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'population': self.population,
            'global_comfort': self.global_comfort.value,
            'active_count': self.active_count,
            'inactive_count': self.inactive_count,
            'average_comfort': self.average_comfort,
            'average_edge_preference': self.average_edge_preference,
            'repositioning_count': self.repositioning_count,
            'comfort_distribution': {
                k.value: v for k, v in self.comfort_distribution.items()
            },
            'npcs': {k: v.to_dict() for k, v in self.npc_states.items()},
        }


# =============================================================================
# UE5 Command Generator
# =============================================================================

@dataclass
class FNPCBehaviorCommand:
    """UE5-ready behavior command for an NPC."""
    npc_id: str
    npc_type: str
    is_active: bool
    
    # Behavior
    comfort_level: str = "relaxed"
    comfort_value: float = 1.0
    current_idle: str = "STAND"
    idle_behaviors_mask: int = 1  # Bitmask
    
    # Position
    edge_preference: float = 0.0
    interaction_radius: float = 200.0
    
    # Movement
    wants_reposition: bool = False
    reposition_reason: str = "none"
    reposition_target_edge: bool = False
    
    # Animation
    activity_level: float = 1.0
    animation_speed: float = 1.0
    
    def to_ue5_json(self) -> Dict[str, Any]:
        """Export as JSON for UE5."""
        return {
            'NPCID': self.npc_id,
            'NPCType': self.npc_type,
            'IsActive': self.is_active,
            'ComfortLevel': self.comfort_level,
            'ComfortValue': self.comfort_value,
            'CurrentIdle': self.current_idle,
            'IdleBehaviorsMask': self.idle_behaviors_mask,
            'EdgePreference': self.edge_preference,
            'InteractionRadius': self.interaction_radius,
            'WantsReposition': self.wants_reposition,
            'RepositionReason': self.reposition_reason,
            'RepositionTargetEdge': self.reposition_target_edge,
            'ActivityLevel': self.activity_level,
            'AnimationSpeed': self.animation_speed,
        }


class NPCCommandGenerator:
    """
    Generates UE5 behavior commands from NPC manager state.
    """
    
    def generate_commands(self, manager: NPCManager) -> List[FNPCBehaviorCommand]:
        """Generate behavior commands from NPC manager."""
        commands = []
        
        for npc_id, npc in manager.npcs.items():
            cmd = FNPCBehaviorCommand(
                npc_id=npc_id,
                npc_type=npc.npc_type.value,
                is_active=npc.is_active,
            )
            
            if npc.is_active:
                cmd.comfort_level = npc.comfort_level.value
                cmd.comfort_value = npc.comfort_value
                cmd.current_idle = npc.current_idle.name if npc.current_idle else "STAND"
                cmd.idle_behaviors_mask = npc.profile.idle_behaviors.get(
                    npc.comfort_level, IdleBehavior.STAND
                ).value
                cmd.edge_preference = npc.edge_preference
                cmd.interaction_radius = npc.interaction_radius
                cmd.wants_reposition = npc.wants_to_reposition
                cmd.reposition_reason = npc.reposition_reason.value
                cmd.reposition_target_edge = npc.edge_preference > 0.5
                cmd.activity_level = npc.activity_level
                cmd.animation_speed = 0.7 + npc.activity_level * 0.3
            
            commands.append(cmd)
        
        return commands
    
    def to_ue5_json(self, manager: NPCManager) -> Dict[str, Any]:
        """Generate complete UE5 JSON payload."""
        commands = self.generate_commands(manager)
        
        return {
            'Population': manager.population,
            'GlobalComfort': manager.global_comfort.value,
            'NPCCommands': [cmd.to_ue5_json() for cmd in commands],
            'Summary': {
                'TotalNPCs': len(manager.npcs),
                'ActiveNPCs': sum(1 for n in manager.npcs.values() if n.is_active),
                'RepositioningNPCs': sum(1 for n in manager.npcs.values() if n.wants_to_reposition),
            },
        }
