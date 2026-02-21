#!/usr/bin/env python3
"""
Phase 6 Test Script for Living Soundscape Engine

Tests the output and logging system:
- EventLogger: Sound event logging
- SDILogger: SDI calculation logging
- DebugLogger: Debug output
- SessionRecorder: Complete session recording

Run from the lse directory:
    python tests/test_phase6.py
"""

import sys
import os
import tempfile
import json

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, src_path)

from output import (
    EventLogger, EventRecord,
    SDILogger, SDIRecord,
    DebugLogger, LogLevel, LogEntry,
    SessionRecorder, SessionData,
)


class MockEvent:
    """Mock SoundscapeEvent for testing."""
    def __init__(self, event_type="sound_start", sound_id="test", 
                 timestamp=0.0, instance_id="inst-1", layer="periodic",
                 duration=5.0, intensity=0.5, reason="test"):
        self.event_type = event_type
        self.sound_id = sound_id
        self.timestamp = timestamp
        self.instance_id = instance_id
        self.layer = layer
        self.duration = duration
        self.intensity = intensity
        self.reason = reason
        self.metadata = {}


class MockEnvironment:
    """Mock environment for testing."""
    def __init__(self, biome_id="forest", weather="clear", 
                 time_of_day="day", population_ratio=0.3):
        self.biome_id = biome_id
        self.weather = weather
        self.time_of_day = time_of_day
        self.population_ratio = population_ratio


class MockSDIResult:
    """Mock SDI result for testing."""
    def __init__(self, raw=0.1, smoothed=0.08, target=0.2, delta=0.12):
        self.raw_sdi = raw
        self.smoothed_sdi = smoothed
        self.target_sdi = target
        self.delta = delta
        self.delta_category = "small"
        self.biome_baseline = 0.0
        self.time_modifier = 0.0
        self.weather_modifier = 0.0
        self.discomfort = MockDiscomfort()
        self.comfort = MockComfort()


class MockDiscomfort:
    def __init__(self):
        self.total = 0.15
        self.density_overload = 0.05
        self.layer_conflict = 0.03
        self.rhythm_instability = 0.02
        self.silence_deprivation = 0.02
        self.contextual_mismatch = 0.01
        self.persistence = 0.01
        self.absence_after_pattern = 0.01


class MockComfort:
    def __init__(self):
        self.total = -0.07
        self.predictable_rhythm = -0.02
        self.appropriate_silence = -0.01
        self.layer_harmony = -0.02
        self.gradual_transition = -0.01
        self.resolution = 0.0
        self.environmental_coherence = -0.01


# =============================================================================
# EventLogger Tests
# =============================================================================

def test_event_logger_basics():
    """Test basic EventLogger functionality."""
    print("\n=== Testing EventLogger Basics ===")
    
    logger = EventLogger(max_events=100)
    
    # Log an event
    event = MockEvent(event_type="sound_start", sound_id="birdsong", timestamp=1.0)
    env = MockEnvironment()
    
    record = logger.log_event(event, env, sdi=0.1)
    
    assert record is not None, "Should return record"
    assert record.event_type == "sound_start", "Should have correct type"
    assert record.sound_id == "birdsong", "Should have correct sound_id"
    assert logger.count == 1, "Should have 1 event"
    print("  ✓ Basic event logging")
    
    # Log more events
    for i in range(10):
        e = MockEvent(event_type="sound_start", sound_id=f"sound_{i}", timestamp=float(i))
        logger.log_event(e, env, sdi=0.1)
    
    assert logger.count == 11, f"Should have 11 events, got {logger.count}"
    print(f"  ✓ Logged 11 events total")
    
    print("  All EventLogger basics tests passed!")


