# Changelog

All notable changes to AURA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-09

### Added

#### Visual Discomfort Engine (VDE) - 8 Phases Complete

- **Phase 1: Core VDI**
  - VDI calculation based on population pressure
  - Visual phase system (Pristine → Comfortable → Uneasy → Stressed → Overwhelmed)
  - Output parameter generation

- **Phase 2: UE5 Integration**
  - Post-process parameter binding
  - Material Parameter Collection integration
  - Niagara particle system parameters
  - C++ header generation for UE5

- **Phase 3: Wildlife System**
  - 3-tier creature sensitivity (Skittish, Wary, Bold)
  - 11 creature categories
  - State machine with asymmetric transitions
  - Recovery timing with "memory" effect
  - UE5-ready spawn commands

- **Phase 4: NPC Modulation**
  - 8 NPC type profiles (Guard, Vendor, Worker, Ambient, etc.)
  - 5 comfort levels
  - 20+ idle behavior repertoire
  - Edge-seeking and repositioning logic
  - Interaction radius modulation

- **Phase 5: Environmental Wear**
  - 3-layer wear system (Displacement, Discoloration, Damage)
  - 9 surface types with unique characteristics
  - Asymmetric accumulation/recovery timing
  - Shader-ready wear parameters

- **Phase 6: Motion Coherence**
  - 4 coherence levels (Unified, Natural, Varied, Chaotic)
  - 6 motion categories (Foliage, Cloth, Props, Water, Particles, NPCs)
  - Wind direction and variance control
  - Phase synchronization management
  - Settling mechanics with residual motion

- **Phase 7: Attraction System**
  - 5 attraction strength levels
  - 5 signal boost types (Light, Wildlife, Clarity, Motion, NPC)
  - 6 distant visual cue types
  - Cross-region attraction coordination
  - Neighbor pressure influence

- **Phase 8: Pressure Coordinator**
  - SDI/VDI coupling with configurable lag
  - Anti-synchronization logic
  - Asymmetric rise/fall timing
  - Pressure phase detection
  - Cross-region attraction broadcasting
  - Scenario simulation tools

#### Audio Systems (SDI)

- Soundscape Discomfort Index calculation
- 6 discomfort factors with weighted contributions
- Layer-based audio mixing
- Population pressure effects
- Sound memory and pattern recognition

#### Tools

- `termux_simulator.py` - Interactive terminal simulator
- `ue5_server.py` - HTTP server for UE5 integration
- UE5 integration documentation

#### Documentation

- Comprehensive README
- VDE design specification
- UE5 integration guide
- Configuration reference

### Technical

- 299 passing tests
- Python 3.8+ compatibility
- JSON configuration system
- UE5-ready parameter output

## [0.1.0] - 2026-02-07

### Added

- Initial project structure
- Basic SDI calculation
- Proof of concept implementation

---

## Roadmap

### Future Considerations

- [ ] WebSocket server for lower-latency UE5 communication
- [ ] Native C++ port for shipping games
- [ ] Additional biome presets
- [ ] Blueprint function library for UE5
- [ ] Real-time tuning interface
- [ ] Analytics and telemetry hooks
