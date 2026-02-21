# Visual Discomfort Index (VDI) System Design

## Overview

The Visual Discomfort Index (VDI) is a companion system to the Sensory Discomfort Index (SDI) that manipulates visual elements to subconsciously encourage player redistribution. While SDI operates through audio, VDI operates through subtle visual degradation and enhancement.

**Core Principle:** Audio and visual discomfort should **correlate, not mirror**. If both spike simultaneously, players detect manipulation. Instead, they lag and lead each other organically.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Population Pressure System                        │
├─────────────────────────────────────────────────────────────────────┤
│                              │                                       │
│              ┌───────────────┴───────────────┐                      │
│              ▼                               ▼                      │
│     ┌─────────────────┐             ┌─────────────────┐             │
│     │  SDI (Audio)    │             │  VDI (Visual)   │             │
│     │  - Leads by 5s  │◄───────────►│  - Lags by 5s   │             │
│     │  - Fast response│  Correlation│  - Slow response│             │
│     └────────┬────────┘             └────────┬────────┘             │
│              │                               │                      │
│              ▼                               ▼                      │
│     ┌─────────────────┐             ┌─────────────────┐             │
│     │ Discomfort      │             │ Fatigue         │             │
│     │ Sounds          │             │ Visuals         │             │
│     └─────────────────┘             └─────────────────┘             │
│                                                                      │
│                    ┌─────────────────┐                              │
│                    │ Attraction      │                              │
│                    │ System          │                              │
│                    │ (Low-pop areas) │                              │
│                    └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

## VDI Phases (Mirrors SDI Phases)

| Phase | Population | Visual Effects |
|-------|------------|----------------|
| NORMAL | 0-15% | Natural, coherent visuals |
| FATIGUE | 15-25% | Subtle clarity loss, wildlife absence begins |
| WEAR | 25-35% | Environmental wear visible, motion desync begins |
| STRESS | 35-50% | Noticeable busyness, light diffusion |
| STRAIN | 50-70% | Significant visual noise, NPC behavior changes |
| OVERLOAD | 70%+ | Maximum visual fatigue |

---

## Visual Discomfort Levers

### 1. Motion Instability (Weight: 0.25)

The most powerful subconscious signal. Humans read motion irregularity as cognitive load.

```json
{
  "motion_instability": {
    "foliage_desync": {
      "description": "Foliage animation becomes slightly out of phase",
      "parameter": "wind_phase_variance",
      "normal": 0.0,
      "max": 0.15,
      "curve": "quadratic"
    },
    "cloth_settle_delay": {
      "description": "Cloth and banners don't quite settle",
      "parameter": "cloth_damping_reduction", 
      "normal": 1.0,
      "max": 0.7,
      "curve": "linear"
    },
    "prop_micro_jitter": {
      "description": "Small props have imperceptible instability",
      "parameter": "prop_transform_noise",
      "normal": 0.0,
      "max": 0.002,
      "curve": "exponential"
    },
    "water_surface_unrest": {
      "description": "Water surfaces show subtle agitation",
      "parameter": "water_normal_noise",
      "normal": 0.0,
      "max": 0.08,
      "curve": "linear"
    }
  }
}
```

**Implementation Notes:**
- NOT glitchy — restless
- Changes should take 10-30 seconds to manifest
- Use Perlin noise, not random
- Affects only dynamic objects, not terrain

### 2. Visual Busyness (Weight: 0.20)

Crowded regions become harder to visually parse.

```json
{
  "visual_busyness": {
    "decal_density": {
      "description": "More overlapping decals (mud, footprints, wear)",
      "parameter": "decal_spawn_multiplier",
      "normal": 1.0,
      "max": 2.5,
      "types": ["footprints", "mud", "scuff_marks", "debris"]
    },
    "particle_density": {
      "description": "Higher particle density (dust, pollen, ash)",
      "parameter": "ambient_particle_multiplier",
      "normal": 1.0,
      "max": 1.8,
      "types": ["dust_motes", "pollen", "insects", "ash"]
    },
    "micro_detail_intensity": {
      "description": "More visual detail competing for attention",
      "parameter": "detail_texture_intensity",
      "normal": 1.0,
      "max": 1.3
    },
    "shadow_complexity": {
      "description": "More overlapping shadow patterns",
      "parameter": "shadow_cascade_blend",
      "normal": 0.5,
      "max": 0.8
    }
  }
}
```

**Implementation Notes:**
- Mirrors sound density concept
- Accumulates over time, doesn't spike
- Player's own movement contributes (more footprints when crowded)

### 3. Light Diffusion / Clarity Loss (Weight: 0.20)

Spaces feel "used up" or stale without being darker.