def test_event_logger_queries():
    """Test EventLogger query methods."""
    print("\n=== Testing EventLogger Queries ===")
    
    logger = EventLogger()
    env = MockEnvironment()
    
    # Log mixed events
    events_data = [
        ("sound_start", "birdsong", "periodic", 1.0),
        ("sound_start", "wind", "background", 2.0),
        ("sound_end", "birdsong", "periodic", 5.0),
        ("sound_start", "rain", "background", 6.0),
        ("sound_interrupt", "wind", "background", 7.0),
    ]
    
    for event_type, sound_id, layer, ts in events_data:
        e = MockEvent(event_type=event_type, sound_id=sound_id, layer=layer, timestamp=ts)
        logger.log_event(e, env, sdi=0.1)
    
    # Query by type
    starts = logger.get_starts()
    assert len(starts) == 3, f"Should have 3 starts, got {len(starts)}"
    print(f"  ✓ get_starts(): {len(starts)} events")
    
    ends = logger.get_ends()
    assert len(ends) == 1, f"Should have 1 end, got {len(ends)}"
    print(f"  ✓ get_ends(): {len(ends)} events")
    
    interrupts = logger.get_interrupts()
    assert len(interrupts) == 1, f"Should have 1 interrupt, got {len(interrupts)}"
    print(f"  ✓ get_interrupts(): {len(interrupts)} events")
    
    # Query by layer
    background = logger.get_by_layer("background")
    assert len(background) == 3, f"Should have 3 background, got {len(background)}"
    print(f"  ✓ get_by_layer(): {len(background)} background events")
    
    # Query by sound
    birdsong = logger.get_by_sound("birdsong")
    assert len(birdsong) == 2, f"Should have 2 birdsong, got {len(birdsong)}"
    print(f"  ✓ get_by_sound(): {len(birdsong)} birdsong events")
    
    # Query by time range
    range_events = logger.get_in_range(2.0, 6.0)
    assert len(range_events) == 3, f"Should have 3 in range, got {len(range_events)}"
    print(f"  ✓ get_in_range(): {len(range_events)} events")
    
    # Recent
    recent = logger.get_recent(3)
    assert len(recent) == 3, "Should get 3 recent"
    assert recent[-1].timestamp == 7.0, "Last should be most recent"
    print(f"  ✓ get_recent(): correct")
    
    print("  All EventLogger query tests passed!")


def test_event_logger_export():
    """Test EventLogger export functionality."""
    print("\n=== Testing EventLogger Export ===")
    
    logger = EventLogger()
    env = MockEnvironment()
    
    for i in range(5):
        e = MockEvent(event_type="sound_start", sound_id=f"sound_{i}", timestamp=float(i))
        logger.log_event(e, env, sdi=0.1 * i)
    
    # CSV export
    csv_data = logger.to_csv()
    assert "timestamp,event_type" in csv_data, "CSV should have header"
    assert "sound_0" in csv_data, "CSV should have data"
    lines = csv_data.strip().split('\n')
    assert len(lines) == 6, f"Should have 6 lines (header + 5 events), got {len(lines)}"
    print(f"  ✓ to_csv(): {len(csv_data)} chars")
    
    # JSON export
    json_data = logger.to_json()
    parsed = json.loads(json_data)
    assert len(parsed) == 5, "JSON should have 5 events"
    print(f"  ✓ to_json(): {len(json_data)} chars")
    
    # File export
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        filepath = f.name
    
    count = logger.write_csv(filepath)
    assert count == 5, f"Should write 5 events, wrote {count}"
    
    with open(filepath) as f:
        content = f.read()
    assert "sound_0" in content, "File should have data"
    print(f"  ✓ write_csv(): {count} events written")
    
    os.unlink(filepath)
    
    print("  All EventLogger export tests passed!")


