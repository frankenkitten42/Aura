#!/usr/bin/env python3
"""
Phase 3 Test Script for Living Soundscape Engine

Tests the SDI calculation system:
- DiscomfortCalculator: Positive SDI factors
- ComfortCalculator: Negative SDI factors
- SDICalculator: Combined calculation with smoothing

Run from the lse directory:
    python tests/test_phase3.py
"""

import sys
import os
import uuid

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, src_path)

from memory import SoundMemory, SoundEvent, SilenceTracker, PatternMemory
from memory.sound_memory import EndType
from sdi import DiscomfortCalculator, ComfortCalculator, SDICalculator, SDIResult
from sdi.factors import DiscomfortResult
from sdi.comfort import ComfortResult
from config import load_config


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


class MockEnvironment:
    """Mock environment for testing."""
    def __init__(self, biome_id="forest", time_of_day="day", weather="clear"):
        self.biome_id = biome_id
        self.time_of_day = time_of_day
        self.weather = weather
        self.biome_parameters = MockBiomeParams()


class MockBiomeParams:
    """Mock biome parameters."""
    def __init__(self):
        self.layer_capacity = 4
        self.silence_tolerance = 5.0
        self.sdi_baseline = 0.0


def test_discomfort_basics():
    """Test basic DiscomfortCalculator functionality."""
    print("\n=== Testing DiscomfortCalculator Basics ===")
    
    calc = DiscomfortCalculator()
    
    # Empty state should produce zero discomfort
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    
    result = calc.calculate(memory, silence, patterns, env, current_time=0.0)
    
    assert isinstance(result, DiscomfortResult), "Should return DiscomfortResult"
    assert result.total == 0.0, f"Empty state should have 0 discomfort, got {result.total}"
    print("  ✓ Empty state produces zero discomfort")
    
    print("  All DiscomfortCalculator basics tests passed!")


def test_density_overload():
    """Test density overload factor calculation."""
    print("\n=== Testing Density Overload Factor ===")
    
    calc = DiscomfortCalculator()
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    env.biome_parameters.layer_capacity = 3
    
    # Add sounds up to capacity (no overload)
    for i in range(3):
        memory.add_event(make_event(f"sound_{i}", 0.0))
    
    result = calc.calculate(memory, silence, patterns, env, current_time=1.0)
    assert result.density_overload == 0.0, f"At capacity should be 0, got {result.density_overload}"
    print("  ✓ No overload at capacity")
    
    # Add one more (1 excess)
    memory.add_event(make_event("sound_extra", 0.0))
    
    result = calc.calculate(memory, silence, patterns, env, current_time=1.0)
    expected = 0.15  # 1 excess * 0.15 weight
    assert abs(result.density_overload - expected) < 0.01, \
        f"1 excess should be ~{expected}, got {result.density_overload}"
    print("  ✓ Overload detected with excess sounds")
    
    # Add two more (3 excess total)
    memory.add_event(make_event("sound_extra2", 0.0))
    memory.add_event(make_event("sound_extra3", 0.0))
    
    result = calc.calculate(memory, silence, patterns, env, current_time=1.0)
    expected = 0.45  # 3 excess * 0.15 (capped at 0.45)
    assert abs(result.density_overload - expected) < 0.01, \
        f"3 excess should be ~{expected}, got {result.density_overload}"
    print("  ✓ Density overload scales with excess")
    
    print("  All density overload tests passed!")


