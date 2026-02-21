#!/usr/bin/env python3
"""
Phase 2 Test Script for Living Soundscape Engine

Tests the memory systems:
- SoundMemory: Event history and querying
- SilenceTracker: Silence gap tracking
- PatternMemory: Rhythm and pattern detection

Run from the lse directory:
    python tests/test_phase2.py
"""

import sys
import os
import uuid

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, src_path)

from memory import (
    SoundMemory, SoundEvent,
    SilenceTracker, SilenceGap,
    PatternMemory, PatternState, PatternType,
)
from memory.sound_memory import EndType


def make_event(sound_id: str, timestamp: float, layer: str = "periodic",
               duration: float = 2.0, intensity: float = 0.5,
               frequency_band: str = "mid", tags: list = None) -> SoundEvent:
    """Helper to create sound events for testing."""
    return SoundEvent(
        instance_id=str(uuid.uuid4()),
        sound_id=sound_id,
        timestamp=timestamp,
        layer=layer,
        intensity=intensity,
        frequency_band=frequency_band,
        duration=duration,
        tags=tags or [],
    )


def test_sound_memory_basics():
    """Test basic SoundMemory operations."""
    print("\n=== Testing SoundMemory Basics ===")
    
    memory = SoundMemory(retention_window=60.0)
    
    # Test initial state
    assert memory.active_count == 0, "Should start empty"
    assert memory.total_events == 0, "Should have no events"
    print("  ✓ Initial state")
    
    # Add an event
    event = make_event("birdsong", 10.0, tags=["organic", "animal"])
    memory.add_event(event)
    
    assert memory.active_count == 1, "Should have 1 active"
    assert memory.total_events == 1, "Should have 1 total"
    assert memory.has_active_sound("birdsong"), "birdsong should be active"
    print("  ✓ Add event")
    
    # Test layer counts
    counts = memory.layer_counts
    assert counts['periodic'] == 1, f"Expected 1 periodic, got {counts}"
    print("  ✓ Layer counts")
    
    # Test frequency counts
    freq_counts = memory.frequency_counts
    assert freq_counts['mid'] == 1, f"Expected 1 mid, got {freq_counts}"
    print("  ✓ Frequency counts")
    
    # End the event
    ended = memory.end_event(event.instance_id, 12.0, EndType.NATURAL)
    assert ended is not None, "Should return ended event"
    assert ended.ended == True, "Event should be marked ended"
    assert ended.end_type == EndType.NATURAL, "Should be natural end"
    assert memory.active_count == 0, "Should have 0 active"
    print("  ✓ End event")
    
    # Counts should be updated
    counts = memory.layer_counts
    assert counts['periodic'] == 0, "Layer count should decrease"
    print("  ✓ Layer count update after end")
    
    print("  All SoundMemory basics tests passed!")


def test_sound_memory_queries():
    """Test SoundMemory query methods."""
    print("\n=== Testing SoundMemory Queries ===")
    
    memory = SoundMemory()
    
    # Add multiple events
    memory.add_event(make_event("birdsong", 0.0, layer="periodic", tags=["animal"]))
    memory.add_event(make_event("wind", 1.0, layer="background", tags=["weather"]))
    memory.add_event(make_event("birdsong", 5.0, layer="periodic", tags=["animal"]))
    memory.add_event(make_event("footsteps", 7.0, layer="reactive", tags=["movement"]))
    
    # Query by layer
    periodic = memory.get_active_by_layer("periodic")
    assert len(periodic) == 2, f"Expected 2 periodic, got {len(periodic)}"
    print("  ✓ Query by layer")
    
    # Query by sound ID
    birds = memory.get_active_by_sound_id("birdsong")
    assert len(birds) == 2, f"Expected 2 birdsong, got {len(birds)}"
    print("  ✓ Query by sound ID")
    
    # Query by tag
    animals = memory.get_active_by_tag("animal")
    assert len(animals) == 2, f"Expected 2 with 'animal' tag, got {len(animals)}"
    print("  ✓ Query by tag")
    
    # Get active IDs
    ids = memory.get_active_ids()
    assert ids == {"birdsong", "wind", "footsteps"}, f"Got {ids}"
    print("  ✓ Get active IDs")
    
    # Get active tags
    tags = memory.get_active_tags()
    assert "animal" in tags and "weather" in tags, f"Got {tags}"
    print("  ✓ Get active tags")
    
    # Recent events
    recent = memory.get_recent_events(2)
    assert len(recent) == 2, f"Expected 2 recent, got {len(recent)}"
    assert recent[-1].sound_id == "footsteps", "Most recent should be footsteps"
    print("  ✓ Recent events")
    
    # Occurrence timestamps
    timestamps = memory.get_occurrence_timestamps("birdsong")
    assert timestamps == [0.0, 5.0], f"Expected [0.0, 5.0], got {timestamps}"
    print("  ✓ Occurrence timestamps")
    
    print("  All SoundMemory query tests passed!")


