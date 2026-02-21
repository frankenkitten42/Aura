"""
Visual Discomfort Engine (VDE) for the Living Soundscape Engine.

Phase 1: Core VDE
- VDI calculation (vdi_calculator.py)
- Population pressure phases
- Basic output parameters (output_params.py)

Phase 2: UE5 Integration
- Post-process parameter binding (ue5_binding.py)
- Material Parameter Collection integration
- Niagara particle system parameters
- C++ header generation (ue5_codegen.py)

Phase 3: Wildlife System
- Multi-tier creature sensitivity (wildlife.py)
- State machine with asymmetric transitions
- Recovery timing with "memory" effect
- UE5-ready spawn commands

Phase 4: NPC Modulation
- Comfort levels based on population (npc_behavior.py)
- Per-type behavior profiles (Vendor, Guard, Ambient, etc.)
- Idle behavior repertoire management
- Repositioning and edge-seeking behavior

Phase 5: Environmental Wear
- Multi-layer wear system (environmental_wear.py)
- Displacement, discoloration, and damage layers
- Surface-type specific wear behavior
- Asymmetric accumulation/recovery timing

Phase 6: Motion Coherence
- Wind direction and variance control (motion_coherence.py)
- Foliage animation synchronization
- Cloth/banner behavior
- Prop micro-movement and jitter
- Phase relationship management

Phase 7: Attraction System
- Cross-region attraction signaling (attraction_system.py)
- Distant visual cues (light shafts, birds, smoke)
- Signal boosts (lighting, wildlife, clarity)
- Visual breadcrumb generation

Phase 8: Pressure Coordinator
- LSE/VDE coupling with configurable lag (pressure_coordinator.py)
- Timing offset management (audio leads, visual follows)
- Anti-synchronization logic
- Cross-modal pressure balancing
- Holistic state management
"""

# Phase 1: Core
from .vdi_calculator import (
    VDICalculator,
    VDIResult,
    VDIFactors,
    VDEConfig,
    VisualPhase,
    WildlifeState,
)

from .output_params import (
    OutputGenerator,
    VDEOutputState,
    PostProcessParams,
    MaterialParams,
    SpawnParams,
    ParticleParams,
    MotionParams,
    AttractionParams,
)

# Phase 2: UE5 Integration
from .ue5_binding import (
    UE5BindingGenerator,
    FVDERegionState,
    FVDEPostProcessSettings,
    FVDEMaterialParameters,
    FVDENiagaraParameters,
    FVDESpawnSettings,
    FVDEAttractionSettings,
    FVDEWorldState,
    MultiRegionProcessor,
)

# Phase 3: Wildlife System
from .wildlife import (
    WildlifeManager,
    WildlifeConfig,
    WildlifeSnapshot,
    WildlifeState as WildlifeStateEnum,  # Alias to avoid conflict
    CreatureTier,
    CreatureCategory,
    CreatureState,
    WildlifeSpawnGenerator,
    FWildlifeSpawnCommand,
    CREATURE_TIERS,
)

# Phase 4: NPC Modulation
from .npc_behavior import (
    NPCManager,
    NPCConfig,
    NPCSnapshot,
    NPCState,
    NPCType,
    ComfortLevel,
    IdleBehavior,
    RepositionReason,
    NPCBehaviorProfile,
    NPCCommandGenerator,
    FNPCBehaviorCommand,
    DEFAULT_PROFILES,
)

# Phase 5: Environmental Wear
from .environmental_wear import (
    WearManager,
    WearConfig,
    WearSnapshot,
    WearLayer,
    SurfaceType,
    WearType,
    FWearParameters,
    RegionWearManager,
    WearZone,
    WEAR_LAYER_MAP,
    SURFACE_WEAR_MAP,
)

# Phase 6: Motion Coherence
from .motion_coherence import (
    MotionManager,
    MotionConfig,
    MotionSnapshot,
    MotionCategory,
    CoherenceLevel,
    WindPattern,
    ElementMotionState,
    CategoryState,
    FMotionParameters,
    WindPatternGenerator,
)

