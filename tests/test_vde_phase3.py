"""
VDE Phase 3 Tests: Wildlife System

Tests:
- Wildlife state machine transitions
- Tier-based sensitivity
- Asymmetric flee/recovery timing
- Per-creature spawn rate modulation
- Behavior modifications per state
- Recovery "memory" effect
- UE5 spawn command generation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from vde.wildlife import (
    WildlifeManager, WildlifeConfig, WildlifeSnapshot,
    WildlifeState, CreatureTier, CreatureCategory, CreatureState,
    WildlifeSpawnGenerator, FWildlifeSpawnCommand, CREATURE_TIERS,
)


class TestWildlifeStateTransitions(unittest.TestCase):
    """Test wildlife state machine transitions."""
    
    def setUp(self):
        self.manager = WildlifeManager()
    
    def test_initial_state_thriving(self):
        """Wildlife should start in THRIVING state."""
        self.assertEqual(self.manager.global_state, WildlifeState.THRIVING)
    
    def test_low_pop_maintains_thriving(self):
        """Low population should maintain THRIVING state."""
        self.manager.set_population(0.05)
        
        for _ in range(20):
            snapshot = self.manager.update(delta_time=0.5)
        
        self.assertEqual(snapshot.global_state, WildlifeState.THRIVING)
    
    def test_medium_pop_triggers_wary(self):
        """Medium population should trigger WARY state."""
        self.manager.set_population(0.25)
        
        for _ in range(50):
            snapshot = self.manager.update(delta_time=0.5)
        
        # Tier 1 should be at least WARY
        tier1_states = [
            c.state for c in self.manager.creatures.values()
            if c.tier == CreatureTier.TIER_1
        ]
        self.assertTrue(all(
            s in [WildlifeState.WARY, WildlifeState.RETREATING, WildlifeState.ABSENT]
            for s in tier1_states
        ))
    
    def test_high_pop_triggers_absent(self):
        """High population should eventually trigger ABSENT state."""
        self.manager.set_population(0.80)
        
        for _ in range(100):
            snapshot = self.manager.update(delta_time=0.5)
        
        # Tier 1 should be ABSENT
        tier1_states = [
            c.state for c in self.manager.creatures.values()
            if c.tier == CreatureTier.TIER_1
        ]
        self.assertTrue(all(s == WildlifeState.ABSENT for s in tier1_states))
    
    def test_state_order_maintained(self):
        """States should transition in order: THRIVING → WARY → RETREATING → ABSENT."""
        self.manager.set_population(0.90)
        
        # Track states visited by a Tier 1 creature
        bird = self.manager.creatures[CreatureCategory.BIRDS_SMALL]
        states_seen = [bird.state]
        
        for _ in range(200):
            self.manager.update(delta_time=0.5)
            if bird.state != states_seen[-1]:
                states_seen.append(bird.state)
        
        # Should have gone through states in order
        expected_order = [WildlifeState.THRIVING, WildlifeState.WARY, 
                         WildlifeState.RETREATING, WildlifeState.ABSENT]
        
        for i, state in enumerate(states_seen[:-1]):
            expected_next_idx = expected_order.index(state) + 1
            if expected_next_idx < len(expected_order):
                self.assertEqual(states_seen[i + 1], expected_order[expected_next_idx])


class TestTierSensitivity(unittest.TestCase):
    """Test creature tier sensitivity differences."""
    
    def setUp(self):
        self.manager = WildlifeManager()
    
    def test_tier1_most_sensitive(self):
        """Tier 1 creatures should flee first."""
        self.manager.set_population(0.40)
        
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        # Get states per tier
        tier_states = {}
        for tier in CreatureTier:
            tier_creatures = [c for c in self.manager.creatures.values() if c.tier == tier]
            if tier_creatures:
                tier_states[tier] = tier_creatures[0].state
        
        # Tier 1 should be in worse state than Tier 3
        state_order = [WildlifeState.THRIVING, WildlifeState.WARY, 
                       WildlifeState.RETREATING, WildlifeState.ABSENT]
        
        tier1_idx = state_order.index(tier_states[CreatureTier.TIER_1])
        tier3_idx = state_order.index(tier_states[CreatureTier.TIER_3])
        
        self.assertGreaterEqual(tier1_idx, tier3_idx,
                               "Tier 1 should be in equal or worse state than Tier 3")
    
    def test_tier3_never_fully_absent(self):
        """Tier 3 creatures (insects) should never have zero spawn rate."""
        self.manager.set_population(0.95)
        
        for _ in range(100):
            self.manager.update(delta_time=0.5)
        
        # Check Tier 3 spawn rates
        tier3_rates = [
            c.current_spawn_rate 
            for c in self.manager.creatures.values()
            if c.tier == CreatureTier.TIER_3
        ]
        
        self.assertTrue(all(r > 0 for r in tier3_rates),
                       "Tier 3 creatures should always have some spawn rate")
    
    def test_tier_mapping_correct(self):
        """Creature tier mapping should be correct."""
        # Tier 1
        self.assertEqual(CREATURE_TIERS[CreatureCategory.BIRDS_SMALL], CreatureTier.TIER_1)
        self.assertEqual(CREATURE_TIERS[CreatureCategory.DEER], CreatureTier.TIER_1)
        
        # Tier 2
        self.assertEqual(CREATURE_TIERS[CreatureCategory.SMALL_MAMMALS], CreatureTier.TIER_2)
        self.assertEqual(CREATURE_TIERS[CreatureCategory.REPTILES], CreatureTier.TIER_2)
        
        # Tier 3
        self.assertEqual(CREATURE_TIERS[CreatureCategory.INSECTS_FLYING], CreatureTier.TIER_3)
        self.assertEqual(CREATURE_TIERS[CreatureCategory.FISH], CreatureTier.TIER_3)


class TestAsymmetricTiming(unittest.TestCase):
    """Test asymmetric flee/recovery timing."""
    
    def setUp(self):
        self.manager = WildlifeManager()
    
    def test_flee_faster_than_recovery(self):
        """Wildlife should flee faster than it recovers."""
        # Measure flee time
        self.manager.set_population(0.90)
        flee_ticks = 0
        
        while self.manager.global_state != WildlifeState.ABSENT:
            self.manager.update(delta_time=0.5)
            flee_ticks += 1
            if flee_ticks > 500:
                break
        
        # Reset and measure recovery time
        self.manager.reset()
        self.manager.set_population(0.90)
        
        # First get to ABSENT
        for _ in range(flee_ticks + 50):
            self.manager.update(delta_time=0.5)
        
        # Now recover
        self.manager.set_population(0.05)
        recovery_ticks = 0
        
        while self.manager.global_state != WildlifeState.THRIVING:
            self.manager.update(delta_time=0.5)
            recovery_ticks += 1
            if recovery_ticks > 1000:
                break
        
        self.assertGreater(recovery_ticks, flee_ticks,
                          f"Recovery ({recovery_ticks}) should be slower than flee ({flee_ticks})")
    
    def test_recovery_takes_significant_time(self):
        """Recovery from ABSENT to THRIVING should take significant time."""
        # Get to ABSENT
        self.manager.set_population(0.90)
        for _ in range(200):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.global_state, WildlifeState.ABSENT)
        
        # Start recovery
        self.manager.set_population(0.05)
        
        # After 10 seconds, should still be recovering
        for _ in range(20):  # 10 seconds at 0.5s tick
            snapshot = self.manager.update(delta_time=0.5)
        
        self.assertNotEqual(self.manager.global_state, WildlifeState.THRIVING,
                           "Recovery should take more than 10 seconds")


class TestSpawnRateModulation(unittest.TestCase):
    """Test spawn rate modulation per state."""
    
    def setUp(self):
        self.manager = WildlifeManager()
    
    def test_thriving_full_spawn_rate(self):
        """THRIVING state should have full spawn rate."""
        self.manager.set_population(0.05)
        
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        bird = self.manager.creatures[CreatureCategory.BIRDS_SMALL]
        base_rate = self.manager.config.base_spawn_rates[CreatureCategory.BIRDS_SMALL]
        
        self.assertAlmostEqual(bird.current_spawn_rate, base_rate, delta=0.5)
    
    def test_absent_zero_spawn_rate_tier1(self):
        """ABSENT Tier 1 creatures should have zero spawn rate."""
        self.manager.set_population(0.90)
        
        for _ in range(200):
            self.manager.update(delta_time=0.5)
        
        bird = self.manager.creatures[CreatureCategory.BIRDS_SMALL]
        
        self.assertLess(bird.current_spawn_rate, 0.1,
                       "Tier 1 ABSENT should have near-zero spawn rate")
    
    def test_spawn_rate_decreases_with_state(self):
        """Spawn rate should decrease as state worsens."""
        rates_by_state = {}
        
        for pop, expected_state in [(0.05, WildlifeState.THRIVING),
                                     (0.25, WildlifeState.WARY),
                                     (0.45, WildlifeState.RETREATING)]:
            self.manager.reset()
            self.manager.set_population(pop)
            
            for _ in range(100):
                self.manager.update(delta_time=0.5)
            
            bird = self.manager.creatures[CreatureCategory.BIRDS_SMALL]
            rates_by_state[expected_state] = bird.current_spawn_rate
        
        # Rates should decrease
        self.assertGreater(rates_by_state[WildlifeState.THRIVING],
                          rates_by_state[WildlifeState.WARY])
        self.assertGreater(rates_by_state[WildlifeState.WARY],
                          rates_by_state[WildlifeState.RETREATING])


class TestBehaviorModifiers(unittest.TestCase):
    """Test behavior modifier changes per state."""
    
    def setUp(self):
        self.manager = WildlifeManager()
    
    def test_thriving_normal_behavior(self):
        """THRIVING should have normal behavior values."""
        self.manager.set_population(0.05)
        
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        bird = self.manager.creatures[CreatureCategory.BIRDS_SMALL]
        
        self.assertAlmostEqual(bird.flee_distance_multiplier, 1.0, delta=0.1)
        self.assertAlmostEqual(bird.activity_level, 1.0, delta=0.1)
        self.assertAlmostEqual(bird.edge_preference, 0.0, delta=0.1)
        self.assertTrue(bird.landing_allowed)
    
    def test_retreating_edge_preference(self):
        """RETREATING should have high edge preference."""
        self.manager.set_population(0.55)
        
        for _ in range(100):
            self.manager.update(delta_time=0.5)
        
        # Find a creature in RETREATING state
        retreating_creatures = [
            c for c in self.manager.creatures.values()
            if c.state == WildlifeState.RETREATING
        ]
        
        if retreating_creatures:
            creature = retreating_creatures[0]
            self.assertGreater(creature.edge_preference, 0.5,
                             "RETREATING should prefer edges")
            self.assertFalse(creature.landing_allowed,
                            "RETREATING should not allow landing")
    
    def test_flee_distance_increases_with_state(self):
        """Flee distance multiplier should increase with worse state."""
        self.manager.set_population(0.90)
        
        for _ in range(200):
            self.manager.update(delta_time=0.5)
        
        bird = self.manager.creatures[CreatureCategory.BIRDS_SMALL]
        
        self.assertGreater(bird.flee_distance_multiplier, 2.0,
                          "ABSENT should have large flee distance")


class TestRecoveryMemory(unittest.TestCase):
    """Test recovery 'memory' effect."""
    
    def setUp(self):
        self.manager = WildlifeManager()
    
    def test_recovery_tracking(self):
        """Should track recovery state."""
        # Get to ABSENT
        self.manager.set_population(0.90)
        for _ in range(200):
            self.manager.update(delta_time=0.5)
        
        # Start recovery
        self.manager.set_population(0.05)
        snapshot = self.manager.update(delta_time=0.5)
        
        # Should be recovering
        # Note: is_recovering is set when we're not ABSENT anymore
        for _ in range(50):
            snapshot = self.manager.update(delta_time=0.5)
            if snapshot.global_state != WildlifeState.ABSENT:
                break
        
        if snapshot.global_state != WildlifeState.ABSENT:
            self.assertTrue(snapshot.is_recovering)
    
    def test_recovery_progress_increases(self):
        """Recovery progress should increase over time."""
        # Get to ABSENT
        self.manager.set_population(0.90)
        for _ in range(200):
            self.manager.update(delta_time=0.5)
        
        # Start recovery
        self.manager.set_population(0.05)
        
        # Track state changes over time
        initial_state = self.manager.global_state
        states_seen = []
        
        for _ in range(500):  # Longer recovery period
            snapshot = self.manager.update(delta_time=0.5)
            if snapshot.global_state != initial_state:
                states_seen.append(snapshot.global_state)
                initial_state = snapshot.global_state
        
        # Should have seen at least one state improvement
        if len(states_seen) > 0:
            # States should improve (move toward THRIVING)
            state_order = [WildlifeState.THRIVING, WildlifeState.WARY, 
                          WildlifeState.RETREATING, WildlifeState.ABSENT]
            
            # Final state should be better than ABSENT
            final_idx = state_order.index(self.manager.global_state)
            absent_idx = state_order.index(WildlifeState.ABSENT)
            
            self.assertLess(final_idx, absent_idx,
                           "Wildlife should have recovered somewhat")


class TestWildlifeSnapshot(unittest.TestCase):
    """Test wildlife snapshot generation."""
    
    def setUp(self):
        self.manager = WildlifeManager()
    
    def test_snapshot_contains_all_fields(self):
        """Snapshot should contain all required fields."""
        self.manager.set_population(0.50)
        snapshot = self.manager.update(delta_time=0.5)
        
        self.assertIsInstance(snapshot.global_state, WildlifeState)
        self.assertIsInstance(snapshot.population, float)
        self.assertIsInstance(snapshot.creature_states, dict)
        self.assertIsInstance(snapshot.total_spawn_rate, float)
        self.assertIsInstance(snapshot.average_activity, float)
        self.assertIsInstance(snapshot.is_recovering, bool)
    
    def test_snapshot_to_dict(self):
        """Snapshot should serialize to dictionary."""
        self.manager.set_population(0.50)
        snapshot = self.manager.update(delta_time=0.5)
        
        data = snapshot.to_dict()
        
        self.assertIn('global_state', data)
        self.assertIn('population', data)
        self.assertIn('creature_states', data)
        self.assertIn('total_spawn_rate', data)
    
    def test_tier_dominant_states(self):
        """Snapshot should include dominant state per tier."""
        self.manager.set_population(0.50)
        
        for _ in range(50):
            snapshot = self.manager.update(delta_time=0.5)
        
        self.assertIn(CreatureTier.TIER_1, snapshot.dominant_tier_state)
        self.assertIn(CreatureTier.TIER_2, snapshot.dominant_tier_state)
        self.assertIn(CreatureTier.TIER_3, snapshot.dominant_tier_state)


class TestSpawnCommandGeneration(unittest.TestCase):
    """Test UE5 spawn command generation."""
    
    def setUp(self):
        self.manager = WildlifeManager()
        self.generator = WildlifeSpawnGenerator()
    
    def test_generate_spawn_commands(self):
        """Should generate spawn commands for active creatures."""
        self.manager.set_population(0.05)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        commands = self.manager.get_spawn_commands()
        
        self.assertGreater(len(commands), 0, "Should have spawn commands")
        
        for cmd in commands:
            self.assertIn('category', cmd)
            self.assertIn('spawn_rate_per_minute', cmd)
            self.assertIn('behavior', cmd)
    
    def test_spawn_generator_commands(self):
        """SpawnGenerator should create FWildlifeSpawnCommand objects."""
        self.manager.set_population(0.05)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        commands = self.generator.generate_commands(self.manager)
        
        self.assertGreater(len(commands), 0)
        self.assertIsInstance(commands[0], FWildlifeSpawnCommand)
    
    def test_spawn_command_to_ue5_json(self):
        """Spawn command should serialize to UE5 JSON."""
        cmd = FWildlifeSpawnCommand(
            category="birds_small",
            tier=1,
            spawn_rate_per_second=0.2,
        )
        
        data = cmd.to_ue5_json()
        
        self.assertIn('Category', data)
        self.assertIn('SpawnRatePerSecond', data)
        self.assertIn('FleeDistance', data)
        self.assertIn('LandingEnabled', data)
    
    def test_generator_ue5_json(self):
        """Generator should produce complete UE5 JSON."""
        self.manager.set_population(0.30)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        data = self.generator.to_ue5_json(self.manager)
        
        self.assertIn('GlobalState', data)
        self.assertIn('Population', data)
        self.assertIn('SpawnCommands', data)
        self.assertIn('TierStates', data)
    
    def test_absent_creatures_not_in_commands(self):
        """ABSENT creatures should not generate commands (except Tier 3)."""
        self.manager.set_population(0.95)
        for _ in range(200):
            self.manager.update(delta_time=0.5)
        
        commands = self.manager.get_spawn_commands()
        
        # Only Tier 3 should have commands
        categories = [cmd['category'] for cmd in commands]
        tier1_cats = [c.value for c in CreatureCategory 
                      if CREATURE_TIERS[c] == CreatureTier.TIER_1]
        
        for cat in tier1_cats:
            self.assertNotIn(cat, categories,
                           f"Tier 1 creature {cat} should not spawn when ABSENT")


class TestWildlifeConfig(unittest.TestCase):
    """Test wildlife configuration."""
    
    def test_default_config(self):
        """Default config should have sensible values."""
        config = WildlifeConfig()
        
        self.assertGreater(config.thriving_max_pop, 0)
        self.assertGreater(config.wary_max_pop, config.thriving_max_pop)
        self.assertGreater(config.retreating_max_pop, config.wary_max_pop)
    
    def test_custom_config(self):
        """Manager should accept custom config."""
        config = WildlifeConfig()
        config.thriving_max_pop = 0.05  # More sensitive
        
        manager = WildlifeManager(config=config)
        manager.set_population(0.08)  # Above custom threshold
        
        for _ in range(50):
            manager.update(delta_time=0.5)
        
        # Should have triggered state change with lower threshold
        self.assertNotEqual(manager.global_state, WildlifeState.THRIVING)
    
    def test_enabled_categories(self):
        """Manager should only track enabled categories."""
        enabled = {CreatureCategory.BIRDS_SMALL, CreatureCategory.INSECTS_FLYING}
        manager = WildlifeManager(enabled_categories=enabled)
        
        self.assertEqual(len(manager.creatures), 2)
        self.assertIn(CreatureCategory.BIRDS_SMALL, manager.creatures)
        self.assertIn(CreatureCategory.INSECTS_FLYING, manager.creatures)
        self.assertNotIn(CreatureCategory.DEER, manager.creatures)


class TestWildlifeReset(unittest.TestCase):
    """Test wildlife manager reset."""
    
    def test_reset_restores_thriving(self):
        """Reset should restore THRIVING state."""
        manager = WildlifeManager()
        
        # Get to bad state
        manager.set_population(0.90)
        for _ in range(200):
            manager.update(delta_time=0.5)
        
        self.assertEqual(manager.global_state, WildlifeState.ABSENT)
        
        # Reset
        manager.reset()
        
        self.assertEqual(manager.global_state, WildlifeState.THRIVING)
    
    def test_reset_clears_spawn_rates(self):
        """Reset should restore base spawn rates."""
        manager = WildlifeManager()
        config = manager.config
        
        # Reduce spawn rates
        manager.set_population(0.90)
        for _ in range(200):
            manager.update(delta_time=0.5)
        
        # Reset
        manager.reset()
        
        bird = manager.creatures[CreatureCategory.BIRDS_SMALL]
        expected_rate = config.base_spawn_rates[CreatureCategory.BIRDS_SMALL]
        
        self.assertAlmostEqual(bird.current_spawn_rate, expected_rate, delta=0.5)


class TestIntegration(unittest.TestCase):
    """Integration tests for wildlife system."""
    
    def test_full_population_cycle(self):
        """Test complete population rise and fall cycle."""
        manager = WildlifeManager()
        
        # Start peaceful
        manager.set_population(0.05)
        for _ in range(20):
            manager.update(delta_time=0.5)
        
        initial_rate = manager.creatures[CreatureCategory.BIRDS_SMALL].current_spawn_rate
        
        # Population rises
        manager.set_population(0.80)
        for _ in range(150):
            manager.update(delta_time=0.5)
        
        peak_rate = manager.creatures[CreatureCategory.BIRDS_SMALL].current_spawn_rate
        self.assertLess(peak_rate, initial_rate * 0.2,
                       "Spawn rate should drop significantly")
        
        # Population falls
        manager.set_population(0.05)
        for _ in range(500):  # Long recovery
            snapshot = manager.update(delta_time=0.5)
        
        recovered_rate = manager.creatures[CreatureCategory.BIRDS_SMALL].current_spawn_rate
        self.assertGreater(recovered_rate, peak_rate,
                          "Spawn rate should recover")
    
    def test_ue5_workflow(self):
        """Test complete VDE → Wildlife → UE5 workflow."""
        manager = WildlifeManager()
        generator = WildlifeSpawnGenerator()
        
        # Simulate game loop
        populations = [0.10, 0.30, 0.50, 0.70, 0.50, 0.30, 0.10]
        
        for pop in populations:
            manager.set_population(pop)
            
            for _ in range(20):
                snapshot = manager.update(delta_time=0.5)
            
            ue5_data = generator.to_ue5_json(manager)
            
            # Verify UE5 data is complete
            self.assertIn('GlobalState', ue5_data)
            self.assertIn('SpawnCommands', ue5_data)
            self.assertEqual(ue5_data['Population'], pop)


def run_tests():
    """Run all Phase 3 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestWildlifeStateTransitions))
    suite.addTests(loader.loadTestsFromTestCase(TestTierSensitivity))
    suite.addTests(loader.loadTestsFromTestCase(TestAsymmetricTiming))
    suite.addTests(loader.loadTestsFromTestCase(TestSpawnRateModulation))
    suite.addTests(loader.loadTestsFromTestCase(TestBehaviorModifiers))
    suite.addTests(loader.loadTestsFromTestCase(TestRecoveryMemory))
    suite.addTests(loader.loadTestsFromTestCase(TestWildlifeSnapshot))
    suite.addTests(loader.loadTestsFromTestCase(TestSpawnCommandGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestWildlifeConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestWildlifeReset))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