```json
{
  "clarity_loss": {
    "shadow_softness": {
      "description": "Shadows become less defined",
      "parameter": "shadow_penumbra_scale",
      "normal": 1.0,
      "max": 1.6
    },
    "bloom_bleed": {
      "description": "Slight bloom bleeding into mid-tones",
      "parameter": "bloom_threshold_reduction",
      "normal": 0.0,
      "max": 0.15
    },
    "contrast_reduction": {
      "description": "Reduced contrast at mid-range distances",
      "parameter": "distance_contrast_fade",
      "normal": 0.0,
      "max": 0.12,
      "start_distance": 15.0,
      "end_distance": 50.0
    },
    "atmospheric_haze": {
      "description": "Barely perceptible haze",
      "parameter": "height_fog_density_add",
      "normal": 0.0,
      "max": 0.003
    },
    "color_vibrancy": {
      "description": "Subtle desaturation (VERY subtle)",
      "parameter": "saturation_multiplier",
      "normal": 1.0,
      "max": 0.95,
      "note": "NEVER below 0.95 - must be imperceptible"
    }
  }
}
```

**Implementation Notes:**
- NEVER make it obviously darker or desaturated
- Aim for "less crisp" not "worse"
- Post-process effects should be region-blended, not hard-edged

### 4. Environmental Fatigue Cues (Weight: 0.15)

The world shows signs of overuse — social signals, not technical ones.

```json
{
  "environmental_fatigue": {
    "ground_wear": {
      "description": "Trampled grass, worn paths",
      "parameter": "terrain_wear_blend",
      "normal": 0.0,
      "max": 0.7,
      "recovery_rate": 0.01,
      "note": "Slow recovery when population drops"
    },
    "ground_discoloration": {
      "description": "Slight browning/muddying of ground",
      "parameter": "terrain_tint_blend",
      "normal": 0.0,
      "max": 0.3,
      "tint_color": [0.85, 0.80, 0.70]
    },
    "water_turbidity": {
      "description": "Water looks disturbed or murky",
      "parameter": "water_clarity",
      "normal": 1.0,
      "max": 0.6
    },
    "fire_smolder_duration": {
      "description": "Fire pits smolder longer than expected",
      "parameter": "ember_lifetime_multiplier",
      "normal": 1.0,
      "max": 3.0
    },
    "litter_accumulation": {
      "description": "Small debris near gathering spots",
      "parameter": "litter_spawn_rate",
      "normal": 0.0,
      "max": 0.4
    }
  }
}
```

**Implementation Notes:**
- These persist slightly after population drops (memory)
- Creates "this place has been busy" narrative
- Recovery should be slow (minutes, not seconds)

### 5. Life Absence (Weight: 0.20)

A quiet absence is more powerful than chaos.

```json
{
  "life_absence": {
    "wildlife_avoidance": {
      "description": "Animals avoid the area entirely",
      "parameter": "wildlife_spawn_suppression",
      "normal": 0.0,
      "max": 1.0,
      "affected": ["birds", "rabbits", "deer", "insects"]
    },
    "npc_comfort_reduction": {
      "description": "NPCs idle less comfortably",
      "parameter": "npc_idle_variety",
      "normal": 1.0,
      "max": 0.3,
      "behaviors_removed": ["sitting", "stretching", "looking_around", "whistling"]
    },
    "npc_repositioning": {
      "description": "Guards and vendors shift positions",
      "parameter": "npc_position_noise",
      "normal": 0.0,
      "max": 0.5
    },
    "ambient_life_density": {
      "description": "Fewer ambient life elements",
      "parameter": "ambient_creature_multiplier",
      "normal": 1.0,
      "max": 0.2,
      "affected": ["butterflies", "fireflies", "fish", "frogs"]
    },
    "birdsong_visual": {
      "description": "No visible birds on branches/roofs",
      "parameter": "perched_bird_spawn",
      "normal": 1.0,
      "max": 0.0,
      "note": "Couples directly with SDI wildlife suppression"
    }
  }
}
```

**Implementation Notes:**
- This is the visual equivalent of SDI's wildlife suppression
- Should lag SDI wildlife suppression by 5-10 seconds
- When birds stop singing, they should also stop being visible

---

## Visual Attraction Levers (Low-Population Areas)

These create **pull** toward less crowded regions.

### 1. Visual Calm and Coherence

```json
{
  "visual_calm": {
    "animation_alignment": {
      "description": "Wind and foliage move in harmony",
      "parameter": "wind_direction_coherence",
      "low_pop": 1.0,
      "high_pop": 0.6
    },
    "lighting_intention": {
      "description": "Lighting feels deliberate and composed",
      "parameter": "light_flicker_reduction",
      "low_pop": 0.0,
      "high_pop": 0.3
    },
    "effect_separation": {
      "description": "Fewer overlapping visual effects",
      "parameter": "effect_density_cap",
      "low_pop": 0.5,
      "high_pop": 1.0
    },
    "spatial_clarity": {
      "description": "Easier to read space and depth",
      "parameter": "depth_fog_contrast",
      "low_pop": 1.0,
      "high_pop": 0.85
    }
  }
}
```

