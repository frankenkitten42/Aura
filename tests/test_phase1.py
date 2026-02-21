#!/usr/bin/env python3
"""
Phase 1 Test Script for Living Soundscape Engine

Tests that all foundation modules load and work correctly:
- utils: Math functions and RNG
- config: Loading JSON files into typed models
- core: State management and clock

Run from the lse directory:
    python tests/test_phase1.py
"""

import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, src_path)

from utils import clamp, lerp, smoothstep, exp_smooth, SeededRNG
from utils.math_utils import variance, coefficient_of_variation
from utils.rng import RNGManager
from config import load_config, ConfigLoader
from core.state import SimulationState, EnvironmentState, SDIState, SoundEvent, SoundMemory
from core.clock import SimulationClock


def test_math_utils():
    """Test math utility functions."""
    print("\n=== Testing Math Utils ===")
    
    # Test clamp
    assert clamp(1.5, 0.0, 1.0) == 1.0, "clamp high failed"
    assert clamp(-0.5, 0.0, 1.0) == 0.0, "clamp low failed"
    assert clamp(0.5, 0.0, 1.0) == 0.5, "clamp middle failed"
    print("  ✓ clamp")
    
    # Test lerp
    assert lerp(0.0, 10.0, 0.5) == 5.0, "lerp failed"
    assert lerp(0.0, 10.0, 0.0) == 0.0, "lerp start failed"
    assert lerp(0.0, 10.0, 1.0) == 10.0, "lerp end failed"
    print("  ✓ lerp")
    
    # Test smoothstep
    assert smoothstep(0.0, 1.0, 0.0) == 0.0, "smoothstep start failed"
    assert smoothstep(0.0, 1.0, 1.0) == 1.0, "smoothstep end failed"
    assert 0.4 < smoothstep(0.0, 1.0, 0.5) < 0.6, "smoothstep middle failed"
    print("  ✓ smoothstep")
    
    # Test exp_smooth
    result = exp_smooth(0.0, 1.0, 0.2)
    assert result == 0.2, f"exp_smooth failed: {result}"
    print("  ✓ exp_smooth")
    
    # Test variance
    v = variance([1, 2, 3, 4, 5])
    assert 1.9 < v < 2.1, f"variance failed: {v}"
    print("  ✓ variance")
    
    # Test coefficient of variation
    cv = coefficient_of_variation([10, 10, 10])
    assert cv == 0.0, f"cv perfect failed: {cv}"
    print("  ✓ coefficient_of_variation")
    
    print("  All math utils tests passed!")


def test_rng():
    """Test random number generation."""
    print("\n=== Testing RNG ===")
    
    # Test seeded reproducibility
    rng1 = SeededRNG(seed=42)
    rng2 = SeededRNG(seed=42)
    
    v1 = [rng1.random() for _ in range(10)]
    v2 = [rng2.random() for _ in range(10)]
    assert v1 == v2, "Seeded RNG not reproducible"
    print("  ✓ Seeded reproducibility")
    
    # Test probability
    rng = SeededRNG(seed=123)
    assert rng.probability(1.0) == True, "probability 1.0 failed"
    assert rng.probability(0.0) == False, "probability 0.0 failed"
    print("  ✓ probability")
    
    # Test weighted choice
    rng = SeededRNG(seed=456)
    choices = [rng.weighted_choice(['a', 'b'], [0, 1]) for _ in range(10)]
    assert all(c == 'b' for c in choices), "weighted_choice failed"
    print("  ✓ weighted_choice")
    
    # Test vary
    rng = SeededRNG(seed=789)
    varied = rng.vary(10.0, 0.1)
    assert 9.0 <= varied <= 11.0, f"vary out of range: {varied}"
    print("  ✓ vary")
    
    # Test RNG manager
    manager = RNGManager(master_seed=42)
    rng_a = manager.get('sounds')
    rng_b = manager.get('timing')
    assert rng_a.seed != rng_b.seed, "RNG streams should have different seeds"
    print("  ✓ RNGManager")
    
    print("  All RNG tests passed!")