# Phase 7: Attraction System
from .attraction_system import (
    AttractionManager,
    AttractionConfig,
    AttractionSnapshot,
    AttractionSignal,
    AttractionStrength,
    DistantCue,
    RegionAttractionState,
    AttractionCoordinator,
    FAttractionParameters,
    DistantCueGenerator,
    DistantCueCommand,
)

# Phase 8: Pressure Coordinator
from .pressure_coordinator import (
    PressureCoordinator,
    PressureConfig,
    PressureSnapshot,
    PressurePhase,
    SyncState,
    RegionPressureManager,
    RegionPressureState,
    PressureHistory,
    PressureSample,
    FPressureParameters,
    ScenarioSimulator,
)

# Legacy compatibility
from .vde_engine import (
    VDEEngine,
    VDEState,
    VDECalculator,
    VisualThresholds,
)

__all__ = [
    # Phase 1: Core
    'VDICalculator',
    'VDIResult',
    'VDIFactors',
    'VDEConfig',
    'VisualPhase',
    'WildlifeState',
    'OutputGenerator',
    'VDEOutputState',
    'PostProcessParams',
    'MaterialParams',
    'SpawnParams',
    'ParticleParams',
    'MotionParams',
    'AttractionParams',
    
    # Phase 2: UE5 Integration
    'UE5BindingGenerator',
    'FVDERegionState',
    'FVDEPostProcessSettings',
    'FVDEMaterialParameters',
    'FVDENiagaraParameters',
    'FVDESpawnSettings',
    'FVDEAttractionSettings',
    'FVDEWorldState',
    'MultiRegionProcessor',
    
    # Phase 3: Wildlife System
    'WildlifeManager',
    'WildlifeConfig',
    'WildlifeSnapshot',
    'WildlifeStateEnum',
    'CreatureTier',
    'CreatureCategory',
    'CreatureState',
    'WildlifeSpawnGenerator',
    'FWildlifeSpawnCommand',
    'CREATURE_TIERS',
    
    # Phase 4: NPC Modulation
    'NPCManager',
    'NPCConfig',
    'NPCSnapshot',
    'NPCState',
    'NPCType',
    'ComfortLevel',
    'IdleBehavior',
    'RepositionReason',
    'NPCBehaviorProfile',
    'NPCCommandGenerator',
    'FNPCBehaviorCommand',
    'DEFAULT_PROFILES',
    
    # Phase 5: Environmental Wear
    'WearManager',
    'WearConfig',
    'WearSnapshot',
    'WearLayer',
    'SurfaceType',
    'WearType',
    'FWearParameters',
    'RegionWearManager',
    'WearZone',
    'WEAR_LAYER_MAP',
    'SURFACE_WEAR_MAP',
    
    # Phase 6: Motion Coherence
    'MotionManager',
    'MotionConfig',
    'MotionSnapshot',
    'MotionCategory',
    'CoherenceLevel',
    'WindPattern',
    'ElementMotionState',
    'CategoryState',
    'FMotionParameters',
    'WindPatternGenerator',
    
    # Phase 7: Attraction System
    'AttractionManager',
    'AttractionConfig',
    'AttractionSnapshot',
    'AttractionSignal',
    'AttractionStrength',
    'DistantCue',
    'RegionAttractionState',
    'AttractionCoordinator',
    'FAttractionParameters',
    'DistantCueGenerator',
    'DistantCueCommand',
    
    # Phase 8: Pressure Coordinator
    'PressureCoordinator',
    'PressureConfig',
    'PressureSnapshot',
    'PressurePhase',
    'SyncState',
    'RegionPressureManager',
    'RegionPressureState',
    'PressureHistory',
    'PressureSample',
    'FPressureParameters',
    'ScenarioSimulator',
    
    # Legacy
    'VDEEngine',
    'VDEState',
    'VDECalculator',
    'VisualThresholds',
]