### 2. Life Density (Not Players)

Humans gravitate toward life, not people.

```json
{
  "life_attraction": {
    "wildlife_presence": {
      "description": "More visible wildlife",
      "parameter": "wildlife_spawn_bonus",
      "low_pop": 1.5,
      "high_pop": 0.0
    },
    "npc_engagement": {
      "description": "NPCs show rich idle behaviors",
      "parameter": "npc_idle_richness",
      "low_pop": 1.0,
      "high_pop": 0.3
    },
    "micro_interactions": {
      "description": "Small environmental interactions",
      "parameter": "ambient_interaction_rate",
      "low_pop": 1.0,
      "high_pop": 0.2,
      "examples": ["birds_landing", "insects_hovering", "leaves_falling", "fish_jumping"]
    }
  }
}
```

### 3. Light as Guidance

Use light the way architecture does.

```json
{
  "light_guidance": {
    "warmth_gradient": {
      "description": "Slightly warmer light in target regions",
      "parameter": "light_temperature_offset",
      "low_pop": 200,
      "high_pop": -100,
      "unit": "kelvin"
    },
    "sun_breaks": {
      "description": "Sun breaks in clearings",
      "parameter": "god_ray_probability",
      "low_pop": 0.4,
      "high_pop": 0.1
    },
    "reflective_highlights": {
      "description": "Reflections that draw the eye",
      "parameter": "specular_intensity_bonus",
      "low_pop": 0.15,
      "high_pop": 0.0
    }
  }
}
```

### 4. Environmental Affordances

Make low-pop areas visually inviting.

```json
{
  "environmental_affordance": {
    "path_clarity": {
      "description": "Clear, readable paths",
      "parameter": "path_visibility_boost",
      "low_pop": 0.2,
      "high_pop": 0.0
    },
    "sightline_openness": {
      "description": "Open sightlines, less occlusion",
      "parameter": "foliage_density_reduction",
      "low_pop": 0.15,
      "high_pop": 0.0
    },
    "framing_emphasis": {
      "description": "Natural framing elements highlighted",
      "parameter": "framing_light_boost",
      "low_pop": 0.1,
      "high_pop": 0.0,
      "affected": ["arches", "tree_frames", "rock_formations"]
    },
    "landmark_visibility": {
      "description": "Distant landmarks feel reachable",
      "parameter": "landmark_atmospheric_reduction",
      "low_pop": 0.3,
      "high_pop": 0.0
    }
  }
}
```

### 5. Subtle Environmental Rewards

Not loot — promise.

```json
{
  "environmental_promise": {
    "discovery_hints": {
      "description": "Ruins partially revealed, caves suggested",
      "parameter": "discovery_visibility",
      "low_pop": 0.8,
      "high_pop": 0.3
    },
    "distant_movement": {
      "description": "Movement in the distance (animals, NPCs)",
      "parameter": "distant_activity_spawn",
      "low_pop": 0.6,
      "high_pop": 0.1
    },
    "curiosity_cues": {
      "description": "Visual + audio cues suggesting activity",
      "parameter": "curiosity_event_rate",
      "low_pop": 0.4,
      "high_pop": 0.05
    }
  }
}
```

---

## SDI-VDI Coupling Rules

### Timing Relationship

```
Population Change
       │
       ├──► SDI responds (0-5 seconds)
       │         │
       │         └──► Discomfort sounds begin
       │
       └──► VDI responds (5-15 seconds lag)
                 │
                 └──► Visual fatigue manifests
```

**Key Principle:** SDI leads, VDI lags. This feels organic.

### Correlation, Not Mirroring

```python
# WRONG - Direct mirror
vdi_value = sdi_value

# RIGHT - Correlated with lag and noise
vdi_target = sdi_value * 0.8 + random_noise(0.1)
vdi_value = lerp(vdi_value, vdi_target, 0.02)  # Slow interpolation
```

### Cross-System Coherence

| SDI Event | VDI Response | Timing |
|-----------|--------------|--------|
| Wildlife suppression starts | Birds stop landing | +5-10s |
| Discomfort sounds begin | Motion desync begins | +8-12s |
| Static layer activates | Atmospheric haze increases | +10-15s |
| Rhythm instability rises | Foliage desync increases | +5-8s |
| Silence phase | Life absence visual | +3-5s |

### Attraction Coupling

When population drops in an area:
1. SDI attraction cues activate immediately (comfortable sounds)
2. VDI attraction cues fade in over 30-60 seconds
3. Wildlife returns visually 10-15s after audio wildlife returns

---

## Anti-Patterns (NEVER DO)