def test_event_logger_stats():
    """Test EventLogger statistics."""
    print("\n=== Testing EventLogger Stats ===")
    
    logger = EventLogger()
    env = MockEnvironment()
    
    # Log varied events
    for i in range(10):
        e = MockEvent(
            event_type="sound_start" if i % 3 != 2 else "sound_end",
            sound_id=f"sound_{i % 3}",
            layer="periodic" if i % 2 == 0 else "background",
            timestamp=float(i)
        )
        logger.log_event(e, env)
    
    stats = logger.get_stats()
    
    assert stats['stored_events'] == 10, "Should have 10 stored"
    assert stats['total_logged'] == 10, "Should have 10 total"
    assert 'by_type' in stats, "Should have type breakdown"
    assert 'by_layer' in stats, "Should have layer breakdown"
    print(f"  ✓ Stats: {stats['total_logged']} events logged")
    
    # Top sounds
    top = stats['top_sounds']
    assert len(top) > 0, "Should have top sounds"
    print(f"  ✓ Top sounds: {top[:3]}")
    
    # Histograms
    sound_hist = logger.get_sound_histogram()
    assert len(sound_hist) == 3, "Should have 3 unique sounds"
    print(f"  ✓ Sound histogram: {len(sound_hist)} sounds")
    
    print("  All EventLogger stats tests passed!")


# =============================================================================
# SDILogger Tests
# =============================================================================

def test_sdi_logger_basics():
    """Test basic SDILogger functionality."""
    print("\n=== Testing SDILogger Basics ===")
    
    logger = SDILogger(sample_interval=0.0)  # Log everything
    
    sdi_result = MockSDIResult(smoothed=0.15)
    env = MockEnvironment()
    
    record = logger.log(0.0, sdi_result, env, active_count=5)
    
    assert record is not None, "Should return record"
    assert record.smoothed_sdi == 0.15, "Should have correct SDI"
    assert logger.count == 1, "Should have 1 record"
    print("  ✓ Basic SDI logging")
    
    # Log more (timestamps must be increasing)
    for i in range(1, 11):
        sdi = MockSDIResult(smoothed=0.1 + i * 0.02)
        logger.log(float(i), sdi, env, active_count=i)
    
    assert logger.count == 11, f"Should have 11 records, got {logger.count}"
    print(f"  ✓ Logged 11 SDI samples")
    
    print("  All SDILogger basics tests passed!")


def test_sdi_logger_sampling():
    """Test SDILogger sampling interval."""
    print("\n=== Testing SDILogger Sampling ===")
    
    logger = SDILogger(sample_interval=5.0)
    sdi = MockSDIResult()
    env = MockEnvironment()
    
    # Log at various times
    times = [0.0, 1.0, 2.0, 5.0, 6.0, 10.0, 11.0, 15.0]
    for t in times:
        logger.log(t, sdi, env)
    
    # Should only have samples at 0, 5, 10, 15 (every 5 seconds)
    assert logger.count == 4, f"Should have 4 samples (interval=5s), got {logger.count}"
    
    timestamps = logger.get_timestamps()
    assert timestamps == [0.0, 5.0, 10.0, 15.0], f"Wrong timestamps: {timestamps}"
    print(f"  ✓ Sample interval enforced: {logger.count} samples")
    
    print("  All SDILogger sampling tests passed!")


def test_sdi_logger_statistics():
    """Test SDILogger statistical methods."""
    print("\n=== Testing SDILogger Statistics ===")
    
    logger = SDILogger(sample_interval=0.0)
    env = MockEnvironment()
    
    # Log with known values
    values = [0.1, 0.2, 0.3, 0.4, 0.5]
    for i, val in enumerate(values):
        sdi = MockSDIResult(smoothed=val)
        logger.log(float(i), sdi, env)
    
    # Average
    avg = logger.get_average_sdi()
    expected_avg = sum(values) / len(values)
    assert abs(avg - expected_avg) < 0.001, f"Average should be {expected_avg}, got {avg}"
    print(f"  ✓ Average SDI: {avg:.3f}")
    
    # Range
    range_info = logger.get_sdi_range()
    assert range_info['min'] == 0.1, f"Min should be 0.1, got {range_info['min']}"
    assert range_info['max'] == 0.5, f"Max should be 0.5, got {range_info['max']}"
    print(f"  ✓ SDI range: {range_info['min']:.2f} to {range_info['max']:.2f}")
    
    # Std dev
    std = logger.get_std_dev()
    assert std > 0, "Std dev should be positive"
    print(f"  ✓ Std dev: {std:.3f}")
    
    # Full stats
    stats = logger.get_stats()
    assert 'total_samples' in stats, "Should have total_samples"
    assert 'average_sdi' in stats, "Should have average"
    print(f"  ✓ Full stats: {stats['total_samples']} samples")
    
    print("  All SDILogger statistics tests passed!")


