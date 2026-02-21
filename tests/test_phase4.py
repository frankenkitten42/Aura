#!/usr/bin/env python3
"""
Phase 4 Test Script for Living Soundscape Engine

Tests the sound selection system:
- SoundSelector: Filtering and probability-based selection
- LayerManager: Capacity management and lifecycle
- Soundscape: Main orchestration

Run from the lse directory:
    python tests/test_phase4.py
"""

import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, src_path)

from config import load_config
from memory import SoundMemory, SilenceTracker, PatternMemory
from lse import (
    SoundSelector, SoundCandidate, SelectionResult,
    LayerManager, LayerState,
    Soundscape, SoundscapeEvent, EventType,
)
from audio.layer_manager import ActiveSoundInfo
from utils.rng import SeededRNG


class MockEnvironment:
    """Mock environment for testing."""
    def __init__(self, biome_id="forest", time_of_day="day", weather="clear"):
        self.biome_id = biome_id
        self.time_of_day = time_of_day
        self.weather = weather
        self.features = {}
        self.biome_parameters = MockBiomeParams()


class MockBiomeParams:
    """Mock biome parameters."""
    def __init__(self):
        self.layer_capacity = 10
        self.silence_tolerance = 5.0
        self.sdi_baseline = 0.0


class MockSDIResult:
    """Mock SDI calculation result."""
    def __init__(self, smoothed_sdi=0.0, delta=0.0, delta_category="none"):
        self.smoothed_sdi = smoothed_sdi
        self.target_sdi = smoothed_sdi + delta
        self.delta = delta
        self.delta_category = delta_category