def test_silence_deprivation():
    """Test silence deprivation factor calculation."""
    print("\n=== Testing Silence Deprivation Factor ===")
    
    calc = DiscomfortCalculator()
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    env.biome_parameters.silence_tolerance = 5.0
    
    # Start with sound (end silence)
    silence.update(0.0, sound_count=1)
    
    # Within tolerance
    result = calc.calculate(memory, silence, patterns, env, current_time=4.0)
    assert result.silence_deprivation == 0.0, \
        f"Within tolerance should be 0, got {result.silence_deprivation}"
    print("  ✓ No deprivation within tolerance")
    
    # Just past tolerance (1x)
    result = calc.calculate(memory, silence, patterns, env, current_time=10.0)
    # time_since = 10, tolerance = 5, deprivation_factor = (10-5)/5 = 1.0
    # expected = 0.08 * 1.0 = 0.08
    assert result.silence_deprivation > 0, \
        f"Past tolerance should be > 0, got {result.silence_deprivation}"
    print(f"  ✓ Deprivation detected: {result.silence_deprivation:.3f}")
    
    # Much past tolerance (2x)
    result = calc.calculate(memory, silence, patterns, env, current_time=15.0)
    # time_since = 15, tolerance = 5, deprivation_factor = (15-5)/5 = 2.0
    # expected = 0.08 * 2.0 = 0.16
    assert result.silence_deprivation > 0.08, \
        f"2x tolerance should be higher, got {result.silence_deprivation}"
    print(f"  ✓ Deprivation increases with time: {result.silence_deprivation:.3f}")
    
    # Start silence (should reset)
    silence.update(16.0, sound_count=0)
    result = calc.calculate(memory, silence, patterns, env, current_time=17.0)
    assert result.silence_deprivation == 0.0, \
        f"During silence should be 0, got {result.silence_deprivation}"
    print("  ✓ Deprivation clears during silence")
    
    print("  All silence deprivation tests passed!")


def test_rhythm_instability():
    """Test rhythm instability factor calculation."""
    print("\n=== Testing Rhythm Instability Factor ===")
    
    calc = DiscomfortCalculator()
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    
    # Create a drifting pattern (CV between 0.15 and 0.40)
    patterns.record_occurrence("creaks", 0.0)
    patterns.record_occurrence("creaks", 5.0)   # interval 5.0
    patterns.record_occurrence("creaks", 10.5)  # interval 5.5
    patterns.record_occurrence("creaks", 15.0)  # interval 4.5
    patterns.record_occurrence("creaks", 21.0)  # interval 6.0
    
    result = calc.calculate(memory, silence, patterns, env, current_time=22.0)
    assert result.rhythm_instability > 0, \
        f"Drifting pattern should cause instability, got {result.rhythm_instability}"
    print(f"  ✓ Drift detected: {result.rhythm_instability:.3f}")
    
    # Add a stable pattern (shouldn't add to instability)
    patterns2 = PatternMemory()
    for i in range(5):
        patterns2.record_occurrence("waves", i * 5.0)
    
    result2 = calc.calculate(memory, silence, patterns2, env, current_time=22.0)
    assert result2.rhythm_instability == 0.0, \
        f"Stable pattern should be 0, got {result2.rhythm_instability}"
    print("  ✓ Stable patterns don't cause instability")
    
    print("  All rhythm instability tests passed!")


def test_comfort_basics():
    """Test basic ComfortCalculator functionality."""
    print("\n=== Testing ComfortCalculator Basics ===")
    
    calc = ComfortCalculator()
    
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    
    result = calc.calculate(memory, silence, patterns, env, current_time=0.0)
    
    assert isinstance(result, ComfortResult), "Should return ComfortResult"
    # Environmental coherence should be active even with no sounds
    assert result.environmental_coherence <= 0, \
        f"Environmental coherence should be <= 0, got {result.environmental_coherence}"
    print("  ✓ Comfort result has correct structure")
    
    print("  All ComfortCalculator basics tests passed!")


def test_predictable_rhythm():
    """Test predictable rhythm comfort factor."""
    print("\n=== Testing Predictable Rhythm Factor ===")
    
    calc = ComfortCalculator()
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    
    # No patterns
    result = calc.calculate(memory, silence, patterns, env, current_time=0.0)
    assert result.predictable_rhythm == 0.0, \
        f"No patterns should be 0, got {result.predictable_rhythm}"
    print("  ✓ No rhythm with no patterns")
    
    # Add stable rhythmic pattern
    for i in range(5):
        patterns.record_occurrence("waves", i * 5.0)
    
    result = calc.calculate(memory, silence, patterns, env, current_time=25.0)
    assert result.predictable_rhythm < 0, \
        f"Stable pattern should be negative, got {result.predictable_rhythm}"
    print(f"  ✓ Stable rhythm comfort: {result.predictable_rhythm:.3f}")
    
    print("  All predictable rhythm tests passed!")