def test_sdi_logger_factors():
    """Test SDILogger factor tracking."""
    print("\n=== Testing SDILogger Factors ===")
    
    logger = SDILogger(sample_interval=0.0)
    env = MockEnvironment()
    
    for i in range(5):
        sdi = MockSDIResult()
        logger.log(float(i), sdi, env)
    
    # Factor averages
    avgs = logger.get_factor_averages()
    assert 'density_overload' in avgs, "Should have density_overload"
    assert 'layer_harmony' in avgs, "Should have layer_harmony"
    print(f"  ✓ Factor averages: {len(avgs)} factors")
    
    # Top factors
    top_discomfort = logger.get_top_discomfort_factors(3)
    assert len(top_discomfort) == 3, "Should get 3 top discomfort factors"
    print(f"  ✓ Top discomfort: {top_discomfort[0][0]}")
    
    top_comfort = logger.get_top_comfort_factors(3)
    assert len(top_comfort) == 3, "Should get 3 top comfort factors"
    print(f"  ✓ Top comfort: {top_comfort[0][0]}")
    
    print("  All SDILogger factor tests passed!")


def test_sdi_logger_export():
    """Test SDILogger export functionality."""
    print("\n=== Testing SDILogger Export ===")
    
    logger = SDILogger(sample_interval=0.0)
    env = MockEnvironment()
    
    for i in range(5):
        sdi = MockSDIResult(smoothed=0.1 * i)
        logger.log(float(i), sdi, env)
    
    # CSV
    csv_data = logger.to_csv()
    assert "timestamp" in csv_data, "CSV should have header"
    assert "smoothed_sdi" in csv_data, "CSV should have SDI column"
    print(f"  ✓ to_csv(): {len(csv_data)} chars")
    
    # JSON
    json_data = logger.to_json()
    parsed = json.loads(json_data)
    assert len(parsed) == 5, "JSON should have 5 records"
    print(f"  ✓ to_json(): {len(json_data)} chars")
    
    print("  All SDILogger export tests passed!")


# =============================================================================
# DebugLogger Tests
# =============================================================================

def test_debug_logger_basics():
    """Test basic DebugLogger functionality."""
    print("\n=== Testing DebugLogger Basics ===")
    
    logger = DebugLogger(level=LogLevel.DEBUG)
    
    # Log at different levels
    logger.trace("engine", "Trace message", 1.0)
    logger.debug("engine", "Debug message", 2.0)
    logger.info("engine", "Info message", 3.0)
    logger.warning("engine", "Warning message", 4.0)
    logger.error("engine", "Error message", 5.0)
    
    # Trace should be filtered (DEBUG level)
    assert logger.count == 4, f"Should have 4 entries (trace filtered), got {logger.count}"
    print(f"  ✓ Level filtering: {logger.count} entries (trace filtered)")
    
    # Test with data
    logger.info("sdi", "SDI calculated", 6.0, sdi=0.15, delta=0.05)
    entry = logger.get_recent(1)[0]
    assert entry.data.get('sdi') == 0.15, "Should have sdi data"
    print("  ✓ Structured data logging")
    
    print("  All DebugLogger basics tests passed!")


def test_debug_logger_levels():
    """Test DebugLogger level filtering."""
    print("\n=== Testing DebugLogger Levels ===")
    
    # Test each level
    for level in [LogLevel.TRACE, LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]:
        logger = DebugLogger(level=level)
        
        logger.trace("test", "trace")
        logger.debug("test", "debug")
        logger.info("test", "info")
        logger.warning("test", "warning")
        logger.error("test", "error")
        
        expected = 5 - level.value
        assert logger.count == expected, f"Level {level.name}: expected {expected}, got {logger.count}"
    
    print("  ✓ All log levels work correctly")
    
    print("  All DebugLogger level tests passed!")


