# AURA — Ambient Universal Response Architecture

A complete environmental pressure system for game development that uses subtle audio and visual cues to influence player behavior without obvious game mechanics.

**299 tests passing** | Python 3.8+ | UE5 Ready

## Overview

AURA creates natural crowd dispersal through environmental feedback. Instead of UI warnings or artificial barriers, it makes crowded areas feel subtly uncomfortable while quiet areas feel naturally appealing.

**Core Principle:** Players leave because they *want* to, not because they're told to.

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESSURE COORDINATOR                         │
│         (Coordinates SDI + VDI with anti-sync logic)            │
├─────────────────────────────┬───────────────────────────────────┤
│      Audio Engine           │           Visual Engine           │
│                             │                                   │
│  ┌─────────────────────┐    │    ┌─────────────────────────┐    │
│  │ SDI Calculator      │    │    │ VDI Calculator          │    │
│  │ (fast response)     │    │    │ (lagged response)       │    │
│  └─────────────────────┘    │    └─────────────────────────┘    │
│           │                 │              │                    │
│  ┌─────────────────────┐    │    ┌─────────────────────────┐    │
│  │ Soundscape Manager  │    │    │ Wildlife System         │    │
│  │ - Layer mixing      │    │    │ - 3 sensitivity tiers   │    │
│  │ - Sound selection   │    │    │ - Behavior state machine│    │
│  │ - Population pressure│   │    │ - Recovery memory       │    │
│  └─────────────────────┘    │    └─────────────────────────┘    │
│           │                 │              │                    │
│  ┌─────────────────────┐    │    ┌─────────────────────────┐    │
│  │ Memory Systems      │    │    │ NPC Modulation          │    │
│  │ - Sound memory      │    │    │ - 8 type profiles       │    │
│  │ - Silence tracking  │    │    │ - 20+ idle behaviors    │    │
│  │ - Pattern memory    │    │    │ - Edge-seeking logic    │    │
│  └─────────────────────┘    │    └─────────────────────────┘    │
│                             │              │                    │
│                             │    ┌─────────────────────────┐    │
│                             │    │ Environmental Wear      │    │
│                             │    │ - 3 wear layers         │    │
│                             │    │ - 9 surface types       │    │
│                             │    └─────────────────────────┘    │
│                             │              │                    │
│                             │    ┌─────────────────────────┐    │
│                             │    │ Motion Coherence        │    │
│                             │    │ - Wind synchronization  │    │
│                             │    │ - 6 motion categories   │    │
│                             │    └─────────────────────────┘    │
│                             │              │                    │
│                             │    ┌─────────────────────────┐    │
│                             │    │ Attraction System       │    │
│                             │    │ - Cross-region signals  │    │
│                             │    │ - 6 distant cue types   │    │
│                             │    └─────────────────────────┘    │
└─────────────────────────────┴───────────────────────────────────┘
```

## Installation

```bash
git clone <repository>
cd lse
pip install -r requirements.txt
```

## Quick Start

```python
from vde import PressureCoordinator

# Create coordinator
coordinator = PressureCoordinator()

# Add regions
coordinator.add_region("marketplace", position=(0, 0))
coordinator.add_region("forest_path", position=(500, 0))
coordinator.add_region("quiet_grove", position=(1000, 0))

# Set populations
coordinator.set_population("marketplace", 0.85)  # Crowded
coordinator.set_population("forest_path", 0.40)  # Moderate
coordinator.set_population("quiet_grove", 0.10)  # Quiet

# Update each tick
snapshots = coordinator.update(delta_time=0.016)

# Get UE5-ready data
ue5_data = coordinator.to_ue5_json()
```

## Soundscape Discomfort Index (SDI)

The SDI measures audio-based environmental comfort. It responds **immediately** to population changes.

### SDI Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Base Layer Mismatch | 0.25 | Wrong ambient for biome |
| Dense Sound Overlap | 0.20 | Too many simultaneous sounds |
| Rhythm Disruption | 0.15 | Broken natural patterns |
| Frequency Harshness | 0.15 | Uncomfortable frequencies |
| Volume Imbalance | 0.15 | Unnatural volume relationships |
| Silence Deficit | 0.10 | Lack of breathing room |

### SDI Levels

| SDI Range | State | Audio Characteristics |
|-----------|-------|----------------------|
| < -0.15 | Pristine | Birds, wind, natural peace |
| -0.15 to +0.15 | Comfortable | Balanced soundscape |
| +0.15 to +0.40 | Uneasy | Rhythm breaking, insects louder |
| +0.40 to +0.65 | Stressed | Drones, static appearing |
| > +0.65 | Overwhelmed | Harsh frequencies dominate |

## Visual Discomfort Index (VDE)

The VDE measures visual environmental pressure. It **lags behind** SDI to create cross-modal offset.

### VDE Phases (8 Complete)

| Phase | Description | Key Features |
|-------|-------------|--------------|
| **Phase 1** | Core VDI | Population phases, output parameters |
| **Phase 2** | UE5 Integration | Post-process, MPC, Niagara bindings |
| **Phase 3** | Wildlife System | 3-tier sensitivity, state machine |
| **Phase 4** | NPC Modulation | 8 type profiles, comfort levels |
| **Phase 5** | Environmental Wear | 3 layers, 9 surface types |
| **Phase 6** | Motion Coherence | Wind sync, 6 motion categories |
| **Phase 7** | Attraction System | Cross-region signals, 6 cue types |
| **Phase 8** | Pressure Coordinator | SDI/VDI coupling, anti-sync |

### Wildlife System

Wildlife provides emotional confirmation of crowding.

**Sensitivity Tiers:**

| Tier | Creatures | Flee Threshold | Return Delay |
|------|-----------|----------------|--------------|
| Skittish | Deer, rabbits, songbirds | 25% population | 200+ seconds |
| Wary | Squirrels, hawks, foxes | 45% population | 120 seconds |
| Bold | Crows, pigeons, rats | 70% population | 60 seconds |

**State Machine:**
```
PRESENT → ALERT → FLEEING → ABSENT → CAUTIOUS → PRESENT
         (fast)           (slow, with memory effect)