def test_sound_memory_cooldowns():
    """Test SoundMemory cooldown functionality."""
    print("\n=== Testing SoundMemory Cooldowns ===")
    
    memory = SoundMemory()
    
    # Set a cooldown
    memory.set_cooldown("birdsong", until=15.0)
    
    # Check at different times
    assert memory.is_on_cooldown("birdsong", 10.0) == True, "Should be on cooldown"
    assert memory.is_on_cooldown("birdsong", 16.0) == False, "Should be off cooldown"
    assert memory.is_on_cooldown("wind", 10.0) == False, "wind has no cooldown"
    print("  ✓ Cooldown checking")
    
    # Cooldown remaining
    remaining = memory.get_cooldown_remaining("birdsong", 10.0)
    assert remaining == 5.0, f"Expected 5.0 remaining, got {remaining}"
    print("  ✓ Cooldown remaining")
    
    print("  All SoundMemory cooldown tests passed!")


def test_sound_memory_pairs():
    """Test SoundMemory pair detection for harmony/conflict."""
    print("\n=== Testing SoundMemory Pairs ===")
    
    memory = SoundMemory()
    
    # Add sounds with different tags
    memory.add_event(make_event("birdsong", 0.0, tags=["animal", "day"]))
    memory.add_event(make_event("wind", 1.0, tags=["weather"]))
    memory.add_event(make_event("seabirds", 2.0, tags=["animal", "coastal"]))
    
    # Check if pair is active
    assert memory.check_sound_pair_active("birdsong", "wind") == True
    assert memory.check_sound_pair_active("birdsong", "thunder") == False
    print("  ✓ Sound pair check")
    
    # Get pairs by tag
    animal_pairs = memory.get_active_with_tag_pair("animal", "weather")
    assert len(animal_pairs) == 2, f"Expected 2 pairs, got {len(animal_pairs)}"
    print("  ✓ Tag pair detection")
    
    print("  All SoundMemory pair tests passed!")


def test_silence_tracker_basics():
    """Test basic SilenceTracker operations."""
    print("\n=== Testing SilenceTracker Basics ===")
    
    tracker = SilenceTracker()
    
    # Start in silence
    assert tracker.in_silence == True, "Should start in silence"
    print("  ✓ Initial state")
    
    # Sound starts - silence ends
    gap = tracker.update(timestamp=5.0, sound_count=1)
    assert tracker.in_silence == False, "Should not be in silence"
    # Gap might be None if < MIN_GAP_DURATION
    print("  ✓ Silence ends when sound starts")
    
    # Sound stops - silence begins
    gap = tracker.update(timestamp=10.0, sound_count=0)
    assert tracker.in_silence == True, "Should be in silence"
    print("  ✓ Silence begins when sound stops")
    
    # Another sound starts after some time
    gap = tracker.update(timestamp=15.0, sound_count=1)
    assert gap is not None, "Should have completed a gap"
    assert gap.duration == 5.0, f"Gap duration should be 5.0, got {gap.duration}"
    print("  ✓ Gap recording")
    
    print("  All SilenceTracker basics tests passed!")