def test_debug_logger_categories():
    """Test DebugLogger category filtering."""
    print("\n=== Testing DebugLogger Categories ===")
    
    logger = DebugLogger(level=LogLevel.DEBUG)
    
    # Log multiple categories
    logger.debug("engine", "Engine message")
    logger.debug("sdi", "SDI message")
    logger.debug("sound", "Sound message")
    logger.debug("memory", "Memory message")
    
    assert logger.count == 4, "Should have 4 entries"
    
    # Set filter
    logger.set_category_filter(["sdi", "sound"])
    
    logger.debug("engine", "Filtered out")
    logger.debug("sdi", "Should appear")
    
    assert logger.count == 5, "Should have 5 entries (1 filtered)"
    print("  ✓ Category filtering works")
    
    # Query by category
    sdi_entries = logger.get_by_category("sdi")
    assert len(sdi_entries) == 2, f"Should have 2 SDI entries, got {len(sdi_entries)}"
    print(f"  ✓ get_by_category(): {len(sdi_entries)} SDI entries")
    
    print("  All DebugLogger category tests passed!")


def test_debug_logger_specialized():
    """Test DebugLogger specialized logging methods."""
    print("\n=== Testing DebugLogger Specialized Methods ===")
    
    logger = DebugLogger(level=LogLevel.TRACE)
    
    # Tick logging
    logger.log_tick(1.0, sdi=0.15, active_sounds=5, delta=0.05)
    print("  ✓ log_tick()")
    
    # Sound logging
    logger.log_sound_start(2.0, "birdsong", "periodic", 5.0, 0.7)
    logger.log_sound_end(7.0, "birdsong", "natural")
    logger.log_sound_interrupt(8.0, "wind", "sdi_reduction")
    print("  ✓ log_sound_start/end/interrupt()")
    
    # SDI logging
    logger.log_sdi_calculation(3.0, raw=0.12, smoothed=0.10, target=0.20, 
                                delta=0.10, top_pos="density", top_neg="harmony")
    print("  ✓ log_sdi_calculation()")
    
    # Environment change
    logger.log_environment_change(4.0, "weather", "clear", "rain")
    print("  ✓ log_environment_change()")
    
    # Pattern
    logger.log_pattern_detected(5.0, "birdsong", "rhythmic", 4.5)
    print("  ✓ log_pattern_detected()")
    
    assert logger.count >= 7, f"Should have at least 7 entries, got {logger.count}"
    
    print("  All DebugLogger specialized tests passed!")


def test_debug_logger_performance():
    """Test DebugLogger performance tracking."""
    print("\n=== Testing DebugLogger Performance ===")
    
    logger = DebugLogger()
    
    # Simulate ticks
    import time
    for _ in range(10):
        logger.tick_start()
        time.sleep(0.001)  # 1ms work
        duration = logger.tick_end()
        assert duration > 0, "Duration should be positive"
    
    stats = logger.get_performance_stats()
    assert stats['samples'] == 10, "Should have 10 samples"
    assert stats['avg_ms'] > 0, "Avg should be positive"
    print(f"  ✓ Performance: avg={stats['avg_ms']:.2f}ms, samples={stats['samples']}")
    
    print("  All DebugLogger performance tests passed!")


