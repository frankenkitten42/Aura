# Visual Discomfort Engine (VDE) Design Document

## Overview

The Visual Discomfort Engine works alongside the Living Soundscape Engine (LSE) to create a holistic environmental pressure system. While SDI manipulates audio to create subconscious discomfort, VDI (Visual Discomfort Index) manipulates visual elements.

**Core Principle:** Audio and visual discomfort should **correlate, not mirror**. If both spike simultaneously, players detect manipulation. Instead, systems lag and lead each other organically.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Environmental Pressure System                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Population ──┬──► LSE (Audio) ──► SDI ──┐                         │
│   Ratio        │                          │                         │
│                │                          ├──► Pressure Coordinator │
│                │                          │                         │
│                └──► VDE (Visual) ──► VDI ─┘                         │
│                                                                      │
│   Pressure Coordinator:                                              │
│   - Manages timing offsets between systems                          │
│   - Prevents synchronized spikes                                     │
│   - Generates attraction signals for other regions                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Visual Discomfort Index (VDI)

### VDI Range
- **-1.0 to +1.0** (mirrors SDI)
- **Negative:** Visually comfortable, inviting
- **Zero:** Neutral
- **Positive:** Visually fatiguing, subtly repellent

### VDI Factors

#### Discomfort Factors (Increase VDI)

| Factor | Weight | Description |
|--------|--------|-------------|
| motion_incoherence | +0.15 | Foliage/cloth animation out of sync |
| visual_density | +0.12 | Overlapping decals, particles, detail |
| light_diffusion | +0.10 | Soft shadows, bloom bleed, reduced contrast |
| environmental_wear | +0.08 | Trampled grass, murky water, discoloration |
| wildlife_absence | +0.12 | No birds, no ambient creatures |
| npc_unease | +0.08 | NPCs repositioning, less idle behavior |
| spatial_noise | +0.10 | Harder to parse environment visually |

#### Comfort Factors (Decrease VDI)

| Factor | Weight | Description |
|--------|--------|-------------|
| motion_coherence | -0.12 | Wind/foliage aligned, rhythmic animation |
| visual_clarity | -0.10 | Clean sightlines, readable space |
| light_quality | -0.08 | Intentional lighting, warm gradients |
| environmental_health | -0.10 | Fresh grass, clear water, vibrant color |
| wildlife_presence | -0.15 | Birds, insects, ambient life |
| npc_comfort | -0.08 | NPCs relaxed, varied idles |
| spatial_invitation | -0.10 | Open paths, framing, distant landmarks |

---

## Pressure Phases (Visual)

| Phase | Population | Visual Effects |
|-------|------------|----------------|
| PRISTINE | 0-10% | Maximum visual comfort, abundant wildlife |
| HEALTHY | 10-20% | Natural state, balanced |
| OCCUPIED | 20-35% | Subtle wear begins, some wildlife retreat |
| BUSY | 35-50% | Visible wear, motion irregularity starts |
| CROWDED | 50-70% | Clear fatigue, light diffusion, NPC unease |
| SATURATED | 70%+ | Maximum visual pressure, stark absence |

---

## Output Parameters (UE5 Integration)

The VDE outputs normalized parameters (0.0-1.0) for UE5 consumption:

### Post-Processing Parameters
```cpp
struct FVDEPostProcessParams
{
    float BloomIntensityMod;      // 0.0 = crisp, 1.0 = diffused
    float ContrastReduction;       // 0.0 = full contrast, 1.0 = flat
    float ShadowSoftness;          // 0.0 = sharp shadows, 1.0 = diffuse
    float ColorSaturationMod;      // Subtle only: 0.95-1.0 range
    float DistanceHazeDensity;     // 0.0 = clear, 1.0 = hazy
    float VignetteSubtle;          // Very subtle darkening at edges
};
```

### Material Parameters
```cpp
struct FVDEMaterialParams
{
    float FoliageRestlessness;     // Animation irregularity
    float ClothSettleTime;         // How long cloth takes to rest
    float WaterClarity;            // 1.0 = clear, 0.0 = murky
    float GroundWear;              // Decal intensity for wear
    float PropMicroJitter;         // Imperceptible prop movement
};
```