def test_silence_tracker_deprivation():
    """Test silence deprivation detection."""
    print("\n=== Testing SilenceTracker Deprivation ===")
    
    tracker = SilenceTracker()
    
    # End silence at time 5
    tracker.update(5.0, sound_count=1)
    
    # Check time since silence
    time_since = tracker.time_since_silence(10.0)
    assert time_since == 5.0, f"Expected 5.0, got {time_since}"
    print("  ✓ Time since silence")
    
    # Check deprivation with different tolerances
    assert tracker.is_deprived(10.0, tolerance=4.0) == True, "Should be deprived"
    assert tracker.is_deprived(10.0, tolerance=6.0) == False, "Should not be deprived"
    print("  ✓ Deprivation detection")
    
    # Deprivation factor
    factor = tracker.get_deprivation_factor(15.0, tolerance=5.0)
    # time_since = 10, tolerance = 5, excess = 5
    # factor = 5/5 = 1.0
    assert factor == 1.0, f"Expected 1.0, got {factor}"
    print("  ✓ Deprivation factor")
    
    # When in silence, no deprivation
    tracker.update(20.0, sound_count=0)  # Start silence
    assert tracker.time_since_silence(25.0) == 0.0, "In silence, time_since should be 0"
    print("  ✓ No deprivation during silence")
    
    print("  All SilenceTracker deprivation tests passed!")


def test_silence_tracker_appropriate_gaps():
    """Test appropriate silence gap detection."""
    print("\n=== Testing SilenceTracker Appropriate Gaps ===")
    
    tracker = SilenceTracker()
    
    # Create some gaps
    # Silence from 0-5 (duration 5), sound from 5-10, silence from 10-15
    tracker.update(5.0, sound_count=1)  # End first silence
    tracker.update(10.0, sound_count=0)  # Start second silence
    gap = tracker.update(15.0, sound_count=1)  # End second silence
    
    assert gap is not None, "Should have a gap"
    
    # Check if gap is appropriate for tolerance=5
    # Appropriate is 50%-150% of tolerance, so 2.5-7.5 seconds
    # Our gap is 5.0, which is appropriate
    is_appropriate = tracker.was_gap_appropriate(gap, tolerance=5.0)
    assert is_appropriate == True, f"Gap of 5.0 should be appropriate for tolerance 5.0"
    print("  ✓ Appropriate gap detection")
    
    # Mark it and check stats
    tracker.mark_gap_appropriate(gap, tolerance=5.0)
    assert gap.was_appropriate == True
    print("  ✓ Gap marking")
    
    print("  All SilenceTracker appropriate gap tests passed!")


def test_pattern_memory_basics():
    """Test basic PatternMemory operations."""
    print("\n=== Testing PatternMemory Basics ===")
    
    memory = PatternMemory()
    
    # Record some occurrences (not enough for pattern)
    memory.record_occurrence("birdsong", 0.0)
    memory.record_occurrence("birdsong", 5.0)
    
    pattern = memory.get_pattern("birdsong")
    assert pattern is not None, "Should have pattern"
    assert pattern.pattern_type == PatternType.NONE, "Not enough data yet"
    print("  ✓ Initial pattern state (insufficient data)")
    
    # Add more to establish pattern
    memory.record_occurrence("birdsong", 10.0)
    memory.record_occurrence("birdsong", 15.0)
    
    pattern = memory.get_pattern("birdsong")
    assert pattern.pattern_type == PatternType.RHYTHMIC, f"Should be rhythmic, got {pattern.pattern_type}"
    assert pattern.avg_interval == 5.0, f"Expected avg 5.0, got {pattern.avg_interval}"
    print("  ✓ Rhythmic pattern detection")
    
    # Check expected next
    assert pattern.expected_next == 20.0, f"Expected 20.0, got {pattern.expected_next}"
    print("  ✓ Next occurrence prediction")
    
    print("  All PatternMemory basics tests passed!")