```

### NPC Behavior Profiles

| Type | Crowd Sensitivity | Can Leave | Characteristics |
|------|-------------------|-----------|-----------------|
| Guard | 0.6x (tolerant) | No | Stationed, large interaction radius |
| Vendor | 0.8x (tolerant) | No | At shop, expects some crowds |
| Worker | 0.9x | No | At workstation |
| Ambient | 1.0x (normal) | Yes | General population |
| Elder | 1.2x (sensitive) | Yes | Needs more space |
| Child | 1.3x (sensitive) | Yes | First to leave |
| Noble | 1.5x (very sensitive) | Yes | Expects personal space |

**Comfort Levels:**
- RELAXED: Full idle repertoire (sitting, chatting, eating)
- COMFORTABLE: Most behaviors available
- UNEASY: Standing idles only
- STRESSED: Minimal behaviors, edge-seeking
- OVERWHELMED: Leave if able

### Environmental Wear

The ground tells a story. Crowded areas look used.

**Wear Layers:**

| Layer | Accumulation | Recovery | Examples |
|-------|--------------|----------|----------|
| Displacement | ~10 seconds | ~2 minutes | Footprints, trampled grass |
| Discoloration | ~30 seconds | ~15 minutes | Browning, mud, worn paths |
| Damage | ~60 seconds | ~30+ minutes | Dead patches, erosion |

**Surface Types:** Grass, Dirt, Stone, Wood, Sand, Snow, Mud, Gravel, Water Edge

### Motion Coherence

The most powerful and least obvious lever.

**Coherence Levels:**

| Population | Level | Effect |
|------------|-------|--------|
| 0-15% | UNIFIED | Perfect sync, calm wind |
| 15-35% | NATURAL | Natural variation, steady wind |
| 35-60% | VARIED | Noticeable desync, gusting |
| 60%+ | CHAOTIC | Full desync, swirling wind |

**Affected Categories:**
- Foliage (trees, bushes, grass)
- Cloth (banners, flags, awnings)
- Props (small objects, hanging items)
- Water (surfaces, ripples)
- Particles (dust, leaves, debris)
- NPCs (idle animations)

### Attraction System

Pulling is harder than pushing. This system makes quiet areas appealing.

**Signal Boosts at BEACON (lowest population):**
- Light Quality: +20%
- Wildlife Surge: +35%
- Visual Clarity: +15%
- Motion Coherence: +20%
- NPC Vitality: +20%

**Distant Visual Cues:**
- Light shafts through trees
- Birds circling/landing
- Peaceful smoke rising
- Movement at edge of vision
- Clear sky patches
- Water glints

## Pressure Coordinator

The final integration layer that coordinates audio and visual systems.

### Key Principles

1. **Audio leads, visual follows** - VDI lags 10-15 seconds behind SDI
2. **Never synchronize peaks** - Anti-sync logic holds VDI during SDI spikes
3. **Asymmetric timing** - Rise fast, recover slow
4. **Cross-region attraction** - Crowded regions boost nearby quiet regions

### Pressure Phases

| Phase | SDI | VDI | Description |
|-------|-----|-----|-------------|
| PRISTINE | Low | Low | Peaceful environment |
| AUDIO_LEADING | High | Low | Audio discomfort first |
| FULLY_PRESSURED | High | High | Maximum pressure |
| VISUAL_TRAILING | Low | High | Visual recovery lagging |
| RECOVERING | Falling | Falling | Both indices dropping |

### Example Scenario: Crowding

```
Time │ Pop% │ SDI    │ VDI    │ Audio              │ Visual
─────┼──────┼────────┼────────┼────────────────────┼────────────────────
0:00 │ 10%  │ -0.15  │ -0.20  │ Birds, wind, peace │ Clear, wildlife
1:00 │ 35%  │ +0.05  │ -0.10  │ Insects louder     │ Wildlife thinning
2:00 │ 50%  │ +0.25  │ +0.08  │ Rhythm breaking    │ Motion incoherence
3:00 │ 70%  │ +0.45  │ +0.30  │ Drones, static     │ Light diffusing
4:00 │ 85%  │ +0.65  │ +0.50  │ Harsh frequencies  │ No wildlife, NPCs uneasy
```

## UE5 Integration

All systems generate UE5-ready parameters.

### Post-Process Parameters

```cpp
UPROPERTY() float VDE_Saturation;           // 0.85-1.0
UPROPERTY() float VDE_Contrast;             // 0.9-1.0
UPROPERTY() float VDE_Bloom;                // 0.0-0.3
UPROPERTY() float VDE_VignetteIntensity;    // 0.0-0.2
UPROPERTY() float VDE_ChromaticAberration;  // 0.0-0.15
```

### Material Parameter Collection

```cpp
UPROPERTY() float VDE_GrassColorShift;      // 0-1 (green to brown)
UPROPERTY() float VDE_GrassHeightMult;      // 0.3-1.0
UPROPERTY() float VDE_GroundWetness;        // 0-1
UPROPERTY() float VDE_PathBlendAmount;      // 0-1
```

### Niagara Parameters

```cpp
UPROPERTY() float VDE_WildlifeSpawnRate;    // 0-1
UPROPERTY() float VDE_ParticleCoherence;    // 0-1
UPROPERTY() float VDE_WindDirection;        // 0-360
UPROPERTY() float VDE_WindStrength;         // 0-1
```

## Project Structure

```
aura/
├── src/
│   ├── vde/                      # Visual Discomfort Engine
│   │   ├── vdi_calculator.py     # Phase 1: Core VDI
│   │   ├── output_params.py      # Phase 1: Output parameters
│   │   ├── ue5_binding.py        # Phase 2: UE5 integration
│   │   ├── ue5_codegen.py        # Phase 2: C++ generation
│   │   ├── wildlife.py           # Phase 3: Wildlife system
│   │   ├── npc_behavior.py       # Phase 4: NPC modulation
│   │   ├── environmental_wear.py # Phase 5: Wear system
│   │   ├── motion_coherence.py   # Phase 6: Motion sync
│   │   ├── attraction_system.py  # Phase 7: Attraction
│   │   └── pressure_coordinator.py # Phase 8: Coordination
│   ├── sdi/                      # Soundscape Discomfort Index
│   │   ├── calculator.py         # SDI calculation
│   │   ├── factors.py            # Discomfort factors
│   │   └── comfort.py            # Comfort evaluation
│   ├── audio/                    # Audio Engine
│   │   ├── soundscape.py         # Main soundscape manager
│   │   ├── layer_manager.py      # Audio layer mixing
│   │   ├── sound_selector.py     # Sound selection logic
│   │   └── population_pressure.py # Population effects
│   ├── memory/                   # Memory systems
│   │   ├── sound_memory.py       # Sound history
│   │   ├── silence_tracker.py    # Silence tracking
│   │   └── pattern_memory.py     # Pattern recognition
│   └── core/                     # Core utilities
│       ├── clock.py              # Time management
│       └── state.py              # State management
├── tests/                        # 299 tests
│   ├── test_vde_phase1.py        # 38 tests
│   ├── test_vde_phase2.py        # 37 tests
│   ├── test_vde_phase3.py        # 33 tests
│   ├── test_vde_phase4.py        # 38 tests
│   ├── test_vde_phase5.py        # 40 tests
│   ├── test_vde_phase6.py        # 41 tests
│   ├── test_vde_phase7.py        # 39 tests
│   └── test_vde_phase8.py        # 33 tests
├── config/                       # Configuration files
├── docs/                         # Design documents
│   ├── VDE_DESIGN.md             # VDE specification
│   └── VDI_DESIGN.md             # VDI specification
└── ue5_generated/                # Generated UE5 headers
```

## Anti-Detection Principles

If players notice the system, it fails.

### Never Do

| Bad Practice | Why |
|--------------|-----|
| Desaturation as punishment | Obvious, feels unfair |
| Screen effects tied to population | Too direct |
| Fog walls | Screams "game mechanic" |
| Camera shake | Aggressive, breaks immersion |
| UI warnings | Absolutely not |
| Sudden transitions | Must be gradual |

### Always Do

| Good Practice | Why |
|---------------|-----|
| Gradual changes | Players adapt without noticing |
| Plausible causation | "It's crowded" explains wear |
| Asymmetric timing | Rise/fall at different rates |
| Cross-modal offset | Audio and visual don't sync |
| Environmental logic | Wildlife leaving makes sense |

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific phase
python tests/test_vde_phase8.py

# Run with coverage
python -m pytest tests/ --cov=src
```

## License

MIT License

## Conclusion

AURA creates complete environmental pressure through:

1. **Audio leads** with SDI (immediate response)
2. **Visual follows** with VDI (lagged response)
3. **Wildlife absence** provides emotional confirmation
4. **NPC behavior** provides social proof
5. **Environmental wear** provides logical explanation
6. **Motion incoherence** creates subconscious unease
7. **Attraction elsewhere** provides escape path

No UI. No warnings. No obvious mechanics.

Players leave because they **want** to.