### Visual Punishments
- ❌ Obvious desaturation
- ❌ Screen shake
- ❌ Vignetting
- ❌ Color grading shifts
- ❌ Camera effects tied to population

### Obvious Signals
- ❌ UI warnings about crowding
- ❌ Fog walls at region boundaries
- ❌ Particle effects that say "leave"
- ❌ NPC dialogue about crowds

### Synchronized Spikes
- ❌ SDI and VDI rising together
- ❌ All effects activating at once
- ❌ Hard thresholds with sudden changes

**The Rule:** If players notice the system, it's dead.

---

## Concrete Example: Forest Clearing

### High Population (60%)

**Audio (SDI):**
- Insects louder, less rhythmic
- Bird calls reduced
- Tonal drone barely audible
- Rhythm instability: 0.15

**Visual (VDI):**
- Foliage slightly restless (phase variance: 0.08)
- No birds visible on branches
- Ground shows wear patterns
- Light feels flat (contrast reduction: 0.08)
- More dust particles
- Fire pit still smoldering from hours ago

### Nearby Low-Pop Grove (10%)

**Audio (SDI):**
- Calm, rhythmic insects
- Birds calling and responding
- Gentle wind
- Predictable rhythm bonus

**Visual (VDI):**
- Wind moves foliage in harmony
- Clear light shafts through canopy
- Birds visible at mid-distance
- Clean ground, readable paths
- Butterflies near flowers
- Distant deer visible through trees

**No signpost says "go here."**

---

## Implementation Priority

### Phase 1: Core Coupling
1. Population pressure → VDI phase calculation
2. SDI-VDI timing relationship
3. Basic wildlife visual suppression

### Phase 2: Motion Systems
1. Foliage desync
2. Cloth/banner animation
3. Water surface unrest

### Phase 3: Environmental Wear
1. Ground wear textures
2. Decal accumulation
3. Turbidity systems

### Phase 4: Attraction Systems
1. Light warmth gradients
2. Wildlife spawn bonuses
3. NPC behavior richness

### Phase 5: Polish
1. Smooth transitions
2. Regional blending
3. Cross-system coherence testing

---

## Data Model

```python
@dataclass
class VDIState:
    phase: VDIPhase
    population: float
    
    # Discomfort modifiers (0.0 to 1.0)
    motion_instability: float = 0.0
    visual_busyness: float = 0.0
    clarity_loss: float = 0.0
    environmental_fatigue: float = 0.0
    life_absence: float = 0.0
    
    # Attraction modifiers (0.0 to 1.0)  
    visual_calm: float = 0.0
    life_attraction: float = 0.0
    light_guidance: float = 0.0
    environmental_affordance: float = 0.0
    environmental_promise: float = 0.0
    
    # Coupling state
    sdi_reference: float = 0.0
    lag_buffer: List[float] = field(default_factory=list)
    
    def calculate_composite_vdi(self) -> float:
        discomfort = (
            self.motion_instability * 0.25 +
            self.visual_busyness * 0.20 +
            self.clarity_loss * 0.20 +
            self.environmental_fatigue * 0.15 +
            self.life_absence * 0.20
        )
        
        attraction = (
            self.visual_calm * 0.20 +
            self.life_attraction * 0.25 +
            self.light_guidance * 0.20 +
            self.environmental_affordance * 0.20 +
            self.environmental_promise * 0.15
        )
        
        return discomfort - attraction
```

---

## Integration with LSE

The VDI system should:
1. Read population from the same source as LSE
2. Read SDI values from LSE (for correlation)
3. Apply its own lag and smoothing
4. Output parameters to UE5 material/lighting systems

```python
class VDIEngine:
    def __init__(self, lse_engine: LSEEngine):
        self.lse = lse_engine
        self.state = VDIState()
        self.sdi_history = []  # For lag calculation
        
    def tick(self, delta_time: float):
        # Get current SDI
        current_sdi = self.lse.sdi
        self.sdi_history.append(current_sdi)
        
        # Use lagged SDI (5-10 seconds ago)
        lag_samples = int(8.0 / delta_time)  # 8 second lag
        if len(self.sdi_history) > lag_samples:
            lagged_sdi = self.sdi_history[-lag_samples]
        else:
            lagged_sdi = current_sdi
        
        # Update VDI based on lagged SDI + population
        self._update_discomfort(lagged_sdi)
        self._update_attraction()
        
        return self.state
```

---

## Success Metrics

The system is working if:
1. Players leave crowded areas without knowing why
2. Players are drawn to low-pop areas without knowing why
3. No player ever mentions "the crowd system"
4. Population naturally balances across regions
5. The world feels "alive" and "responsive"

The system has failed if:
1. Players complain about "the fog/blur/darkness"
2. Players identify population-based changes
3. Reddit posts appear analyzing "the crowd mechanic"
4. Players feel punished for being in groups