def test_appropriate_silence():
    """Test appropriate silence comfort factor."""
    print("\n=== Testing Appropriate Silence Factor ===")
    
    calc = ComfortCalculator()
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    env.biome_parameters.silence_tolerance = 5.0
    
    # Create an appropriate gap (50-150% of tolerance = 2.5-7.5s)
    silence.update(0.0, sound_count=1)   # End initial silence
    silence.update(5.0, sound_count=0)   # Start silence
    gap = silence.update(9.0, sound_count=1)   # End silence (4s gap)
    
    # Mark as appropriate
    if gap:
        silence.mark_gap_appropriate(gap, tolerance=5.0)
    
    result = calc.calculate(memory, silence, patterns, env, current_time=10.0)
    assert result.appropriate_silence < 0, \
        f"Appropriate gap should give comfort, got {result.appropriate_silence}"
    print(f"  ✓ Appropriate silence comfort: {result.appropriate_silence:.3f}")
    
    print("  All appropriate silence tests passed!")


def test_layer_harmony():
    """Test layer harmony comfort factor."""
    print("\n=== Testing Layer Harmony Factor ===")
    
    # Load config to get harmony pairs
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    
    calc = ComfortCalculator(config)
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    
    # Add sounds that are a known harmony pair
    # From our config: birdsong + wind_through_leaves is strong harmony
    memory.add_event(make_event("birdsong", 0.0, tags=["animal", "organic"]))
    memory.add_event(make_event("wind_through_leaves", 0.0, tags=["weather", "foliage"]))
    
    result = calc.calculate(memory, silence, patterns, env, current_time=1.0)
    assert result.layer_harmony < 0, \
        f"Harmony pair should give comfort, got {result.layer_harmony}"
    print(f"  ✓ Layer harmony comfort: {result.layer_harmony:.3f}")
    
    print("  All layer harmony tests passed!")