def test_pattern_memory_drift():
    """Test drifting pattern detection."""
    print("\n=== Testing PatternMemory Drift ===")
    
    memory = PatternMemory()
    
    # Create a drifting pattern (intervals: 5.0, 5.5, 4.5, 6.0)
    # CV should be between 0.15 and 0.40
    memory.record_occurrence("creaks", 0.0)
    memory.record_occurrence("creaks", 5.0)   # interval 5.0
    memory.record_occurrence("creaks", 10.5)  # interval 5.5
    memory.record_occurrence("creaks", 15.0)  # interval 4.5
    memory.record_occurrence("creaks", 21.0)  # interval 6.0
    
    pattern = memory.get_pattern("creaks")
    
    # Check CV is in drift range
    assert 0.10 < pattern.cv < 0.40, f"CV {pattern.cv} not in drift range"
    
    # Should be classified as drifting
    assert pattern.pattern_type == PatternType.DRIFTING, f"Expected DRIFTING, got {pattern.pattern_type}"
    print("  ✓ Drifting pattern detection")
    
    # Check drift amount
    drift = pattern.get_drift_amount()
    assert drift > 0, f"Should have positive drift, got {drift}"
    print("  ✓ Drift amount calculation")
    
    print("  All PatternMemory drift tests passed!")


def test_pattern_memory_breaks():
    """Test broken pattern detection."""
    print("\n=== Testing PatternMemory Breaks ===")
    
    memory = PatternMemory()
    
    # Create a rhythmic pattern
    memory.record_occurrence("drips", 0.0)
    memory.record_occurrence("drips", 2.0)
    memory.record_occurrence("drips", 4.0)
    memory.record_occurrence("drips", 6.0)
    
    pattern = memory.get_pattern("drips")
    assert pattern.pattern_type == PatternType.RHYTHMIC, "Should be rhythmic"
    assert pattern.expected_next == 8.0, "Should expect next at 8.0"
    print("  ✓ Established rhythmic pattern")
    
    # Check for break at time 8 (not broken yet)
    broken = pattern.check_break(8.0)
    assert broken == False, "Not broken yet at expected time"
    
    # Check at 2x expected interval (threshold is 2.0)
    # expected at 8.0, avg_interval is 2.0
    # break threshold = 8.0 + (2.0 * 2.0) = 12.0
    broken = pattern.check_break(13.0)
    assert broken == True, "Should be broken now"
    assert pattern.pattern_type == PatternType.BROKEN, "Type should be BROKEN"
    assert pattern.is_broken == True, "is_broken flag should be set"
    print("  ✓ Pattern break detection")
    
    # Get break duration
    duration = pattern.get_break_duration(15.0)
    assert duration == 2.0, f"Expected 2.0 break duration, got {duration}"
    print("  ✓ Break duration calculation")
    
    # Adding occurrence should resolve break
    memory.record_occurrence("drips", 16.0)
    pattern = memory.get_pattern("drips")
    assert pattern.is_broken == False, "Break should be resolved"
    print("  ✓ Break resolution")
    
    print("  All PatternMemory break tests passed!")


def test_pattern_memory_sdi_queries():
    """Test SDI-related queries on PatternMemory."""
    print("\n=== Testing PatternMemory SDI Queries ===")
    
    memory = PatternMemory()
    
    # Create different pattern types
    # Rhythmic
    for i in range(5):
        memory.record_occurrence("waves", i * 5.0)
    
    # Drifting
    timestamps = [0.0, 5.0, 10.5, 15.0, 21.0]
    for t in timestamps:
        memory.record_occurrence("creaks", t)
    
    # Verify classifications
    rhythmic_count = memory.count_rhythmic()
    drifting_count = memory.count_drifting()
    
    assert rhythmic_count >= 1, f"Should have at least 1 rhythmic, got {rhythmic_count}"
    print("  ✓ Count rhythmic patterns")
    
    # Get stability score
    score = memory.get_rhythm_stability_score()
    # Should be positive (has rhythmic, maybe some drift)
    print(f"  ✓ Stability score: {score:.2f}")
    
    # Get summary
    summary = memory.get_summary()
    assert 'rhythmic' in summary, "Summary should include rhythmic"
    assert 'drifting' in summary, "Summary should include drifting"
    print(f"  ✓ Pattern summary: {summary}")
    
    print("  All PatternMemory SDI query tests passed!")