### Spawning Parameters
```cpp
struct FVDESpawnParams
{
    float WildlifeSpawnRate;       // Multiplier for ambient creatures
    float BirdLandingChance;       // Probability birds land nearby
    float InsectDensity;           // Ambient insect activity
    float NPCIdleVariety;          // How many idle behaviors available
    float NPCComfortLevel;         // Affects idle selection
};
```

### Particle Parameters
```cpp
struct FVDEParticleParams
{
    float DustDensity;             // Airborne particle count
    float PollenIntensity;         // Organic particles
    float DebrisFrequency;         // Leaves, small debris
    float ParticleCoherence;       // How aligned particle motion is
};
```

---

## Timing and Coupling

### The Offset Rule

SDI and VDI should never spike together. The Pressure Coordinator manages this:

```
Time ────────────────────────────────────────────►

Population rises:
  SDI:  ▁▂▃▄▅▆▇█████████████
  VDI:  ▁▁▁▂▃▄▅▆▇███████████  (lags 5-15 seconds)

Population falls:
  SDI:  █████████▇▆▅▄▃▂▁▁▁▁▁
  VDI:  ███████████▇▆▅▄▃▂▁▁▁  (lags 10-20 seconds)

Attraction elsewhere:
  When local VDI rises, nearby low-pop regions
  get ATTRACTION boost (negative VDI modifier)
```

### Coupling Rules

1. **VDI lags SDI by 5-15 seconds on rise**
   - Audio discomfort noticed first
   - Visual follows as "confirmation"
   
2. **VDI lags SDI by 10-20 seconds on fall**
   - Audio relief comes first
   - Visual "recovery" takes longer
   
3. **Never synchronize peaks**
   - If SDI spikes suddenly, VDI holds steady briefly
   - Prevents "the game is punishing me" feeling
   
4. **Cross-region attraction**
   - High local pressure → broadcast attraction to neighbors
   - Neighbors with low population get visual comfort boost

---

## Wildlife Behavior System

Wildlife is the strongest visual signal. Absence speaks louder than presence.

### Wildlife States

| State | Trigger | Behavior |
|-------|---------|----------|
| THRIVING | Pop < 15% | Full activity, birds land, insects hover |
| WARY | Pop 15-30% | Reduced landing, quicker flight |
| RETREATING | Pop 30-50% | Animals at edges only, no landing |
| ABSENT | Pop > 50% | No wildlife spawns in region |

### Wildlife Types

```
Tier 1 (Most Sensitive):
  - Birds (first to leave, last to return)
  - Deer/large fauna
  
Tier 2 (Moderate):
  - Small mammals
  - Reptiles
  
Tier 3 (Least Sensitive):
  - Insects (reduce but don't eliminate)
  - Fish (if water present)
```

### Recovery Time

Wildlife doesn't return instantly when population drops:

| From State | To State | Recovery Time |
|------------|----------|---------------|
| ABSENT | RETREATING | 30 seconds |
| RETREATING | WARY | 45 seconds |
| WARY | THRIVING | 60 seconds |

This creates "memory" — recently crowded areas feel empty even after players leave.

---

## NPC Behavior Modulation

NPCs provide social proof. Their discomfort is contagious.

### NPC Comfort Levels

| Population | NPC Behavior |
|------------|--------------|
| Low | Full idle repertoire, sitting, stretching, chatting |
| Medium | Standing idles only, occasional repositioning |
| High | Minimal idles, frequent repositioning, "busy" poses |
| Critical | NPCs cluster at edges, reduced interaction radius |

### Specific Behaviors

**Vendors:**
- Low pop: Relaxed, call out to players, gesture
- High pop: Hunched, minimal animation, quick transactions

**Guards:**
- Low pop: Patrol normally, varied routes
- High pop: Stationary, alert pose, eyes tracking

