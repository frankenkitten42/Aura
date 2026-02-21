"""
VDE Phase 4 Tests: NPC Modulation System

Tests:
- Comfort level transitions
- Per-type behavior profiles
- Idle behavior repertoire
- Repositioning logic
- Edge-seeking behavior
- Interaction radius changes
- NPC activation/deactivation
- UE5 command generation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from vde.npc_behavior import (
    NPCManager, NPCConfig, NPCSnapshot, NPCState,
    NPCType, ComfortLevel, IdleBehavior, RepositionReason,
    NPCBehaviorProfile, NPCCommandGenerator, FNPCBehaviorCommand,
    DEFAULT_PROFILES,
)


class TestComfortLevels(unittest.TestCase):
    """Test comfort level transitions based on population."""
    
    def setUp(self):
        self.manager = NPCManager()
        self.manager.register_npc("test_npc", NPCType.AMBIENT)
    
    def test_initial_comfort_relaxed(self):
        """NPCs should start at RELAXED comfort."""
        npc = self.manager.npcs["test_npc"]
        self.assertEqual(npc.comfort_level, ComfortLevel.RELAXED)
    
    def test_low_pop_relaxed(self):
        """Low population should maintain RELAXED comfort."""
        self.manager.set_population(0.10)
        
        for _ in range(20):
            snapshot = self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.global_comfort, ComfortLevel.RELAXED)
    
    def test_medium_pop_comfortable(self):
        """Medium population should trigger COMFORTABLE."""
        self.manager.set_population(0.30)
        
        for _ in range(20):
            snapshot = self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.global_comfort, ComfortLevel.COMFORTABLE)
    
    def test_high_pop_stressed(self):
        """High population should trigger STRESSED."""
        self.manager.set_population(0.70)
        
        for _ in range(20):
            snapshot = self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.global_comfort, ComfortLevel.STRESSED)
    
    def test_very_high_pop_overwhelmed(self):
        """Very high population should trigger OVERWHELMED."""
        self.manager.set_population(0.90)
        
        for _ in range(20):
            snapshot = self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.global_comfort, ComfortLevel.OVERWHELMED)
    
    def test_comfort_value_decreases(self):
        """Comfort value (0-1) should decrease with population."""
        self.manager.set_population(0.05)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        low_comfort = self.manager.npcs["test_npc"].comfort_value
        
        self.manager.set_population(0.85)
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        high_comfort = self.manager.npcs["test_npc"].comfort_value
        
        self.assertGreater(low_comfort, high_comfort)


class TestNPCTypes(unittest.TestCase):
    """Test different NPC type behaviors."""
    
    def setUp(self):
        self.manager = NPCManager()
    
    def test_vendor_profile_exists(self):
        """Vendor profile should exist with correct settings."""
        profile = DEFAULT_PROFILES[NPCType.VENDOR]
        
        self.assertTrue(profile.has_station)
        self.assertLess(profile.crowd_sensitivity, 1.0)  # Vendors tolerate crowds
    
    def test_guard_less_sensitive(self):
        """Guards should be less sensitive to crowds."""
        profile = DEFAULT_PROFILES[NPCType.GUARD]
        
        self.assertLess(profile.crowd_sensitivity, 1.0)
    
    def test_noble_more_sensitive(self):
        """Nobles should be more sensitive to crowds."""
        profile = DEFAULT_PROFILES[NPCType.NOBLE]
        
        self.assertGreater(profile.crowd_sensitivity, 1.0)
    
    def test_different_types_different_comfort(self):
        """Different NPC types should have different comfort at same population."""
        self.manager.register_npc("guard", NPCType.GUARD)
        self.manager.register_npc("noble", NPCType.NOBLE)
        
        self.manager.set_population(0.50)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        guard = self.manager.npcs["guard"]
        noble = self.manager.npcs["noble"]
        
        # Noble should be less comfortable than guard at same population
        self.assertGreater(guard.comfort_value, noble.comfort_value)


class TestIdleBehaviors(unittest.TestCase):
    """Test idle behavior repertoire management."""
    
    def setUp(self):
        self.manager = NPCManager()
        self.manager.register_npc("ambient", NPCType.AMBIENT)
    
    def test_relaxed_full_repertoire(self):
        """RELAXED should have full idle repertoire."""
        profile = DEFAULT_PROFILES[NPCType.AMBIENT]
        relaxed_behaviors = profile.idle_behaviors[ComfortLevel.RELAXED]
        
        # Should include sitting, chatting, etc.
        self.assertTrue(IdleBehavior.SIT in relaxed_behaviors)
        self.assertTrue(IdleBehavior.CHAT in relaxed_behaviors)
        self.assertTrue(IdleBehavior.LEAN in relaxed_behaviors)
    
    def test_overwhelmed_minimal_repertoire(self):
        """OVERWHELMED should have minimal idle repertoire."""
        profile = DEFAULT_PROFILES[NPCType.AMBIENT]
        overwhelmed_behaviors = profile.idle_behaviors[ComfortLevel.OVERWHELMED]
        
        # Should only have basic standing
        self.assertTrue(IdleBehavior.STAND in overwhelmed_behaviors or 
                       IdleBehavior.FIDGET in overwhelmed_behaviors)
        self.assertFalse(IdleBehavior.SIT in overwhelmed_behaviors)
        self.assertFalse(IdleBehavior.CHAT in overwhelmed_behaviors)
    
    def test_behavior_changes_with_comfort(self):
        """Current idle should change as comfort changes."""
        self.manager.set_population(0.05)
        
        # Force behavior selection by running many updates
        for _ in range(50):
            self.manager.update(delta_time=1.0)
        
        npc = self.manager.npcs["ambient"]
        relaxed_idle = npc.current_idle
        
        # Now stress the NPC
        self.manager.set_population(0.90)
        for _ in range(50):
            self.manager.update(delta_time=1.0)
        
        # Idle repertoire should be more restricted
        stressed_behaviors = npc.profile.idle_behaviors.get(
            npc.comfort_level, IdleBehavior.STAND
        )
        # The available behaviors at stressed should be fewer
        relaxed_behaviors = npc.profile.idle_behaviors.get(
            ComfortLevel.RELAXED, IdleBehavior.STAND
        )
        
        self.assertLess(bin(stressed_behaviors.value).count('1'),
                       bin(relaxed_behaviors.value).count('1'))


class TestRepositioning(unittest.TestCase):
    """Test NPC repositioning behavior."""
    
    def setUp(self):
        self.manager = NPCManager()
        self.manager.register_npc("test", NPCType.AMBIENT)
    
    def test_reposition_interval_varies(self):
        """Reposition interval should vary with comfort."""
        # Relaxed - longer interval
        self.manager.set_population(0.05)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        relaxed_interval = self.manager.npcs["test"].reposition_interval
        
        # Stressed - shorter interval
        self.manager.set_population(0.85)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        stressed_interval = self.manager.npcs["test"].reposition_interval
        
        self.assertGreater(relaxed_interval, stressed_interval)
    
    def test_wants_reposition_after_interval(self):
        """NPC should want to reposition after interval passes."""
        self.manager.set_population(0.50)
        
        # Get the interval
        for _ in range(10):
            self.manager.update(delta_time=0.5)
        interval = self.manager.npcs["test"].reposition_interval
        
        # Run until past interval
        total_time = 0
        while total_time < interval + 1:
            self.manager.update(delta_time=0.5)
            total_time += 0.5
        
        self.assertTrue(self.manager.npcs["test"].wants_to_reposition)
    
    def test_reposition_reason_crowding(self):
        """High population should cause CROWDING reposition reason."""
        self.manager.set_population(0.85)
        
        # Run until reposition wanted
        for _ in range(100):
            self.manager.update(delta_time=0.5)
            if self.manager.npcs["test"].wants_to_reposition:
                break
        
        npc = self.manager.npcs["test"]
        if npc.wants_to_reposition:
            self.assertEqual(npc.reposition_reason, RepositionReason.CROWDING)
    
    def test_acknowledge_reposition(self):
        """Acknowledging reposition should reset the state."""
        self.manager.set_population(0.50)
        
        # Trigger reposition
        for _ in range(100):
            self.manager.update(delta_time=0.5)
        
        # Acknowledge
        self.manager.acknowledge_reposition("test")
        
        npc = self.manager.npcs["test"]
        self.assertFalse(npc.wants_to_reposition)
        self.assertEqual(npc.time_since_reposition, 0.0)


class TestEdgePreference(unittest.TestCase):
    """Test edge-seeking behavior."""
    
    def setUp(self):
        self.manager = NPCManager()
        self.manager.register_npc("test", NPCType.AMBIENT)
    
    def test_low_edge_preference_when_relaxed(self):
        """Edge preference should be low when relaxed."""
        self.manager.set_population(0.05)
        
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        npc = self.manager.npcs["test"]
        self.assertLess(npc.edge_preference, 0.2)
    
    def test_high_edge_preference_when_stressed(self):
        """Edge preference should increase when stressed."""
        self.manager.set_population(0.85)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        npc = self.manager.npcs["test"]
        self.assertGreater(npc.edge_preference, 0.4)
    
    def test_edge_preference_increases_with_pop(self):
        """Edge preference should increase with population."""
        edge_prefs = []
        
        for pop in [0.10, 0.30, 0.50, 0.70, 0.90]:
            self.manager.reset()
            self.manager.set_population(pop)
            
            for _ in range(30):
                self.manager.update(delta_time=0.5)
            
            edge_prefs.append(self.manager.npcs["test"].edge_preference)
        
        # Should be generally increasing
        self.assertLess(edge_prefs[0], edge_prefs[-1])


class TestInteractionRadius(unittest.TestCase):
    """Test interaction radius changes."""
    
    def setUp(self):
        self.manager = NPCManager()
        self.manager.register_npc("test", NPCType.AMBIENT)
    
    def test_base_radius_when_relaxed(self):
        """Interaction radius should be near base when relaxed."""
        self.manager.set_population(0.05)
        
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        npc = self.manager.npcs["test"]
        base = npc.profile.base_interaction_radius
        
        self.assertAlmostEqual(npc.interaction_radius, base, delta=base * 0.1)
    
    def test_reduced_radius_when_stressed(self):
        """Interaction radius should shrink when stressed."""
        # Get relaxed radius
        self.manager.set_population(0.05)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        relaxed_radius = self.manager.npcs["test"].interaction_radius
        
        # Get stressed radius
        self.manager.set_population(0.85)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        stressed_radius = self.manager.npcs["test"].interaction_radius
        
        self.assertLess(stressed_radius, relaxed_radius)


class TestNPCActivation(unittest.TestCase):
    """Test NPC activation/deactivation."""
    
    def setUp(self):
        self.manager = NPCManager()
    
    def test_npcs_can_leave(self):
        """NPCs with can_leave=True should deactivate when overwhelmed."""
        self.manager.register_npc("noble", NPCType.NOBLE)
        
        self.manager.set_population(0.95)
        
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        noble = self.manager.npcs["noble"]
        # Nobles can leave when overwhelmed
        if noble.comfort_level == ComfortLevel.OVERWHELMED:
            profile = DEFAULT_PROFILES[NPCType.NOBLE]
            behaviors = profile.idle_behaviors.get(ComfortLevel.OVERWHELMED, IdleBehavior.STAND)
            if behaviors == IdleBehavior.NONE:
                self.assertFalse(noble.is_active)
    
    def test_vendors_stay(self):
        """Vendors should not leave (has_station=True)."""
        self.manager.register_npc("vendor", NPCType.VENDOR)
        
        self.manager.set_population(0.95)
        
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        vendor = self.manager.npcs["vendor"]
        self.assertTrue(vendor.is_active)
    
    def test_guards_stay(self):
        """Guards should not leave."""
        self.manager.register_npc("guard", NPCType.GUARD)
        
        self.manager.set_population(0.95)
        
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        guard = self.manager.npcs["guard"]
        self.assertTrue(guard.is_active)


class TestNPCSnapshot(unittest.TestCase):
    """Test NPC snapshot generation."""
    
    def setUp(self):
        self.manager = NPCManager()
        self.manager.register_npc("vendor", NPCType.VENDOR)
        self.manager.register_npc("guard", NPCType.GUARD)
        self.manager.register_npc("ambient", NPCType.AMBIENT)
    
    def test_snapshot_contains_all_fields(self):
        """Snapshot should contain all required fields."""
        self.manager.set_population(0.50)
        snapshot = self.manager.update(delta_time=0.5)
        
        self.assertIsInstance(snapshot.global_comfort, ComfortLevel)
        self.assertIsInstance(snapshot.population, float)
        self.assertIsInstance(snapshot.npc_states, dict)
        self.assertGreater(snapshot.active_count, 0)
    
    def test_snapshot_to_dict(self):
        """Snapshot should serialize to dictionary."""
        self.manager.set_population(0.50)
        snapshot = self.manager.update(delta_time=0.5)
        
        data = snapshot.to_dict()
        
        self.assertIn('global_comfort', data)
        self.assertIn('active_count', data)
        self.assertIn('comfort_distribution', data)
        self.assertIn('npcs', data)
    
    def test_comfort_distribution(self):
        """Snapshot should track comfort distribution."""
        self.manager.set_population(0.50)
        
        for _ in range(30):
            snapshot = self.manager.update(delta_time=0.5)
        
        # Should have distribution counts
        total = sum(snapshot.comfort_distribution.values())
        self.assertEqual(total, snapshot.active_count)


class TestCommandGeneration(unittest.TestCase):
    """Test UE5 command generation."""
    
    def setUp(self):
        self.manager = NPCManager()
        self.manager.register_npc("vendor", NPCType.VENDOR)
        self.manager.register_npc("guard", NPCType.GUARD)
        self.generator = NPCCommandGenerator()
    
    def test_generate_commands(self):
        """Should generate commands for all NPCs."""
        self.manager.set_population(0.50)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        commands = self.manager.get_behavior_commands()
        
        self.assertEqual(len(commands), 2)
        
        for cmd in commands:
            self.assertIn('npc_id', cmd)
            self.assertIn('comfort_level', cmd)
            self.assertIn('current_idle', cmd)
    
    def test_generator_commands(self):
        """Generator should create FNPCBehaviorCommand objects."""
        self.manager.set_population(0.50)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        commands = self.generator.generate_commands(self.manager)
        
        self.assertGreater(len(commands), 0)
        self.assertIsInstance(commands[0], FNPCBehaviorCommand)
    
    def test_command_to_ue5_json(self):
        """Command should serialize to UE5 JSON."""
        cmd = FNPCBehaviorCommand(
            npc_id="test_npc",
            npc_type="vendor",
            is_active=True,
        )
        
        data = cmd.to_ue5_json()
        
        self.assertIn('NPCID', data)
        self.assertIn('NPCType', data)
        self.assertIn('ComfortLevel', data)
        self.assertIn('IdleBehaviorsMask', data)
    
    def test_generator_ue5_json(self):
        """Generator should produce complete UE5 JSON."""
        self.manager.set_population(0.50)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        data = self.generator.to_ue5_json(self.manager)
        
        self.assertIn('Population', data)
        self.assertIn('GlobalComfort', data)
        self.assertIn('NPCCommands', data)
        self.assertIn('Summary', data)


class TestNPCConfig(unittest.TestCase):
    """Test NPC configuration."""
    
    def test_default_config(self):
        """Default config should have sensible values."""
        config = NPCConfig()
        
        self.assertGreater(config.relaxed_max_pop, 0)
        self.assertGreater(config.comfortable_max_pop, config.relaxed_max_pop)
        self.assertGreater(config.base_reposition_interval, config.min_reposition_interval)
    
    def test_custom_config(self):
        """Manager should accept custom config."""
        config = NPCConfig()
        config.relaxed_max_pop = 0.10  # More sensitive
        
        manager = NPCManager(config=config)
        manager.register_npc("test", NPCType.AMBIENT)
        manager.set_population(0.15)  # Above custom threshold
        
        for _ in range(20):
            manager.update(delta_time=0.5)
        
        self.assertNotEqual(manager.global_comfort, ComfortLevel.RELAXED)


class TestNPCReset(unittest.TestCase):
    """Test NPC manager reset."""
    
    def setUp(self):
        self.manager = NPCManager()
        self.manager.register_npc("test", NPCType.AMBIENT)
    
    def test_reset_restores_relaxed(self):
        """Reset should restore RELAXED comfort."""
        self.manager.set_population(0.90)
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        self.manager.reset()
        
        self.assertEqual(self.manager.global_comfort, ComfortLevel.RELAXED)
        self.assertEqual(self.manager.npcs["test"].comfort_level, ComfortLevel.RELAXED)
    
    def test_reset_restores_activity(self):
        """Reset should restore NPC activity."""
        self.manager.reset()
        
        npc = self.manager.npcs["test"]
        self.assertTrue(npc.is_active)
        self.assertAlmostEqual(npc.comfort_value, 1.0, delta=0.1)


class TestIntegration(unittest.TestCase):
    """Integration tests for NPC system."""
    
    def test_full_population_cycle(self):
        """Test complete population rise and fall cycle."""
        manager = NPCManager()
        manager.register_npc("vendor", NPCType.VENDOR)
        manager.register_npc("guard", NPCType.GUARD)
        manager.register_npc("noble", NPCType.NOBLE)
        manager.register_npc("ambient", NPCType.AMBIENT)
        
        # Start peaceful
        manager.set_population(0.05)
        for _ in range(20):
            manager.update(delta_time=0.5)
        
        initial_comforts = {
            npc_id: npc.comfort_value 
            for npc_id, npc in manager.npcs.items()
        }
        
        # Population rises
        manager.set_population(0.85)
        for _ in range(50):
            manager.update(delta_time=0.5)
        
        # All should be less comfortable
        for npc_id, npc in manager.npcs.items():
            self.assertLess(npc.comfort_value, initial_comforts[npc_id],
                          f"{npc_id} should be less comfortable")
        
        # Population falls
        manager.set_population(0.05)
        for _ in range(50):
            manager.update(delta_time=0.5)
        
        # Should recover
        for npc_id, npc in manager.npcs.items():
            if npc.is_active:
                self.assertGreater(npc.comfort_value, 0.5,
                                  f"{npc_id} should recover comfort")
    
    def test_ue5_workflow(self):
        """Test complete NPC → UE5 workflow."""
        manager = NPCManager()
        generator = NPCCommandGenerator()
        
        manager.register_npc("vendor_01", NPCType.VENDOR)
        manager.register_npc("guard_01", NPCType.GUARD)
        manager.register_npc("ambient_01", NPCType.AMBIENT)
        
        populations = [0.10, 0.30, 0.50, 0.70, 0.50, 0.30, 0.10]
        
        for pop in populations:
            manager.set_population(pop)
            
            for _ in range(20):
                snapshot = manager.update(delta_time=0.5)
            
            ue5_data = generator.to_ue5_json(manager)
            
            # Verify UE5 data
            self.assertIn('GlobalComfort', ue5_data)
            self.assertIn('NPCCommands', ue5_data)
            self.assertEqual(len(ue5_data['NPCCommands']), 3)


def run_tests():
    """Run all Phase 4 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestComfortLevels))
    suite.addTests(loader.loadTestsFromTestCase(TestNPCTypes))
    suite.addTests(loader.loadTestsFromTestCase(TestIdleBehaviors))
    suite.addTests(loader.loadTestsFromTestCase(TestRepositioning))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgePreference))
    suite.addTests(loader.loadTestsFromTestCase(TestInteractionRadius))
    suite.addTests(loader.loadTestsFromTestCase(TestNPCActivation))
    suite.addTests(loader.loadTestsFromTestCase(TestNPCSnapshot))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestNPCConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestNPCReset))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