def test_debug_logger_export():
    """Test DebugLogger export functionality."""
    print("\n=== Testing DebugLogger Export ===")
    
    logger = DebugLogger(level=LogLevel.DEBUG)
    
    for i in range(5):
        logger.info("test", f"Message {i}", float(i), value=i)
    
    # Text export
    text = logger.to_text()
    assert "Message 0" in text, "Text should have messages"
    lines = text.strip().split('\n')
    assert len(lines) == 5, f"Should have 5 lines, got {len(lines)}"
    print(f"  ✓ to_text(): {len(lines)} lines")
    
    # JSON export
    json_data = logger.to_json()
    parsed = json.loads(json_data)
    assert len(parsed) == 5, "JSON should have 5 entries"
    print(f"  ✓ to_json(): {len(json_data)} chars")
    
    # Summary
    summary = logger.get_summary()
    assert "Total entries: 5" in summary, "Summary should have count"
    print("  ✓ get_summary()")
    
    print("  All DebugLogger export tests passed!")


# =============================================================================
# SessionRecorder Tests
# =============================================================================

def test_session_recorder_basics():
    """Test basic SessionRecorder functionality."""
    print("\n=== Testing SessionRecorder Basics ===")
    
    recorder = SessionRecorder()
    
    assert not recorder.is_recording, "Should not be recording initially"
    
    # Start recording
    recorder.start(seed=42, config_summary={'biomes': 12})
    
    assert recorder.is_recording, "Should be recording after start"
    print("  ✓ Session started")
    
    # Record some events
    event = MockEvent(event_type="sound_start", sound_id="birdsong", timestamp=1.0)
    env = MockEnvironment()
    
    recorder.record_event(event, env, sdi=0.1)
    print("  ✓ Event recorded")
    
    # Record SDI
    sdi = MockSDIResult(smoothed=0.15)
    recorder.record_sdi(1.0, sdi, env, active_count=3)
    print("  ✓ SDI recorded")
    
    # Stop recording
    session = recorder.stop()
    
    assert not recorder.is_recording, "Should not be recording after stop"
    assert session is not None, "Should return session data"
    assert session.seed == 42, "Should have seed"
    assert len(session.events) == 1, "Should have 1 event"
    print("  ✓ Session stopped")
    
    print("  All SessionRecorder basics tests passed!")


def test_session_recorder_recording():
    """Test SessionRecorder recording methods."""
    print("\n=== Testing SessionRecorder Recording ===")
    
    recorder = SessionRecorder(snapshot_interval=5.0, sdi_interval=1.0)
    recorder.start(seed=123)
    
    env = MockEnvironment()
    
    # Record events
    for i in range(5):
        event = MockEvent(
            event_type="sound_start" if i % 2 == 0 else "sound_end",
            sound_id=f"sound_{i}",
            timestamp=float(i)
        )
        recorder.record_event(event, env, sdi=0.1)
    
    # Record SDI (should respect interval)
    for i in range(10):
        sdi = MockSDIResult(smoothed=0.1 + i * 0.01)
        recorded = recorder.record_sdi(float(i) * 0.5, sdi, env)
    
    # Record snapshots
    for i in range(15):
        state = {
            'simulation_time': float(i),
            'environment': {'biome_id': 'forest', 'weather': 'clear'},
            'sdi': {'current': 0.1, 'target': 0.2, 'delta': 0.1},
            'stats': {'active_sounds': 3},
            'memory': {'patterns_tracked': 1},
        }
        recorder.record_snapshot(state, float(i))
    
    session = recorder.stop()
    
    assert len(session.events) == 5, f"Should have 5 events, got {len(session.events)}"
    print(f"  ✓ Events: {len(session.events)}")
    
    # SDI samples depend on interval
    print(f"  ✓ SDI samples: {len(session.sdi_timeline)}")
    
    # Snapshots depend on interval
    print(f"  ✓ Snapshots: {len(session.snapshots)}")
    
    print("  All SessionRecorder recording tests passed!")