**Ambient NPCs:**
- Low pop: Sit, lean, converse, varied activities
- High pop: Standing, walking through, no lingering

---

## Environmental Wear System

The ground tells a story. Crowded areas look used.

### Wear Layers

```
Layer 1: Ground Displacement (immediate)
  - Footprint decals
  - Trampled grass (shader-driven)
  - Disturbed dirt/dust
  
Layer 2: Discoloration (builds over time)
  - Slight browning of grass
  - Mud accumulation
  - Worn paths emerging
  
Layer 3: Persistent Damage (slow accumulation)
  - Dead patches
  - Compacted soil
  - Erosion near high-traffic points
```

### Recovery

Wear recovers when population drops, but slowly:

| Wear Type | Recovery Rate |
|-----------|---------------|
| Footprints | 2 minutes |
| Trampled grass | 5 minutes |
| Discoloration | 15 minutes |
| Persistent damage | 30+ minutes |

---

## Light and Atmosphere

Light quality is subconscious but powerful.

### Discomfort Lighting

| Effect | Implementation |
|--------|----------------|
| Flat light | Reduce shadow contrast by 20-30% |
| Diffused shadows | Increase shadow softness |
| Bloom bleed | Subtle bloom on bright sources |
| Haze | Distance fog density +10-20% |
| Color temperature | Slightly cooler (not obviously) |

### Comfort Lighting

| Effect | Implementation |
|--------|----------------|
| Crisp light | Full shadow contrast |
| Sharp shadows | Hard shadow edges |
| Clean highlights | No bloom bleed |
| Clear air | Minimal distance haze |
| Warm hints | Slightly warmer color temp |
| Light shafts | God rays in clearings |

---

## Motion Coherence System

The most powerful and least obvious lever.

### Incoherent Motion (Discomfort)

```
Foliage:
  - Wind direction varies per-plant
  - Animation speeds slightly different
  - Phase offsets randomized
  
Cloth/Banners:
  - Never fully settle
  - Micro-oscillations persist
  - Different wind response per element
  
Props:
  - Imperceptible jitter on small items
  - Hanging objects sway asynchronously
  - Flags/pennants cycle at different rates
```

### Coherent Motion (Comfort)

```
Foliage:
  - Unified wind direction
  - Synchronized wave patterns
  - Natural phase relationships
  
Cloth/Banners:
  - Settle properly
  - Unified wind response
  - Clean rest states
  
Props:
  - Completely still when appropriate
  - Synchronized micro-movements
  - Predictable patterns
```

---

## Attraction System

Pulling is harder than pushing. This system makes other places appealing.

### Attraction Signals

When a region broadcasts high pressure, neighboring low-pop regions receive:

| Signal | Effect |
|--------|--------|
| Light quality boost | +15% to comfort lighting |
| Wildlife surge | +25% spawn rate temporarily |
| Visual clarity | -10% haze, +10% contrast |
| Motion alignment | Extra coherence in animation |
| NPC vitality | More varied, relaxed behaviors |

### Distant Cues

Players should see attraction from afar:

```
Visual breadcrumbs:
  - Light breaking through trees in distance
  - Birds circling distant areas
  - Smoke rising (peaceful, not danger)
  - Movement at edge of vision
  
Not:
  - Glowing paths
  - UI markers
  - Obvious color differences
```

---

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

---

## Integration with LSE

### Shared Population Input

Both systems read from the same population metric but respond differently:

```python
population = get_region_population()

# LSE responds immediately with audio
lse.set_population(population)

# VDE responds with lag
vde.set_population_target(population)  # Smooths over time
```

### Pressure Coordinator

```python
class PressureCoordinator:
    def __init__(self, lse: LSEEngine, vde: VDEEngine):
        self.lse = lse
        self.vde = vde
        self.sdi_history = []
        self.vdi_lag = 10.0  # seconds
        
    def update(self, population: float, delta_time: float):
        # SDI updates immediately
        self.lse.set_population(population)
        
        # VDI follows with lag
        lagged_pop = self._calculate_lagged_population(population)
        self.vde.set_population(lagged_pop)
        
        # Prevent synchronized peaks
        if self._sdi_spiking():
            self.vde.hold_current()  # Pause VDI changes briefly
        
        # Broadcast attraction to neighbors
        if self.lse.sdi > 0.3 or self.vde.vdi > 0.3:
            self._broadcast_attraction()
```