def test_environmental_coherence():
    """Test environmental coherence comfort factor."""
    print("\n=== Testing Environmental Coherence Factor ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    
    calc = ComfortCalculator(config)
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment(biome_id="forest")
    
    # Add sounds from forest biome
    memory.add_event(make_event("birdsong", 0.0))
    memory.add_event(make_event("wind_through_leaves", 0.0))
    
    result = calc.calculate(memory, silence, patterns, env, current_time=1.0)
    assert result.environmental_coherence < 0, \
        f"Coherent sounds should give comfort, got {result.environmental_coherence}"
    print(f"  ✓ Environmental coherence: {result.environmental_coherence:.3f}")
    
    # Add a sound not in forest biome (e.g., blizzard_wind is snow-only)
    memory.add_event(make_event("blizzard_wind", 0.0, tags=["weather"]))
    
    result2 = calc.calculate(memory, silence, patterns, env, current_time=1.0)
    # Coherence should be 0 or less negative now
    assert result2.environmental_coherence >= result.environmental_coherence, \
        f"Incoherent sound should reduce comfort"
    print(f"  ✓ Incoherence detected: {result2.environmental_coherence:.3f}")
    
    print("  All environmental coherence tests passed!")


def test_sdi_calculator_basics():
    """Test basic SDICalculator functionality."""
    print("\n=== Testing SDICalculator Basics ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    
    calc = SDICalculator(config)
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    
    result = calc.calculate(
        memory, silence, patterns, env,
        current_time=0.0,
        population_ratio=0.0
    )
    
    assert isinstance(result, SDIResult), "Should return SDIResult"
    assert -1.0 <= result.raw_sdi <= 1.0, f"SDI should be in range, got {result.raw_sdi}"
    assert -1.0 <= result.smoothed_sdi <= 1.0, "Smoothed should be in range"
    print("  ✓ SDI result in valid range")
    
    # Check structure
    assert hasattr(result, 'discomfort'), "Should have discomfort breakdown"
    assert hasattr(result, 'comfort'), "Should have comfort breakdown"
    assert hasattr(result, 'target_sdi'), "Should have target SDI"
    assert hasattr(result, 'delta'), "Should have delta"
    print("  ✓ SDI result has all components")
    
    print("  All SDICalculator basics tests passed!")


def test_population_to_target():
    """Test population to target SDI mapping."""
    print("\n=== Testing Population to Target SDI ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    
    calc = SDICalculator(config)
    
    # Test population points from config
    # (0.0, -0.30), (0.2, 0.00), (0.5, 0.20), (0.8, 0.50), (1.0, 0.80)
    
    target_0 = calc.get_population_target(0.0)
    assert abs(target_0 - (-0.30)) < 0.01, f"Pop 0.0 -> -0.30, got {target_0}"
    print(f"  ✓ Population 0.0 -> target {target_0:.2f}")
    
    target_50 = calc.get_population_target(0.5)
    assert abs(target_50 - 0.20) < 0.01, f"Pop 0.5 -> 0.20, got {target_50}"
    print(f"  ✓ Population 0.5 -> target {target_50:.2f}")
    
    target_100 = calc.get_population_target(1.0)
    assert abs(target_100 - 0.80) < 0.01, f"Pop 1.0 -> 0.80, got {target_100}"
    print(f"  ✓ Population 1.0 -> target {target_100:.2f}")
    
    # Test interpolation
    target_35 = calc.get_population_target(0.35)
    # Should be between 0.00 and 0.20
    assert 0.0 <= target_35 <= 0.20, f"Pop 0.35 should interpolate, got {target_35}"
    print(f"  ✓ Population 0.35 -> target {target_35:.2f} (interpolated)")
    
    print("  All population-to-target tests passed!")


def test_smoothing():
    """Test SDI smoothing behavior."""
    print("\n=== Testing SDI Smoothing ===")
    
    calc = SDICalculator()
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    
    # First calculation
    result1 = calc.calculate(memory, silence, patterns, env, current_time=0.0)
    sdi1 = result1.smoothed_sdi
    
    # Add many sounds to spike SDI
    for i in range(10):
        memory.add_event(make_event(f"sound_{i}", 1.0))
    
    result2 = calc.calculate(memory, silence, patterns, env, current_time=1.0)
    sdi2 = result2.smoothed_sdi
    
    # Smoothed should move toward raw, but not jump
    assert sdi2 != result2.raw_sdi, "Smoothed should differ from raw"
    assert abs(sdi2 - sdi1) < abs(result2.raw_sdi - sdi1), \
        "Smoothed change should be less than raw change"
    print(f"  ✓ Smoothing prevents jumps: raw={result2.raw_sdi:.3f}, smoothed={sdi2:.3f}")
    
    # Multiple ticks should converge
    for i in range(10):
        result = calc.calculate(memory, silence, patterns, env, current_time=2.0 + i)
    
    # Should be closer to raw now
    assert abs(result.smoothed_sdi - result.raw_sdi) < abs(sdi2 - result2.raw_sdi), \
        "Should converge toward raw over time"
    print(f"  ✓ Smoothing converges: {result.smoothed_sdi:.3f} -> {result.raw_sdi:.3f}")
    
    print("  All smoothing tests passed!")


def test_delta_categorization():
    """Test SDI delta categorization."""
    print("\n=== Testing Delta Categorization ===")
    
    calc = SDICalculator()
    
    # Test threshold boundaries
    thresholds = calc.get_delta_thresholds()
    print(f"  Thresholds: {thresholds}")
    
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    
    # Low population = low target, empty soundscape = low SDI -> small delta
    result = calc.calculate(
        memory, silence, patterns, env,
        current_time=0.0,
        population_ratio=0.0
    )
    
    print(f"  Delta: {result.delta:.3f}, Category: {result.delta_category}")
    
    # High population should create larger delta
    result2 = calc.calculate(
        memory, silence, patterns, env,
        current_time=1.0,
        population_ratio=0.9
    )
    
    print(f"  High pop delta: {result2.delta:.3f}, Category: {result2.delta_category}")
    assert result2.delta > result.delta, "Higher population should increase delta"
    print("  ✓ Delta increases with population gap")
    
    print("  All delta categorization tests passed!")


def test_top_contributors():
    """Test finding top positive and negative contributors."""
    print("\n=== Testing Top Contributors ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    
    calc = SDICalculator(config)
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment()
    env.biome_parameters.layer_capacity = 2
    
    # Add excess sounds for density overload
    for i in range(5):
        memory.add_event(make_event(f"sound_{i}", 0.0))
    
    # End silence for deprivation
    silence.update(0.0, sound_count=1)
    
    result = calc.calculate(
        memory, silence, patterns, env,
        current_time=20.0,  # Long time for silence deprivation
        population_ratio=0.5
    )
    
    print(f"  Top positive: {result.top_positive}")
    print(f"  Top negative: {result.top_negative}")
    
    assert result.top_positive[0] != "none", "Should have a positive contributor"
    assert result.top_positive[1] > 0, "Positive contributor should be > 0"
    print("  ✓ Top contributors identified")
    
    print("  All top contributor tests passed!")


def test_full_integration():
    """Test complete SDI calculation with all systems."""
    print("\n=== Testing Full SDI Integration ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    config = load_config(config_dir)
    
    calc = SDICalculator(config)
    memory = SoundMemory()
    silence = SilenceTracker()
    patterns = PatternMemory()
    env = MockEnvironment(biome_id="forest", time_of_day="day", weather="clear")
    
    # Simulate a sequence of events
    current_time = 0.0
    results = []
    
    def tick(duration: float = 1.0) -> SDIResult:
        nonlocal current_time
        current_time += duration
        return calc.calculate(
            memory, silence, patterns, env,
            current_time=current_time,
            population_ratio=0.3  # Moderate population
        )
    
    # Initial state
    result = tick()
    results.append(result)
    print(f"  t={current_time:.0f}: SDI={result.smoothed_sdi:.3f}")
    
    # Add some sounds
    memory.add_event(make_event("birdsong", current_time))
    silence.update(current_time, sound_count=1)
    patterns.record_occurrence("birdsong", current_time)
    
    result = tick(5.0)
    results.append(result)
    print(f"  t={current_time:.0f}: SDI={result.smoothed_sdi:.3f} (birdsong started)")
    
    # Add harmonious sound
    memory.add_event(make_event("wind_through_leaves", current_time))
    patterns.record_occurrence("wind_through_leaves", current_time)
    
    result = tick(5.0)
    results.append(result)
    print(f"  t={current_time:.0f}: SDI={result.smoothed_sdi:.3f} (harmony pair)")
    
    # Create silence gap
    memory.end_event_by_sound_id("birdsong", current_time)
    memory.end_event_by_sound_id("wind_through_leaves", current_time)
    silence.update(current_time, sound_count=0)
    
    result = tick(4.0)
    results.append(result)
    print(f"  t={current_time:.0f}: SDI={result.smoothed_sdi:.3f} (silence)")
    
    # More birdsong to establish pattern
    memory.add_event(make_event("birdsong", current_time))
    silence.update(current_time, sound_count=1)
    patterns.record_occurrence("birdsong", current_time)
    
    for i in range(3):
        result = tick(5.0)
        patterns.record_occurrence("birdsong", current_time)
    
    result = tick()
    results.append(result)
    print(f"  t={current_time:.0f}: SDI={result.smoothed_sdi:.3f} (pattern forming)")
    
    # Final summary
    print(f"\n  Final SDI breakdown:")
    print(f"    Raw: {result.raw_sdi:.3f}")
    print(f"    Smoothed: {result.smoothed_sdi:.3f}")
    print(f"    Target: {result.target_sdi:.3f}")
    print(f"    Delta: {result.delta:.3f} ({result.delta_category})")
    print(f"    Top +: {result.top_positive}")
    print(f"    Top -: {result.top_negative}")
    
    # Verify the system produced reasonable results
    assert all(-1.0 <= r.smoothed_sdi <= 1.0 for r in results), "All SDI values in range"
    print("  ✓ All SDI values in valid range")
    
    # CSV output test
    csv_row = result.to_csv_row()
    assert 'raw_sdi' in csv_row, "CSV row should have raw_sdi"
    assert 'density_overload' in csv_row, "CSV row should have factors"
    print(f"  ✓ CSV output has {len(csv_row)} columns")
    
    print("  Full integration test passed!")


def main():
    """Run all Phase 3 tests."""
    print("=" * 60)
    print("Living Soundscape Engine - Phase 3 Tests")
    print("SDI Calculation System")
    print("=" * 60)
    
    try:
        # Discomfort factor tests
        test_discomfort_basics()
        test_density_overload()
        test_silence_deprivation()
        test_rhythm_instability()
        
        # Comfort factor tests
        test_comfort_basics()
        test_predictable_rhythm()
        test_appropriate_silence()
        test_layer_harmony()
        test_environmental_coherence()
        
        # Main calculator tests
        test_sdi_calculator_basics()
        test_population_to_target()
        test_smoothing()
        test_delta_categorization()
        test_top_contributors()
        
        # Full integration
        test_full_integration()
        
        print("\n" + "=" * 60)
        print("ALL PHASE 3 TESTS PASSED!")
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