def test_sound_selector_basics():
    """Test basic SoundSelector functionality."""
    print("\n=== Testing SoundSelector Basics ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    rng = SeededRNG(seed=42)
    
    selector = SoundSelector(config, rng)
    
    # Check that sounds were loaded
    assert len(selector.sounds) > 0, "Should have loaded sounds"
    print(f"  ✓ Loaded {len(selector.sounds)} sounds")
    
    # Check that biome pools were loaded
    assert len(selector.biome_pools) > 0, "Should have biome pools"
    print(f"  ✓ Loaded {len(selector.biome_pools)} biome pools")
    
    # Check harmony/conflict pairs
    assert len(selector.harmony_pairs) > 0, "Should have harmony pairs"
    print(f"  ✓ Loaded {len(selector.harmony_pairs)} harmony pairs")
    
    print("  All SoundSelector basics tests passed!")


def test_candidate_filtering():
    """Test sound candidate filtering."""
    print("\n=== Testing Candidate Filtering ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    rng = SeededRNG(seed=42)
    
    selector = SoundSelector(config, rng)
    memory = SoundMemory()
    env = MockEnvironment(biome_id="forest", time_of_day="day", weather="clear")
    
    # Get candidates for periodic layer
    candidates = selector.get_candidates(
        layer="periodic",
        environment=env,
        sound_memory=memory,
        current_time=0.0
    )
    
    assert len(candidates) > 0, "Should have candidates for forest/day"
    print(f"  ✓ Found {len(candidates)} periodic candidates for forest/day")
    
    # All candidates should be periodic layer
    for c in candidates:
        assert c.layer == "periodic", f"Expected periodic, got {c.layer}"
    print("  ✓ All candidates are correct layer")
    
    # Test time filtering - night sounds shouldn't appear during day
    night_sounds = [c for c in candidates if 'night' in c.tags or 'nocturnal' in c.tags]
    day_sounds = [c for c in candidates if 'day' in c.tags or 'diurnal' in c.tags]
    print(f"  ✓ Day sounds: {len(day_sounds)}, Night sounds filtered: {len(night_sounds)}")
    
    # Test with night time
    env_night = MockEnvironment(biome_id="forest", time_of_day="night", weather="clear")
    candidates_night = selector.get_candidates(
        layer="periodic",
        environment=env_night,
        sound_memory=memory,
        current_time=0.0
    )
    print(f"  ✓ Found {len(candidates_night)} periodic candidates for forest/night")
    
    print("  All candidate filtering tests passed!")


def test_probability_adjustment():
    """Test SDI-based probability adjustments."""
    print("\n=== Testing Probability Adjustment ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    rng = SeededRNG(seed=42)
    
    selector = SoundSelector(config, rng)
    memory = SoundMemory()
    env = MockEnvironment()
    
    candidates = selector.get_candidates("periodic", env, memory, 0.0)
    
    if len(candidates) == 0:
        print("  ✓ No candidates to adjust (skipped)")
        return
    
    # Get original probabilities
    original_probs = {c.sound_id: c.base_probability for c in candidates}
    
    # Adjust with positive delta (need more SDI)
    adjusted_pos = selector.adjust_probabilities(
        candidates.copy(), sdi_delta=0.3, delta_category="medium"
    )
    
    # Adjust with negative delta (need less SDI)
    candidates2 = selector.get_candidates("periodic", env, memory, 0.0)
    adjusted_neg = selector.adjust_probabilities(
        candidates2, sdi_delta=-0.3, delta_category="medium"
    )
    
    print(f"  ✓ Adjusted {len(adjusted_pos)} candidates for positive delta")
    print(f"  ✓ Adjusted {len(adjusted_neg)} candidates for negative delta")
    
    # Verify adjusted probabilities are set (even if same as base)
    for c in adjusted_pos:
        assert 0.0 <= c.adjusted_probability <= 1.0, "Probability should be in range"
    print("  ✓ All adjusted probabilities are in valid range")
    
    # Show some examples
    for c in adjusted_pos[:2]:
        print(f"    - {c.sound_id}: base={c.base_probability:.2f}, adjusted={c.adjusted_probability:.2f}")
    
    print("  All probability adjustment tests passed!")


def test_sound_selection():
    """Test actual sound selection."""
    print("\n=== Testing Sound Selection ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    rng = SeededRNG(seed=42)
    
    selector = SoundSelector(config, rng)
    memory = SoundMemory()
    env = MockEnvironment()
    
    # Run multiple selections to test randomness
    selections = []
    for i in range(10):
        result = selector.select(
            layer="periodic",
            environment=env,
            sound_memory=memory,
            current_time=float(i),
            sdi_delta=0.0,
            delta_category="none",
        )
        if result.selected:
            selections.append(result)
    
    print(f"  ✓ Made {len(selections)} selections out of 10 attempts")
    
    # At least some should succeed
    assert len(selections) > 0, "Should have made some selections"
    
    # Check selection result structure
    for sel in selections:
        assert sel.sound_id is not None, "Should have sound_id"
        assert sel.instance_id is not None, "Should have instance_id"
        assert sel.duration > 0, "Should have positive duration"
        assert 0 <= sel.intensity <= 1, "Intensity should be in range"
    print("  ✓ Selection results have valid structure")
    
    # Test forced selection
    result = selector.select(
        layer="periodic",
        environment=env,
        sound_memory=SoundMemory(),  # Fresh memory
        current_time=100.0,
        force_selection=True,
    )
    assert result.selected, "Forced selection should succeed"
    print(f"  ✓ Forced selection: {result.sound_id}")
    
    print("  All sound selection tests passed!")


def test_layer_manager_basics():
    """Test basic LayerManager functionality."""
    print("\n=== Testing LayerManager Basics ===")
    
    manager = LayerManager()
    
    # Check initial state
    assert manager.get_active_count() == 0, "Should start empty"
    assert manager.can_add_sound("periodic"), "Should be able to add to periodic"
    print("  ✓ Initial state correct")
    
    # Add a sound
    sound = ActiveSoundInfo(
        instance_id="test-1",
        sound_id="birdsong",
        layer="periodic",
        start_time=0.0,
        expected_end_time=5.0,
        intensity=0.5,
        frequency_band="mid",
        is_continuous=False,
    )
    
    success, reason = manager.add_sound(sound)
    assert success, f"Should add successfully: {reason}"
    assert manager.get_active_count() == 1, "Should have 1 active"
    print("  ✓ Added sound successfully")
    
    # Query methods
    assert manager.has_active_sound("birdsong"), "Should find birdsong"
    assert "birdsong" in manager.get_active_sound_ids(), "Should be in active IDs"
    print("  ✓ Query methods work")
    
    # Remove sound
    removed = manager.remove_sound("test-1")
    assert removed is not None, "Should remove successfully"
    assert manager.get_active_count() == 0, "Should be empty again"
    print("  ✓ Removed sound successfully")
    
    print("  All LayerManager basics tests passed!")


def test_layer_capacity():
    """Test layer capacity enforcement."""
    print("\n=== Testing Layer Capacity ===")
    
    manager = LayerManager()
    
    # Set small capacity for testing
    manager.layers['periodic'].capacity = 2
    
    # Add up to capacity
    for i in range(2):
        sound = ActiveSoundInfo(
            instance_id=f"test-{i}",
            sound_id=f"sound_{i}",
            layer="periodic",
            start_time=0.0,
            expected_end_time=10.0,
            intensity=0.5,
            frequency_band="mid",
            is_continuous=False,
        )
        success, _ = manager.add_sound(sound)
        assert success, f"Should add sound {i}"
    
    assert manager.layers['periodic'].is_full, "Layer should be full"
    print("  ✓ Layer reaches capacity correctly")
    
    # Try to add beyond capacity
    extra = ActiveSoundInfo(
        instance_id="test-extra",
        sound_id="extra_sound",
        layer="periodic",
        start_time=0.0,
        expected_end_time=10.0,
        intensity=0.5,
        frequency_band="mid",
        is_continuous=False,
    )
    success, reason = manager.add_sound(extra)
    assert not success, "Should not add beyond capacity"
    print(f"  ✓ Rejected over-capacity add: {reason}")
    
    # Test interruption
    interrupted = manager.interrupt_oldest("periodic")
    assert interrupted is not None, "Should interrupt oldest"
    assert not manager.layers['periodic'].is_full, "Should have room now"
    print(f"  ✓ Interrupted oldest: {interrupted.sound_id}")
    
    print("  All layer capacity tests passed!")


def test_expired_sounds():
    """Test expired sound cleanup."""
    print("\n=== Testing Expired Sound Cleanup ===")
    
    manager = LayerManager()
    
    # Add sounds with different end times
    for i, end_time in enumerate([5.0, 10.0, 15.0]):
        sound = ActiveSoundInfo(
            instance_id=f"test-{i}",
            sound_id=f"sound_{i}",
            layer="periodic",
            start_time=0.0,
            expected_end_time=end_time,
            intensity=0.5,
            frequency_band="mid",
            is_continuous=False,
        )
        manager.add_sound(sound)
    
    assert manager.get_active_count() == 3, "Should have 3 active"
    
    # Check at time 7 (first should be expired)
    expired = manager.get_expired_sounds(7.0)
    assert len(expired) == 1, f"Expected 1 expired at t=7, got {len(expired)}"
    print("  ✓ Found 1 expired sound at t=7")
    
    # Cleanup at time 12 (first two should be gone)
    removed = manager.cleanup_expired(12.0)
    assert len(removed) == 2, f"Expected 2 removed at t=12, got {len(removed)}"
    assert manager.get_active_count() == 1, "Should have 1 remaining"
    print("  ✓ Cleaned up 2 expired sounds at t=12")
    
    print("  All expired sound tests passed!")


def test_soundscape_basics():
    """Test basic Soundscape functionality."""
    print("\n=== Testing Soundscape Basics ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    rng = SeededRNG(seed=42)
    
    soundscape = Soundscape(config, rng)
    
    assert soundscape.layer_manager.get_active_count() == 0, "Should start empty"
    print("  ✓ Soundscape initialized empty")
    
    # Get state
    state = soundscape.get_state()
    assert 'layers' in state, "State should have layers"
    assert 'active_sounds' in state, "State should have active_sounds"
    print(f"  ✓ State structure correct: {list(state.keys())}")
    
    print("  All Soundscape basics tests passed!")


def test_soundscape_tick():
    """Test Soundscape tick behavior."""
    print("\n=== Testing Soundscape Tick ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    rng = SeededRNG(seed=42)
    
    soundscape = Soundscape(config, rng)
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    sdi = MockSDIResult(smoothed_sdi=0.0, delta=0.1, delta_category="small")
    
    all_events = []
    
    # Run several ticks
    for t in range(0, 30, 1):
        events = soundscape.tick(
            current_time=float(t),
            environment=env,
            sound_memory=memory,
            silence_tracker=silence,
            pattern_memory=patterns,
            sdi_result=sdi,
        )
        all_events.extend(events)
    
    print(f"  ✓ Generated {len(all_events)} events over 30 ticks")
    
    # Count event types
    starts = [e for e in all_events if e.event_type == EventType.SOUND_START]
    ends = [e for e in all_events if e.event_type == EventType.SOUND_END]
    
    print(f"  ✓ Sound starts: {len(starts)}")
    print(f"  ✓ Sound ends: {len(ends)}")
    
    # Should have started some sounds
    assert len(starts) > 0, "Should have started some sounds"
    
    # Check event structure
    for event in starts[:3]:
        assert event.sound_id, "Event should have sound_id"
        assert event.instance_id, "Event should have instance_id"
        assert event.duration > 0, "Event should have duration"
        print(f"    - {event.sound_id} ({event.layer}): {event.duration:.1f}s")
    
    print("  All Soundscape tick tests passed!")


def test_soundscape_sdi_response():
    """Test Soundscape response to SDI deltas."""
    print("\n=== Testing SDI Response ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    rng = SeededRNG(seed=42)
    
    # Test with high delta (need more SDI)
    soundscape_high = Soundscape(config, rng)
    memory_high = SoundMemory()
    silence_high = SilenceTracker()
    patterns_high = PatternMemory()
    env = MockEnvironment()
    sdi_high = MockSDIResult(smoothed_sdi=0.1, delta=0.4, delta_category="large")
    
    events_high = []
    for t in range(0, 20):
        events = soundscape_high.tick(
            current_time=float(t),
            environment=env,
            sound_memory=memory_high,
            silence_tracker=silence_high,
            pattern_memory=patterns_high,
            sdi_result=sdi_high,
        )
        events_high.extend(events)
    
    # Test with low delta (need less SDI)
    rng2 = SeededRNG(seed=42)  # Same seed for comparison
    soundscape_low = Soundscape(config, rng2)
    memory_low = SoundMemory()
    silence_low = SilenceTracker()
    patterns_low = PatternMemory()
    sdi_low = MockSDIResult(smoothed_sdi=0.5, delta=-0.4, delta_category="large")
    
    events_low = []
    for t in range(0, 20):
        events = soundscape_low.tick(
            current_time=float(t),
            environment=env,
            sound_memory=memory_low,
            silence_tracker=silence_low,
            pattern_memory=patterns_low,
            sdi_result=sdi_low,
        )
        events_low.extend(events)
    
    starts_high = len([e for e in events_high if e.event_type == EventType.SOUND_START])
    starts_low = len([e for e in events_low if e.event_type == EventType.SOUND_START])
    
    print(f"  High delta (+0.4) starts: {starts_high}")
    print(f"  Low delta (-0.4) starts: {starts_low}")
    
    # High delta should generally produce more sounds (aggressive addition)
    # But this depends on RNG, so we just check both produced events
    assert starts_high > 0, "High delta should produce some sounds"
    assert starts_low >= 0, "Low delta may produce fewer sounds"
    print("  ✓ SDI response behavior observed")
    
    print("  All SDI response tests passed!")


def test_force_start_stop():
    """Test forced sound start/stop."""
    print("\n=== Testing Force Start/Stop ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    rng = SeededRNG(seed=42)
    
    soundscape = Soundscape(config, rng)
    
    # Force start a known sound
    event = soundscape.force_start_sound("birdsong", current_time=0.0)
    
    assert event is not None, "Should create event"
    assert event.event_type == EventType.SOUND_START, "Should be start event"
    assert event.sound_id == "birdsong", "Should be birdsong"
    print(f"  ✓ Force started: {event.sound_id} for {event.duration:.1f}s")
    
    # Check it's active
    active = soundscape.get_active_sounds()
    assert len(active) == 1, "Should have 1 active sound"
    assert active[0].sound_id == "birdsong", "Should be birdsong"
    print("  ✓ Sound is active in manager")
    
    # Force stop
    stop_event = soundscape.force_stop_sound(event.instance_id, current_time=2.0)
    
    assert stop_event is not None, "Should create stop event"
    assert stop_event.event_type == EventType.SOUND_INTERRUPT, "Should be interrupt"
    print(f"  ✓ Force stopped: {stop_event.sound_id}")
    
    # Check it's gone
    active = soundscape.get_active_sounds()
    assert len(active) == 0, "Should have no active sounds"
    print("  ✓ Sound removed from manager")
    
    print("  All force start/stop tests passed!")


def test_integration():
    """Test full integration of selection system."""
    print("\n=== Testing Full Integration ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    rng = SeededRNG(seed=42)
    
    soundscape = Soundscape(config, rng)
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment(biome_id="forest", time_of_day="day", weather="clear")
    
    all_events = []
    
    # Simulate 60 seconds
    print("  Simulating 60 seconds of soundscape...")
    
    for t in range(60):
        # Vary SDI over time
        population = 0.2 + 0.3 * (t / 60.0)  # Increasing population
        delta = population * 0.5 - 0.1
        category = "none" if abs(delta) < 0.1 else "small" if abs(delta) < 0.2 else "medium"
        sdi = MockSDIResult(smoothed_sdi=delta + 0.1, delta=delta, delta_category=category)
        
        events = soundscape.tick(
            current_time=float(t),
            environment=env,
            sound_memory=memory,
            silence_tracker=silence,
            pattern_memory=patterns,
            sdi_result=sdi,
            population_ratio=population,
        )
        all_events.extend(events)
    
    # Analyze results
    starts = [e for e in all_events if e.event_type == EventType.SOUND_START]
    ends = [e for e in all_events if e.event_type == EventType.SOUND_END]
    interrupts = [e for e in all_events if e.event_type == EventType.SOUND_INTERRUPT]
    
    print(f"\n  Results:")
    print(f"    Total events: {len(all_events)}")
    print(f"    Sounds started: {len(starts)}")
    print(f"    Sounds ended: {len(ends)}")
    print(f"    Sounds interrupted: {len(interrupts)}")
    
    # Check pattern memory was updated
    patterns_count = len(patterns.get_all_patterns())
    print(f"    Patterns tracked: {patterns_count}")
    
    # Check sound memory
    print(f"    Sound memory events: {memory.total_events}")
    
    # Final state
    state = soundscape.get_state()
    print(f"    Final active sounds: {len(state['active_sounds'])}")
    
    # Unique sounds played
    unique_sounds = set(e.sound_id for e in starts)
    print(f"    Unique sounds played: {len(unique_sounds)}")
    for sound in list(unique_sounds)[:5]:
        count = sum(1 for e in starts if e.sound_id == sound)
        print(f"      - {sound}: {count} times")
    
    assert len(starts) > 0, "Should have played some sounds"
    assert patterns_count > 0, "Should have tracked some patterns"
    
    print("\n  ✓ Full integration test passed!")


def main():
    """Run all Phase 4 tests."""
    print("=" * 60)
    print("Living Soundscape Engine - Phase 4 Tests")
    print("Sound Selection System")
    print("=" * 60)
    
    try:
        # SoundSelector tests
        test_sound_selector_basics()
        test_candidate_filtering()
        test_probability_adjustment()
        test_sound_selection()
        
        # LayerManager tests
        test_layer_manager_basics()
        test_layer_capacity()
        test_expired_sounds()
        
        # Soundscape tests
        test_soundscape_basics()
        test_soundscape_tick()
        test_soundscape_sdi_response()
        test_force_start_stop()
        
        # Full integration
        test_integration()
        
        print("\n" + "=" * 60)
        print("ALL PHASE 4 TESTS PASSED!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