---

## Example Scenarios

### Scenario 1: Forest Clearing Crowding

**Initial State:** 10% population, pristine

| Time | Population | SDI | VDI | Audio | Visual |
|------|------------|-----|-----|-------|--------|
| 0:00 | 10% | -0.15 | -0.20 | Birds, wind, peace | Clear light, wildlife, coherent motion |
| 1:00 | 35% | +0.05 | -0.10 | Insects louder | Wildlife starting to thin |
| 2:00 | 50% | +0.25 | +0.08 | Rhythm breaking | Motion incoherence begins |
| 3:00 | 70% | +0.45 | +0.30 | Drones, static | Light diffusing, wear visible |
| 4:00 | 85% | +0.65 | +0.50 | Harsh frequencies | No wildlife, NPCs uneasy |

### Scenario 2: Dispersal After Event

**Initial State:** 90% population, saturated

| Time | Population | SDI | VDI | Recovery Signal |
|------|------------|-----|-----|-----------------|
| 0:00 | 90% | +0.70 | +0.60 | Maximum pressure |
| 2:00 | 50% | +0.25 | +0.45 | Audio relief first |
| 4:00 | 30% | -0.05 | +0.20 | Visual still recovering |
| 6:00 | 20% | -0.15 | +0.05 | Wildlife returning |
| 8:00 | 15% | -0.20 | -0.15 | Full recovery |

---

## Implementation Phases

### Phase 1: Core VDE
- VDI calculation
- Population pressure phases
- Basic output parameters

### Phase 2: UE5 Integration
- Post-process parameter binding
- Material parameter system
- Niagara particle integration

### Phase 3: Wildlife System
- Spawn rate modulation
- Behavior state machine
- Recovery timing

### Phase 4: NPC Modulation
- Comfort level system
- Idle behavior selection
- Repositioning logic

### Phase 5: Environmental Wear
- Decal system
- Shader-driven grass trampling
- Wear accumulation/recovery

### Phase 6: Motion Coherence
- Wind system integration
- Animation phase control
- Prop micro-movement

### Phase 7: Attraction System
- Cross-region signaling
- Distant visual cues
- Light gradient system

### Phase 8: Pressure Coordinator
- LSE/VDE coupling
- Timing offset management
- Anti-synchronization logic

---

## Metrics and Tuning

### Success Metrics

| Metric | Target |
|--------|--------|
| Player-reported "crowding" | Correlates with actual pop |
| Voluntary dispersal rate | Increases with VDI |
| Time in high-pop regions | Decreases naturally |
| Player complaints about mechanics | Zero (invisible) |

### Tuning Parameters

All exposed for runtime adjustment:

```python
VDE_TUNING = {
    'vdi_lag_rise': 10.0,        # Seconds to follow SDI up
    'vdi_lag_fall': 15.0,        # Seconds to follow SDI down
    'wildlife_sensitivity': 1.0,  # How fast wildlife responds
    'wear_accumulation': 1.0,     # How fast wear builds
    'motion_incoherence_max': 0.3, # Maximum animation disruption
    'light_diffusion_max': 0.25,  # Maximum bloom/softness
    'attraction_radius': 500.0,   # Meters to broadcast attraction
    'attraction_strength': 0.15,  # Boost to nearby comfort
}
```

---

## Conclusion

The VDE creates a complete environmental pressure system when combined with the LSE:

1. **Audio leads** with SDI
2. **Visual follows** with VDI (lagged)
3. **Wildlife absence** provides emotional confirmation
4. **Environmental wear** provides logical explanation
5. **Attraction elsewhere** provides escape path

No UI. No warnings. No obvious mechanics.

Players leave because they **want** to, not because they're told to.