def test_session_recorder_environment():
    """Test SessionRecorder environment change tracking."""
    print("\n=== Testing SessionRecorder Environment Tracking ===")
    
    recorder = SessionRecorder()
    recorder.start()
    
    # Simulate environment changes
    env1 = MockEnvironment(biome_id="forest", weather="clear")
    recorder.check_environment_change(0.0, env1)
    
    env2 = MockEnvironment(biome_id="forest", weather="rain")
    recorder.check_environment_change(10.0, env2)
    
    env3 = MockEnvironment(biome_id="swamp", weather="rain")
    recorder.check_environment_change(20.0, env3)
    
    session = recorder.stop()
    
    # Should have 2 changes (weather and biome)
    assert len(session.environment_changes) == 2, f"Should have 2 changes, got {len(session.environment_changes)}"
    print(f"  ✓ Environment changes tracked: {len(session.environment_changes)}")
    
    # Check change details
    weather_change = [c for c in session.environment_changes if c['change_type'] == 'weather']
    assert len(weather_change) == 1, "Should have 1 weather change"
    assert weather_change[0]['old_value'] == 'clear', "Old weather should be clear"
    assert weather_change[0]['new_value'] == 'rain', "New weather should be rain"
    print("  ✓ Change details correct")
    
    print("  All SessionRecorder environment tests passed!")


def test_session_data_export():
    """Test SessionData export functionality."""
    print("\n=== Testing SessionData Export ===")
    
    recorder = SessionRecorder()
    recorder.start(seed=42)
    
    env = MockEnvironment()
    for i in range(5):
        event = MockEvent(sound_id=f"sound_{i}", timestamp=float(i))
        recorder.record_event(event, env)
        
        sdi = MockSDIResult(smoothed=0.1 * i)
        recorder.record_sdi(float(i), sdi, env)
    
    session = recorder.stop()
    
    # Summary
    summary = session.get_summary()
    assert "SESSION SUMMARY" in summary, "Should have header"
    assert "Total events: 5" in summary, "Should have event count"
    print("  ✓ get_summary()")
    
    # JSON export
    json_str = session.to_json()
    parsed = json.loads(json_str)
    assert 'metadata' in parsed, "JSON should have metadata"
    assert 'events' in parsed, "JSON should have events"
    print(f"  ✓ to_json(): {len(json_str)} chars")
    
    # CSV exports
    events_csv = session.events_to_csv()
    assert len(events_csv) > 0, "Should have events CSV"
    print(f"  ✓ events_to_csv(): {len(events_csv)} chars")
    
    sdi_csv = session.sdi_to_csv()
    assert len(sdi_csv) > 0, "Should have SDI CSV"
    print(f"  ✓ sdi_to_csv(): {len(sdi_csv)} chars")
    
    # File save/load
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name
    
    session.save(filepath)
    print(f"  ✓ save()")
    
    loaded = SessionData.load(filepath)
    assert loaded.seed == 42, "Loaded session should have seed"
    assert len(loaded.events) == 5, "Loaded session should have events"
    print(f"  ✓ load()")
    
    os.unlink(filepath)
    
    print("  All SessionData export tests passed!")


# =============================================================================
# Integration Tests
# =============================================================================

