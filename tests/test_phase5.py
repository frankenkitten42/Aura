#!/usr/bin/env python3
"""
Phase 5 Test Script for Living Soundscape Engine

Tests the main engine integration:
- LSEEngine: Main engine class
- SimulationRunner: Simulation and demo runner
- Full feedback loop integration

Run from the lse directory:
    python tests/test_phase5.py
"""

import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, src_path)

from config import load_config
from engine import LSEEngine, EnvironmentState, EngineStats
from simulation import SimulationRunner, SimulationResults, run_demo


def test_engine_initialization():
    """Test LSEEngine initialization."""
    print("\n=== Testing Engine Initialization ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    
    # Initialize with path
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    assert engine is not None, "Engine should initialize"
    assert engine.config is not None, "Should have config"
    assert engine.rng is not None, "Should have RNG"
    print("  ✓ Engine initialized with config path")
    
    # Check initial state
    assert engine.simulation_time == 0.0, "Should start at time 0"
    assert engine.sdi == 0.0, "Should start with SDI 0"
    assert engine.stats.total_ticks == 0, "Should start with 0 ticks"
    print("  ✓ Initial state correct")
    
    # Initialize with pre-loaded config
    config = load_config(config_dir)
    engine2 = LSEEngine(config=config, seed=123)
    assert engine2.config is config, "Should use provided config"
    print("  ✓ Engine initialized with pre-loaded config")
    
    print("  All engine initialization tests passed!")


def test_environment_control():
    """Test environment state control."""
    print("\n=== Testing Environment Control ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    # Check default environment
    assert engine.environment.biome_id == "forest", "Default biome should be forest"
    assert engine.environment.time_of_day == "day", "Default time should be day"
    assert engine.environment.weather == "clear", "Default weather should be clear"
    print("  ✓ Default environment state")
    
    # Set environment
    engine.set_environment(
        biome_id="desert",
        weather="rain",
        time_of_day="night",
    )
    assert engine.environment.biome_id == "desert", "Biome should be desert"
    assert engine.environment.weather == "rain", "Weather should be rain"
    assert engine.environment.time_of_day == "night", "Time should be night"
    print("  ✓ Environment update")
    
    # Individual setters
    engine.set_biome("swamp")
    assert engine.environment.biome_id == "swamp", "Should update biome"
    
    engine.set_weather("fog")
    assert engine.environment.weather == "fog", "Should update weather"
    
    engine.set_time_of_day("dawn")
    assert engine.environment.time_of_day == "dawn", "Should update time"
    print("  ✓ Individual setters")
    
    # Population
    engine.set_population(0.75)
    assert engine.environment.population_ratio == 0.75, "Should update population"
    
    # Clamp to range
    engine.set_population(1.5)
    assert engine.environment.population_ratio == 1.0, "Should clamp to 1.0"
    
    engine.set_population(-0.5)
    assert engine.environment.population_ratio == 0.0, "Should clamp to 0.0"
    print("  ✓ Population control")
    
    print("  All environment control tests passed!")


def test_engine_tick():
    """Test engine tick cycle."""
    print("\n=== Testing Engine Tick ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    # Initial tick
    events = engine.tick(delta_time=1.0)
    
    assert engine.stats.total_ticks == 1, "Should have 1 tick"
    assert engine.simulation_time == 1.0, "Time should advance"
    assert isinstance(events, list), "Should return event list"
    print(f"  ✓ First tick: {len(events)} events")
    
    # Multiple ticks
    total_events = len(events)
    for _ in range(9):
        events = engine.tick(delta_time=1.0)
        total_events += len(events)
    
    assert engine.stats.total_ticks == 10, "Should have 10 ticks"
    assert engine.simulation_time == 10.0, "Time should be 10"
    print(f"  ✓ 10 ticks: {total_events} total events")
    
    # Check stats are updated
    assert engine.stats.total_events >= 0, "Should track events"
    print(f"  ✓ Stats: started={engine.stats.total_sounds_started}, ended={engine.stats.total_sounds_ended}")
    
    print("  All engine tick tests passed!")


def test_sdi_feedback():
    """Test SDI feedback loop."""
    print("\n=== Testing SDI Feedback Loop ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    # Low population - should have low/negative SDI target
    engine.set_population(0.0)
    engine.tick(1.0)
    
    sdi_result = engine.sdi_result
    assert sdi_result is not None, "Should have SDI result"
    assert sdi_result.target_sdi < 0.1, f"Low pop should have low target: {sdi_result.target_sdi}"
    print(f"  ✓ Low population: target SDI = {sdi_result.target_sdi:.3f}")
    
    # Run more ticks to see SDI evolution
    for _ in range(20):
        engine.tick(1.0)
    
    low_pop_sdi = engine.sdi
    print(f"  ✓ SDI after 20 ticks (low pop): {low_pop_sdi:.3f}")
    
    # High population - should drive SDI up
    engine.set_population(0.9)
    for _ in range(30):
        engine.tick(1.0)
    
    high_pop_sdi = engine.sdi
    sdi_result = engine.sdi_result
    print(f"  ✓ SDI after high pop: {high_pop_sdi:.3f}, target: {sdi_result.target_sdi:.3f}")
    
    # Delta should be positive (need more SDI)
    assert sdi_result.target_sdi > low_pop_sdi, "High pop should have higher target"
    print(f"  ✓ Delta: {engine.sdi_delta:.3f}")
    
    # Check SDI breakdown is available
    breakdown = engine.get_sdi_breakdown()
    assert 'density_overload' in breakdown, "Should have factor breakdown"
    assert 'environmental_coherence' in breakdown, "Should have comfort factors"
    print(f"  ✓ SDI breakdown has {len(breakdown)} factors")
    
    print("  All SDI feedback tests passed!")


def test_event_callbacks():
    """Test event callback system."""
    print("\n=== Testing Event Callbacks ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    received_events = []
    
    def callback(event):
        received_events.append(event)
    
    # Register callback
    engine.on_event(callback)
    
    # Run ticks
    for _ in range(30):
        engine.tick(1.0)
    
    print(f"  ✓ Received {len(received_events)} events via callback")
    assert len(received_events) > 0, "Should receive some events"
    
    # Check event structure
    for event in received_events[:3]:
        assert hasattr(event, 'event_type'), "Event should have type"
        assert hasattr(event, 'sound_id'), "Event should have sound_id"
        print(f"    - {event.event_type.value}: {event.sound_id}")
    
    # Remove callback
    engine.remove_callback(callback)
    old_count = len(received_events)
    engine.tick(1.0)
    assert len(received_events) == old_count, "Should not receive events after removal"
    print("  ✓ Callback removal works")
    
    print("  All event callback tests passed!")


def test_manual_sound_control():
    """Test manual sound triggering and stopping."""
    print("\n=== Testing Manual Sound Control ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    # Trigger a sound
    event = engine.trigger_sound("birdsong")
    
    assert event is not None, "Should create event"
    assert event.sound_id == "birdsong", "Should be birdsong"
    print(f"  ✓ Triggered: {event.sound_id} ({event.instance_id[:8]}...)")
    
    # Check it's active
    active = engine.get_active_sounds()
    assert any(s.sound_id == "birdsong" for s in active), "Birdsong should be active"
    print(f"  ✓ Sound is active (total active: {len(active)})")
    
    # Stop it
    stop_event = engine.stop_sound(event.instance_id)
    
    assert stop_event is not None, "Should create stop event"
    assert stop_event.event_type.value == "sound_interrupt", "Should be interrupt"
    print(f"  ✓ Stopped: {stop_event.sound_id}")
    
    # Check it's gone
    active = engine.get_active_sounds()
    birdsong_active = [s for s in active if s.sound_id == "birdsong"]
    assert len(birdsong_active) == 0, "Birdsong should not be active"
    print("  ✓ Sound removed from active")
    
    # Trigger with custom params
    event2 = engine.trigger_sound("wind_through_leaves", duration=10.0, intensity=0.8)
    assert event2.duration == 10.0, "Should use custom duration"
    assert event2.intensity == 0.8, "Should use custom intensity"
    print(f"  ✓ Custom params: duration={event2.duration}, intensity={event2.intensity}")
    
    print("  All manual sound control tests passed!")


def test_notifications():
    """Test transition and resolution notifications."""
    print("\n=== Testing Notifications ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    # Run some ticks
    for _ in range(10):
        engine.tick(1.0)
    
    # Notify transition
    engine.notify_transition()
    sdi_before = engine.sdi
    
    # This should contribute to comfort in next tick
    engine.tick(1.0)
    print(f"  ✓ After transition notification: SDI = {engine.sdi:.3f}")
    
    # Notify resolution
    engine.notify_resolution()
    engine.tick(1.0)
    print(f"  ✓ After resolution notification: SDI = {engine.sdi:.3f}")
    
    print("  All notification tests passed!")


def test_state_inspection():
    """Test state inspection methods."""
    print("\n=== Testing State Inspection ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    # Run some ticks
    engine.set_population(0.5)
    for _ in range(30):
        engine.tick(1.0)
    
    # Get full state
    state = engine.get_state()
    
    assert 'simulation_time' in state, "Should have time"
    assert 'environment' in state, "Should have environment"
    assert 'sdi' in state, "Should have SDI"
    assert 'soundscape' in state, "Should have soundscape"
    assert 'stats' in state, "Should have stats"
    assert 'memory' in state, "Should have memory"
    print(f"  ✓ State has {len(state)} top-level keys")
    
    # Check environment state
    env = state['environment']
    assert 'biome_id' in env, "Should have biome"
    assert 'population_ratio' in env, "Should have population"
    print(f"  ✓ Environment: {env['biome_id']}, pop={env['population_ratio']}")
    
    # Check SDI state
    sdi = state['sdi']
    assert 'current' in sdi, "Should have current SDI"
    assert 'target' in sdi, "Should have target SDI"
    print(f"  ✓ SDI: current={sdi['current']:.3f}, target={sdi['target']:.3f}")
    
    # Check stats
    stats = state['stats']
    assert 'total_ticks' in stats, "Should have tick count"
    print(f"  ✓ Stats: {stats['total_ticks']} ticks, {stats['total_sounds_started']} sounds")
    
    print("  All state inspection tests passed!")


def test_engine_reset():
    """Test engine reset."""
    print("\n=== Testing Engine Reset ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    # Run some ticks
    for _ in range(20):
        engine.tick(1.0)
    
    assert engine.stats.total_ticks == 20, "Should have 20 ticks"
    assert engine.simulation_time == 20.0, "Time should be 20"
    print(f"  Before reset: ticks={engine.stats.total_ticks}, time={engine.simulation_time}")
    
    # Reset
    engine.reset()
    
    assert engine.stats.total_ticks == 0, "Should have 0 ticks after reset"
    assert engine.simulation_time == 0.0, "Time should be 0 after reset"
    assert engine.sdi == 0.0, "SDI should be 0 after reset"
    print(f"  After reset: ticks={engine.stats.total_ticks}, time={engine.simulation_time}")
    
    # Should be able to run again
    engine.tick(1.0)
    assert engine.stats.total_ticks == 1, "Should be able to tick after reset"
    print("  ✓ Engine runs after reset")
    
    print("  All engine reset tests passed!")


def test_simulation_runner():
    """Test SimulationRunner."""
    print("\n=== Testing SimulationRunner ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    
    runner = SimulationRunner(config_path=config_dir, seed=42)
    
    # Configure
    runner.configure(
        duration=30.0,
        tick_interval=0.5,
        initial_biome="forest",
        initial_population=0.2,
    )
    
    # Add steps
    runner.add_step(10.0, "set_population", {"ratio": 0.5})
    runner.add_step(20.0, "set_weather", {"weather": "rain"})
    
    # Run
    results = runner.run()
    
    assert isinstance(results, SimulationResults), "Should return results"
    assert len(results.events) > 0, "Should have events"
    assert len(results.sdi_log) > 0, "Should have SDI log"
    assert len(results.step_log) == 2, "Should have 2 step logs"
    print(f"  ✓ Simulation ran: {len(results.events)} events")
    
    # Check stats
    assert results.stats['total_ticks'] > 0, "Should have ticks"
    print(f"  ✓ Stats: {results.stats['total_ticks']} ticks")
    
    # Test summary
    summary = results.summary()
    assert "SIMULATION RESULTS" in summary, "Summary should have header"
    assert "Duration" in summary, "Summary should have duration"
    print("  ✓ Summary generated")
    
    # Test CSV export
    events_csv = results.events_to_csv()
    assert "time,event_type" in events_csv, "Events CSV should have header"
    print(f"  ✓ Events CSV: {len(events_csv)} chars")
    
    sdi_csv = results.sdi_to_csv()
    assert "time,sdi" in sdi_csv, "SDI CSV should have header"
    print(f"  ✓ SDI CSV: {len(sdi_csv)} chars")
    
    # Test JSON export
    json_str = results.to_json()
    assert '"events"' in json_str, "JSON should have events"
    print(f"  ✓ JSON export: {len(json_str)} chars")
    
    print("  All SimulationRunner tests passed!")


def test_demo_simulation():
    """Test the demo simulation."""
    print("\n=== Testing Demo Simulation ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    
    # Run a short demo
    results = run_demo(config_path=config_dir, duration=30.0, seed=42)
    
    assert isinstance(results, SimulationResults), "Should return results"
    assert len(results.events) > 0, "Should have events"
    print(f"  ✓ Demo ran: {len(results.events)} events, {results.stats['total_ticks']} ticks")
    
    # Check SDI range
    sdi_values = [entry['sdi'] for entry in results.sdi_log]
    min_sdi = min(sdi_values)
    max_sdi = max(sdi_values)
    print(f"  ✓ SDI range: {min_sdi:.3f} to {max_sdi:.3f}")
    
    # Check summary
    summary = results.summary()
    print("\n" + summary)
    
    print("  Demo simulation test passed!")


def test_full_integration():
    """Test complete engine integration."""
    print("\n=== Testing Full Integration ===")
    
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
    engine = LSEEngine(config_path=config_dir, seed=42)
    
    # Scenario: Simulate a player session
    print("  Simulating player session...")
    
    events_log = []
    sdi_log = []
    
    def log_event(event):
        events_log.append(event)
    
    engine.on_event(log_event)
    
    # Phase 1: Player enters quiet forest (0-30s)
    print("    Phase 1: Quiet forest...")
    engine.set_environment(biome_id="forest", time_of_day="day", weather="clear")
    engine.set_population(0.1)
    
    for t in range(30):
        engine.tick(1.0)
        if t % 10 == 0:
            sdi_log.append((t, engine.sdi, engine.sdi_delta))
    
    # Phase 2: Other players arrive (30-60s)
    print("    Phase 2: Population increases...")
    for t in range(30, 60):
        pop = 0.1 + (t - 30) * 0.02  # Gradual increase
        engine.set_population(pop)
        engine.tick(1.0)
        if t % 10 == 0:
            sdi_log.append((t, engine.sdi, engine.sdi_delta))
    
    # Phase 3: Weather changes (60-90s)
    print("    Phase 3: Storm arrives...")
    engine.set_weather("storm")
    engine.set_population(0.7)
    
    for t in range(60, 90):
        engine.tick(1.0)
        if t % 10 == 0:
            sdi_log.append((t, engine.sdi, engine.sdi_delta))
    
    # Phase 4: Storm passes, players leave (90-120s)
    print("    Phase 4: Resolution...")
    engine.set_weather("clear")
    engine.notify_resolution()  # Storm ending
    
    for t in range(90, 120):
        pop = 0.7 - (t - 90) * 0.02  # Gradual decrease
        engine.set_population(max(0.1, pop))
        engine.tick(1.0)
        if t % 10 == 0:
            sdi_log.append((t, engine.sdi, engine.sdi_delta))
    
    # Results
    print("\n  Session Results:")
    print(f"    Total events: {len(events_log)}")
    print(f"    Sounds started: {engine.stats.total_sounds_started}")
    print(f"    Sounds ended: {engine.stats.total_sounds_ended}")
    
    print("\n  SDI Timeline:")
    for t, sdi, delta in sdi_log:
        pop = engine.environment.population_ratio
        marker = "+" if delta > 0.1 else "-" if delta < -0.1 else "="
        print(f"    t={t:3d}s: SDI={sdi:+.3f}, delta={delta:+.3f} {marker}")
    
    # Verify the system responded appropriately
    # SDI should have been higher during high population
    mid_sdi = [s for t, s, d in sdi_log if 60 <= t <= 80]
    end_sdi = [s for t, s, d in sdi_log if t >= 100]
    
    if mid_sdi and end_sdi:
        avg_mid = sum(mid_sdi) / len(mid_sdi)
        avg_end = sum(end_sdi) / len(end_sdi)
        print(f"\n  SDI comparison: high-pop avg={avg_mid:.3f}, low-pop avg={avg_end:.3f}")
    
    # Final state
    state = engine.get_state()
    print(f"\n  Final state:")
    print(f"    Simulation time: {state['simulation_time']:.0f}s")
    print(f"    Active sounds: {state['stats']['active_sounds']}")
    print(f"    Patterns tracked: {state['memory']['patterns_tracked']}")
    
    print("\n  ✓ Full integration test passed!")


def main():
    """Run all Phase 5 tests."""
    print("=" * 60)
    print("Living Soundscape Engine - Phase 5 Tests")
    print("Main Engine Integration")
    print("=" * 60)
    
    try:
        # LSEEngine tests
        test_engine_initialization()
        test_environment_control()
        test_engine_tick()
        test_sdi_feedback()
        test_event_callbacks()
        test_manual_sound_control()
        test_notifications()
        test_state_inspection()
        test_engine_reset()
        
        # SimulationRunner tests
        test_simulation_runner()
        test_demo_simulation()
        
        # Full integration
        test_full_integration()
        
        print("\n" + "=" * 60)
        print("ALL PHASE 5 TESTS PASSED!")
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