def test_integration():
    """Test that memory systems work together."""
    print("\n=== Testing Memory Integration ===")
    
    # Create all memory systems
    sound_memory = SoundMemory()
    silence_tracker = SilenceTracker()
    pattern_memory = PatternMemory()
    
    # Simulate a sequence of events
    current_time = 0.0
    
    def tick(duration: float = 1.0):
        nonlocal current_time
        current_time += duration
        return current_time
    
    # Add first sound
    event1 = make_event("birdsong", tick(), layer="periodic")
    sound_memory.add_event(event1)
    silence_tracker.update(current_time, sound_count=1)
    pattern_memory.record_occurrence("birdsong", current_time)
    
    # Some time passes
    tick(5.0)
    
    # End first sound
    sound_memory.end_event(event1.instance_id, current_time)
    silence_tracker.update(current_time, sound_count=0)
    
    # Silence period
    tick(3.0)
    
    # Second birdsong
    event2 = make_event("birdsong", current_time, layer="periodic")
    sound_memory.add_event(event2)
    silence_tracker.update(current_time, sound_count=1)
    pattern_memory.record_occurrence("birdsong", current_time)
    
    # Check all systems are tracking correctly
    assert sound_memory.active_count == 1, "Should have 1 active sound"
    assert len(silence_tracker._gaps) >= 1, "Should have recorded a gap"
    
    pattern = pattern_memory.get_pattern("birdsong")
    assert len(pattern.occurrences) == 2, "Should have 2 occurrences"
    print("  ✓ Multi-system event tracking")
    
    # Add more birdsongs to establish pattern
    tick(3.0)
    sound_memory.end_event(event2.instance_id, current_time)
    
    tick(3.0)
    event3 = make_event("birdsong", current_time)
    sound_memory.add_event(event3)
    pattern_memory.record_occurrence("birdsong", current_time)
    
    tick(3.0)
    sound_memory.end_event(event3.instance_id, current_time)
    
    tick(3.0)
    event4 = make_event("birdsong", current_time)
    sound_memory.add_event(event4)
    pattern_memory.record_occurrence("birdsong", current_time)
    
    # Check pattern is forming
    pattern = pattern_memory.get_pattern("birdsong")
    assert len(pattern.intervals) >= 2, "Should have intervals"
    print(f"  ✓ Pattern forming: {pattern.pattern_type.value}")
    
    # Check time since silence
    time_since = silence_tracker.time_since_silence(current_time)
    print(f"  ✓ Time since silence: {time_since:.1f}s")
    
    # Get overall state
    print(f"  ✓ Total events: {sound_memory.total_events}")
    print(f"  ✓ Total gaps: {silence_tracker.total_gaps}")
    print(f"  ✓ Pattern summary: {pattern_memory.get_summary()}")
    
    print("  All memory integration tests passed!")


def main():
    """Run all Phase 2 tests."""
    print("=" * 60)
    print("Living Soundscape Engine - Phase 2 Tests")
    print("Memory Systems")
    print("=" * 60)
    
    try:
        # SoundMemory tests
        test_sound_memory_basics()
        test_sound_memory_queries()
        test_sound_memory_cooldowns()
        test_sound_memory_pairs()
        
        # SilenceTracker tests
        test_silence_tracker_basics()
        test_silence_tracker_deprivation()
        test_silence_tracker_appropriate_gaps()
        
        # PatternMemory tests
        test_pattern_memory_basics()
        test_pattern_memory_drift()
        test_pattern_memory_breaks()
        test_pattern_memory_sdi_queries()
        
        # Integration test
        test_integration()
        
        print("\n" + "=" * 60)
        print("ALL PHASE 2 TESTS PASSED!")
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