def test_config_loading():
    """Test configuration loading."""
    print("\n=== Testing Config Loading ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    
    # Test full config load
    config = load_config(config_dir)
    print(f"  ✓ Loaded config from {config_dir}")
    
    # Check biomes
    assert len(config.biomes) > 0, "No biomes loaded"
    assert 'forest' in config.biomes, "Forest biome not found"
    forest = config.biomes['forest']
    assert forest.parameters.baseline_density == 8.0, "Forest density wrong"
    print(f"  ✓ Loaded {len(config.biomes)} biomes")
    
    # Check sounds
    assert len(config.sounds) > 0, "No sounds loaded"
    assert 'birdsong' in config.sounds, "Birdsong not found"
    birdsong = config.sounds['birdsong']
    assert birdsong.layer == 'periodic', "Birdsong layer wrong"
    assert 'day' in birdsong.time_constraints, "Birdsong time constraint wrong"
    print(f"  ✓ Loaded {len(config.sounds)} sounds")
    
    # Check SDI factors
    assert len(config.sdi.discomfort_factors) > 0, "No discomfort factors"
    assert len(config.sdi.comfort_factors) > 0, "No comfort factors"
    print(f"  ✓ Loaded {len(config.sdi.discomfort_factors)} discomfort factors")
    print(f"  ✓ Loaded {len(config.sdi.comfort_factors)} comfort factors")
    
    # Check population curve
    assert len(config.population.curve.points) > 0, "No population curve points"
    print(f"  ✓ Loaded population curve with {len(config.population.curve.points)} points")
    
    # Check conflicts
    assert len(config.conflicts.sound_conflicts) > 0, "No sound conflicts"
    assert len(config.conflicts.harmony_pairs) > 0, "No harmony pairs"
    print(f"  ✓ Loaded {len(config.conflicts.sound_conflicts)} conflicts, "
          f"{len(config.conflicts.harmony_pairs)} harmony pairs")
    
    # Check weather/time modifiers
    assert 'clear' in config.weather_modifiers, "Clear weather not found"
    assert 'day' in config.time_modifiers, "Day time modifier not found"
    print(f"  ✓ Loaded {len(config.weather_modifiers)} weather modifiers")
    print(f"  ✓ Loaded {len(config.time_modifiers)} time modifiers")
    
    # Test derived lookups
    periodic_sounds = config.get_sounds_by_layer('periodic')
    assert len(periodic_sounds) > 0, "No periodic sounds found"
    print(f"  ✓ Derived lookup: {len(periodic_sounds)} periodic sounds")
    
    forest_sounds = config.get_biome_sounds('forest')
    assert len(forest_sounds) > 0, "No forest sounds found"
    print(f"  ✓ Biome lookup: {len(forest_sounds)} forest sounds")
    
    print("  All config loading tests passed!")


def test_state():
    """Test state management."""
    print("\n=== Testing State Management ===")
    
    # Test SimulationState creation
    state = SimulationState()
    assert state.tick == 0, "Initial tick wrong"
    assert state.timestamp == 0.0, "Initial timestamp wrong"
    assert len(state.active_sounds) == 0, "Should have no active sounds"
    print("  ✓ SimulationState creation")
    
    # Test tick advancement
    state.advance_tick(1.0)
    assert state.tick == 1, "Tick not advanced"
    assert state.timestamp == 1.0, "Timestamp not advanced"
    print("  ✓ Tick advancement")
    
    # Test environment state
    env = state.environment
    assert env.biome_id == "forest", "Default biome wrong"
    assert env.time_of_day == "day", "Default time wrong"
    assert env.weather == "clear", "Default weather wrong"
    print("  ✓ EnvironmentState defaults")
    
    # Test SDI state
    sdi = state.sdi
    assert sdi.raw_sdi == 0.0, "Initial raw SDI wrong"
    assert sdi.smoothed_sdi == 0.0, "Initial smoothed SDI wrong"
    sdi.update(0.5, 0.2)
    assert sdi.raw_sdi == 0.5, "Raw SDI not updated"
    assert sdi.smoothed_sdi == 0.1, "Smoothed SDI wrong"
    print("  ✓ SDIState update")
    
    # Test SDI contributions
    contrib = sdi.contributions
    contrib.density_overload = 0.15
    contrib.layer_harmony = -0.08
    top_pos = contrib.get_top_positive()
    top_neg = contrib.get_top_negative()
    assert top_pos[0] == 'density_overload', f"Top positive wrong: {top_pos}"
    assert top_neg[0] == 'layer_harmony', f"Top negative wrong: {top_neg}"
    print("  ✓ SDI contributions tracking")
    
    # Test sound memory
    memory = state.sound_memory
    event = SoundEvent(
        sound_id='birdsong',
        timestamp=1.0,
        duration=4.0,
        intensity=0.5,
        layer='periodic'
    )
    memory.add_event(event)
    assert len(memory.recent_events) == 1, "Event not added"
    assert 'birdsong' in memory.patterns, "Pattern not created"
    print("  ✓ SoundMemory event tracking")
    
    # Test pattern tracking
    memory.add_event(SoundEvent(sound_id='birdsong', timestamp=5.0, duration=4.0, intensity=0.5, layer='periodic'))
    memory.add_event(SoundEvent(sound_id='birdsong', timestamp=9.0, duration=4.0, intensity=0.5, layer='periodic'))
    pattern = memory.get_pattern('birdsong')
    assert len(pattern.occurrences) == 3, "Pattern occurrences wrong"
    assert len(pattern.intervals) == 2, "Pattern intervals wrong"
    print("  ✓ Pattern tracking")
    
    # Test state reset
    state.reset()
    assert state.tick == 0, "Reset tick failed"
    assert len(state.active_sounds) == 0, "Reset active sounds failed"
    print("  ✓ State reset")
    
    print("  All state management tests passed!")


def test_clock():
    """Test simulation clock."""
    print("\n=== Testing Simulation Clock ===")
    
    # Test creation and defaults
    clock = SimulationClock(game_hour=12.0)
    assert clock.game_hour == 12.0, "Initial hour wrong"
    assert clock.time_of_day_str == "day", "Initial time of day wrong"
    print("  ✓ Clock creation")
    
    # Test time of day detection
    clock.set_game_hour(6.0)
    assert clock.time_of_day_str == "dawn", "Dawn detection failed"
    clock.set_game_hour(22.0)
    assert clock.time_of_day_str == "night", "Night detection failed"
    clock.set_game_hour(2.0)
    assert clock.time_of_day_str == "midnight", "Midnight detection failed"
    print("  ✓ Time of day detection")
    
    # Test tick advancement
    clock.reset(game_hour=12.0)
    clock.hours_per_minute = 60.0  # 1 hour per second for testing
    clock.tick()
    assert clock.simulation_time == 1.0, "Simulation time not advanced"
    assert clock.game_hour > 12.0, "Game hour not advanced"
    print("  ✓ Tick advancement")
    
    # Test time constraints
    clock.set_game_hour(14.0)  # Day
    assert clock.matches_constraint("all") == True, "all constraint failed"
    assert clock.matches_constraint("day") == True, "day constraint failed"
    assert clock.matches_constraint("night") == False, "night constraint failed"
    print("  ✓ Time constraints")
    
    # Test is_day/is_night
    clock.set_game_hour(14.0)
    assert clock.is_day == True, "is_day failed"
    assert clock.is_night == False, "is_night failed"
    clock.set_game_hour(23.0)
    assert clock.is_day == False, "is_day night failed"
    assert clock.is_night == True, "is_night night failed"
    print("  ✓ Day/night detection")
    
    # Test format_time
    clock.set_game_hour(14.5)
    formatted = clock.format_time()
    assert formatted == "14:30", f"format_time failed: {formatted}"
    print("  ✓ Time formatting")
    
    # Test pause/resume
    clock.pause()
    time_before = clock.simulation_time
    clock.tick()
    assert clock.simulation_time == time_before, "Clock should be paused"
    clock.resume()
    clock.tick()
    assert clock.simulation_time > time_before, "Clock should advance after resume"
    print("  ✓ Pause/resume")
    
    print("  All clock tests passed!")


def test_integration():
    """Test that all components work together."""
    print("\n=== Testing Integration ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    
    # Load config
    config = load_config(config_dir)
    
    # Create state
    state = SimulationState()
    
    # Create clock
    clock = SimulationClock(game_hour=10.0)  # Morning
    
    # Set up environment from config
    biome = config.biomes['forest']
    state.environment.biome_id = 'forest'
    state.environment.biome_parameters = biome.parameters
    state.environment.time_of_day = clock.time_of_day_str
    
    # Verify integration
    assert state.environment.biome_parameters.baseline_density == 8.0
    assert state.environment.time_of_day == 'day'
    print("  ✓ Config + State + Clock integration")
    
    # Simulate a few ticks
    for i in range(10):
        clock.tick()
        state.advance_tick(clock.tick_rate)
        state.environment.time_of_day = clock.time_of_day_str
    
    assert state.tick == 10, "Ticks not accumulated"
    print("  ✓ Multi-tick simulation")
    
    # Create a snapshot
    snapshot = state.to_snapshot()
    assert 'tick' in snapshot
    assert 'biome' in snapshot
    assert snapshot['biome'] == 'forest'
    print("  ✓ State snapshot creation")
    
    print("  All integration tests passed!")


def main():
    """Run all Phase 1 tests."""
    print("=" * 60)
    print("Living Soundscape Engine - Phase 1 Tests")
    print("=" * 60)
    
    try:
        test_math_utils()
        test_rng()
        test_config_loading()
        test_state()
        test_clock()
        test_integration()
        
        print("\n" + "=" * 60)
        print("ALL PHASE 1 TESTS PASSED!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