def test_full_integration():
    """Test full logging integration with engine."""
    print("\n=== Testing Full Logging Integration ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    
    from engine import LSEEngine
    
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    # Set up loggers
    event_logger = EventLogger()
    sdi_logger = SDILogger(sample_interval=1.0)
    debug_logger = DebugLogger(level=LogLevel.INFO)
    session_recorder = SessionRecorder()
    
    # Start session
    session_recorder.start(seed=42, config_summary={'biomes': 12, 'sounds': 58})
    
    # Register event callback
    def on_event(event):
        event_logger.log_event(event, engine.environment, engine.sdi)
        session_recorder.record_event(event, engine.environment, engine.sdi)
        
        if event.event_type.value == "sound_start":
            debug_logger.log_sound_start(
                event.timestamp, event.sound_id, event.layer,
                event.duration, event.intensity
            )
    
    engine.on_event(on_event)
    
    # Run simulation
    engine.set_environment(biome_id="forest", weather="clear", time_of_day="day")
    engine.set_population(0.3)
    
    print("  Running 60 second simulation...")
    
    for t in range(60):
        debug_logger.tick_start()
        
        events = engine.tick(delta_time=1.0)
        
        duration = debug_logger.tick_end()
        
        # Log SDI
        if engine.sdi_result:
            sdi_logger.log(float(t), engine.sdi_result, engine.environment,
                          len(engine.get_active_sounds()))
            session_recorder.record_sdi(float(t), engine.sdi_result,
                                        engine.environment)
        
        # Log tick
        debug_logger.log_tick(float(t), engine.sdi, len(engine.get_active_sounds()),
                             engine.sdi_delta)
        
        # Check environment changes
        session_recorder.check_environment_change(float(t), engine.environment)
        
        # Periodic snapshot
        if t % 10 == 0:
            session_recorder.record_snapshot(engine.get_state(), float(t))
        
        # Change population midway
        if t == 30:
            engine.set_population(0.7)
            debug_logger.log_environment_change(float(t), "population", 0.3, 0.7)
    
    # Stop session
    session = session_recorder.stop()
    
    # Print results
    print(f"\n  Results:")
    print(f"    Events logged: {event_logger.count}")
    print(f"    SDI samples: {sdi_logger.count}")
    print(f"    Debug entries: {debug_logger.count}")
    print(f"    Session events: {len(session.events)}")
    print(f"    Session SDI: {len(session.sdi_timeline)}")
    print(f"    Session snapshots: {len(session.snapshots)}")
    
    # Event stats
    event_stats = event_logger.get_stats()
    print(f"\n  Event Stats:")
    print(f"    By type: {event_stats['by_type']}")
    print(f"    Top sounds: {event_stats['top_sounds'][:3]}")
    
    # SDI stats
    sdi_stats = sdi_logger.get_stats()
    print(f"\n  SDI Stats:")
    print(f"    Average: {sdi_stats['average_sdi']:.3f}")
    print(f"    Range: {sdi_stats['min']:.3f} to {sdi_stats['max']:.3f}")
    
    # Top factors
    top_dis = sdi_logger.get_top_discomfort_factors(2)
    top_com = sdi_logger.get_top_comfort_factors(2)
    print(f"    Top discomfort: {[f[0] for f in top_dis]}")
    print(f"    Top comfort: {[f[0] for f in top_com]}")
    
    # Performance
    perf = debug_logger.get_performance_stats()
    print(f"\n  Performance:")
    print(f"    Avg tick: {perf['avg_ms']:.2f}ms")
    print(f"    Max tick: {perf['max_ms']:.2f}ms")
    
    # Session summary
    print(f"\n  Session Summary Preview:")
    summary_lines = session.get_summary().split('\n')[:15]
    for line in summary_lines:
        print(f"    {line}")
    
    # Verify data
    assert event_logger.count > 0, "Should have logged events"
    assert sdi_logger.count > 0, "Should have logged SDI"
    assert len(session.events) > 0, "Session should have events"
    
    print("\n  ✓ Full integration test passed!")


def main():
    """Run all Phase 6 tests."""
    print("=" * 60)
    print("Living Soundscape Engine - Phase 6 Tests")
    print("Output and Logging System")
    print("=" * 60)
    
    try:
        # EventLogger tests
        test_event_logger_basics()
        test_event_logger_queries()
        test_event_logger_export()
        test_event_logger_stats()
        
        # SDILogger tests
        test_sdi_logger_basics()
        test_sdi_logger_sampling()
        test_sdi_logger_statistics()
        test_sdi_logger_factors()
        test_sdi_logger_export()
        
        # DebugLogger tests
        test_debug_logger_basics()
        test_debug_logger_levels()
        test_debug_logger_categories()
        test_debug_logger_specialized()
        test_debug_logger_performance()
        test_debug_logger_export()
        
        # SessionRecorder tests
        test_session_recorder_basics()
        test_session_recorder_recording()
        test_session_recorder_environment()
        test_session_data_export()
        
        # Full integration
        test_full_integration()
        
        print("\n" + "=" * 60)
        print("ALL PHASE 6 TESTS PASSED!")
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
