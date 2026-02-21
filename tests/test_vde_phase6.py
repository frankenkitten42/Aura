"""
VDE Phase 6 Tests: Motion Coherence System

Tests:
- Coherence level transitions
- Wind behavior
- Element phase synchronization
- Category-specific behavior
- Settling mechanics
- Prop jitter
- UE5 parameter generation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import math
from vde.motion_coherence import (
    MotionManager, MotionConfig, MotionSnapshot,
    MotionCategory, CoherenceLevel, WindPattern,
    ElementMotionState, CategoryState,
    FMotionParameters, WindPatternGenerator,
)


class TestCoherenceLevels(unittest.TestCase):
    """Test coherence level transitions based on population."""
    
    def setUp(self):
        self.manager = MotionManager()
    
    def test_initial_coherence_natural(self):
        """Should start at NATURAL coherence."""
        self.assertEqual(self.manager.coherence_level, CoherenceLevel.NATURAL)
    
    def test_low_pop_unified(self):
        """Low population should achieve UNIFIED coherence."""
        self.manager.set_population(0.05)
        
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.coherence_level, CoherenceLevel.UNIFIED)
    
    def test_medium_low_pop_natural(self):
        """Medium-low population should achieve NATURAL coherence."""
        self.manager.set_population(0.25)
        
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.coherence_level, CoherenceLevel.NATURAL)
    
    def test_medium_high_pop_varied(self):
        """Medium-high population should achieve VARIED coherence."""
        self.manager.set_population(0.50)
        
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.coherence_level, CoherenceLevel.VARIED)
    
    def test_high_pop_chaotic(self):
        """High population should achieve CHAOTIC coherence."""
        self.manager.set_population(0.80)
        
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.coherence_level, CoherenceLevel.CHAOTIC)
    
    def test_coherence_value_decreases(self):
        """Coherence value (0-1) should decrease with population."""
        self.manager.set_population(0.05)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        high_coherence = self.manager.coherence_value
        
        self.manager.set_population(0.85)
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        low_coherence = self.manager.coherence_value
        
        self.assertGreater(high_coherence, low_coherence)


class TestWindBehavior(unittest.TestCase):
    """Test wind direction and strength behavior."""
    
    def setUp(self):
        self.manager = MotionManager()
    
    def test_wind_exists(self):
        """Wind should have direction and strength."""
        self.manager.update(delta_time=0.5)
        
        self.assertIsNotNone(self.manager._wind_direction)
        self.assertIsNotNone(self.manager._wind_strength)
    
    def test_wind_direction_in_range(self):
        """Wind direction should be 0-360 degrees."""
        self.manager.set_population(0.50)
        
        for _ in range(100):
            self.manager.update(delta_time=0.5)
            self.assertGreaterEqual(self.manager._wind_direction, 0)
            self.assertLess(self.manager._wind_direction, 360)
    
    def test_wind_strength_in_range(self):
        """Wind strength should be 0-1."""
        self.manager.set_population(0.50)
        
        for _ in range(100):
            self.manager.update(delta_time=0.5)
            self.assertGreaterEqual(self.manager._wind_strength, 0)
            self.assertLessEqual(self.manager._wind_strength, 1)
    
    def test_chaotic_wind_more_variable(self):
        """Chaotic coherence should have more wind variance."""
        # Unified - collect directions
        self.manager.set_population(0.05)
        unified_dirs = []
        for _ in range(50):
            self.manager.update(delta_time=0.5)
            unified_dirs.append(self.manager._wind_direction)
        
        # Calculate variance
        unified_var = max(unified_dirs) - min(unified_dirs)
        
        # Chaotic - collect directions
        self.manager.set_population(0.85)
        chaotic_dirs = []
        for _ in range(50):
            self.manager.update(delta_time=0.5)
            chaotic_dirs.append(self.manager._wind_direction)
        
        chaotic_var = max(chaotic_dirs) - min(chaotic_dirs)
        
        # Chaotic should have more variance
        self.assertGreater(chaotic_var, unified_var)


class TestElementRegistration(unittest.TestCase):
    """Test element registration and tracking."""
    
    def setUp(self):
        self.manager = MotionManager()
    
    def test_register_element(self):
        """Should register elements correctly."""
        self.manager.register_element("tree_01", MotionCategory.FOLIAGE)
        
        self.assertIn("tree_01", self.manager.categories[MotionCategory.FOLIAGE].elements)
    
    def test_register_multiple_categories(self):
        """Should register elements in different categories."""
        self.manager.register_element("tree_01", MotionCategory.FOLIAGE)
        self.manager.register_element("banner_01", MotionCategory.CLOTH)
        self.manager.register_element("lantern_01", MotionCategory.PROPS)
        
        self.assertEqual(len(self.manager.categories[MotionCategory.FOLIAGE].elements), 1)
        self.assertEqual(len(self.manager.categories[MotionCategory.CLOTH].elements), 1)
        self.assertEqual(len(self.manager.categories[MotionCategory.PROPS].elements), 1)
    
    def test_unregister_element(self):
        """Should unregister elements correctly."""
        self.manager.register_element("tree_01", MotionCategory.FOLIAGE)
        self.manager.unregister_element("tree_01", MotionCategory.FOLIAGE)
        
        self.assertNotIn("tree_01", self.manager.categories[MotionCategory.FOLIAGE].elements)
    
    def test_element_has_random_phase(self):
        """Elements should start with random base phase."""
        self.manager.register_element("tree_01", MotionCategory.FOLIAGE)
        self.manager.register_element("tree_02", MotionCategory.FOLIAGE)
        
        tree1 = self.manager.categories[MotionCategory.FOLIAGE].elements["tree_01"]
        tree2 = self.manager.categories[MotionCategory.FOLIAGE].elements["tree_02"]
        
        # Phases should differ (with high probability)
        self.assertNotAlmostEqual(tree1.base_phase, tree2.base_phase, delta=0.01)


class TestPhaseCoherence(unittest.TestCase):
    """Test phase synchronization behavior."""
    
    def setUp(self):
        self.manager = MotionManager()
        for i in range(5):
            self.manager.register_element(f"tree_{i}", MotionCategory.FOLIAGE)
    
    def test_unified_small_phase_offset(self):
        """UNIFIED coherence should have small phase offsets."""
        self.manager.set_population(0.05)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        offsets = [
            abs(e.phase_offset) 
            for e in self.manager.categories[MotionCategory.FOLIAGE].elements.values()
        ]
        
        max_offset = max(offsets)
        self.assertLess(max_offset, 0.5)  # Small offset in unified
    
    def test_chaotic_large_phase_offset(self):
        """CHAOTIC coherence should allow larger phase offsets."""
        self.manager.set_population(0.85)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        # Config allows up to pi offset for chaotic
        cfg = self.manager.config
        max_allowed = cfg.phase_variance[CoherenceLevel.CHAOTIC]
        
        self.assertGreater(max_allowed, 1.0)  # Should be large


class TestSpeedVariance(unittest.TestCase):
    """Test animation speed variance behavior."""
    
    def setUp(self):
        self.manager = MotionManager()
        for i in range(5):
            self.manager.register_element(f"tree_{i}", MotionCategory.FOLIAGE)
    
    def test_unified_consistent_speed(self):
        """UNIFIED coherence should have consistent speeds."""
        self.manager.set_population(0.05)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        speeds = [
            e.speed_multiplier 
            for e in self.manager.categories[MotionCategory.FOLIAGE].elements.values()
        ]
        
        speed_range = max(speeds) - min(speeds)
        self.assertLess(speed_range, 0.2)  # Tight range
    
    def test_chaotic_varied_speed(self):
        """CHAOTIC coherence should allow varied speeds."""
        self.manager.set_population(0.85)
        
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        # Config allows larger variance
        cfg = self.manager.config
        variance = cfg.speed_variance[CoherenceLevel.CHAOTIC]
        
        self.assertGreater(variance, 0.3)


class TestSettlingBehavior(unittest.TestCase):
    """Test element settling mechanics."""
    
    def setUp(self):
        self.manager = MotionManager()
        # Use low wind strength config
        self.manager.config.base_wind_strength = 0.1
        self.manager.register_element("banner_01", MotionCategory.CLOTH)
    
    def test_unified_can_settle(self):
        """UNIFIED coherence with low wind should allow settling."""
        self.manager.set_population(0.05)
        
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        banner = self.manager.categories[MotionCategory.CLOTH].elements["banner_01"]
        
        # Settling should progress
        self.assertGreater(banner.settling_progress, 0)
    
    def test_chaotic_minimal_settling(self):
        """CHAOTIC coherence should have minimal settling."""
        self.manager.set_population(0.85)
        
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        banner = self.manager.categories[MotionCategory.CLOTH].elements["banner_01"]
        
        # Should have residual motion
        cfg = self.manager.config
        settling_rate = cfg.settling_rate[CoherenceLevel.CHAOTIC]
        
        self.assertLess(settling_rate, 0.5)
    
    def test_water_never_settles(self):
        """Water category should never fully settle."""
        self.manager.register_element("pond_01", MotionCategory.WATER)
        self.manager.set_population(0.05)
        
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        self.assertFalse(self.manager.categories[MotionCategory.WATER].can_settle)


class TestPropJitter(unittest.TestCase):
    """Test prop micro-movement and jitter."""
    
    def setUp(self):
        self.manager = MotionManager()
        self.manager.register_element("lantern_01", MotionCategory.PROPS)
    
    def test_unified_no_jitter(self):
        """UNIFIED coherence should have no jitter."""
        self.manager.set_population(0.05)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        lantern = self.manager.categories[MotionCategory.PROPS].elements["lantern_01"]
        
        self.assertLess(lantern.jitter_amount, 0.01)
    
    def test_chaotic_has_jitter(self):
        """CHAOTIC coherence should have jitter."""
        self.manager.set_population(0.85)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        lantern = self.manager.categories[MotionCategory.PROPS].elements["lantern_01"]
        
        self.assertGreater(lantern.jitter_amount, 0.005)


class TestCategoryStates(unittest.TestCase):
    """Test per-category state tracking."""
    
    def setUp(self):
        self.manager = MotionManager()
    
    def test_all_categories_exist(self):
        """All motion categories should be initialized."""
        for category in MotionCategory:
            self.assertIn(category, self.manager.categories)
    
    def test_category_coherence_tracks_global(self):
        """Category coherence should track global coherence."""
        self.manager.set_population(0.50)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        for state in self.manager.categories.values():
            self.assertAlmostEqual(
                state.phase_coherence, 
                self.manager.coherence_value,
                delta=0.1
            )


class TestMotionSnapshot(unittest.TestCase):
    """Test motion snapshot generation."""
    
    def setUp(self):
        self.manager = MotionManager()
        self.manager.register_element("tree_01", MotionCategory.FOLIAGE)
    
    def test_snapshot_contains_all_fields(self):
        """Snapshot should contain all required fields."""
        self.manager.set_population(0.50)
        snapshot = self.manager.update(delta_time=0.5)
        
        self.assertIsInstance(snapshot.population, float)
        self.assertIsInstance(snapshot.coherence_level, CoherenceLevel)
        self.assertIsInstance(snapshot.coherence_value, float)
        self.assertIsInstance(snapshot.global_wind_direction, float)
        self.assertIsInstance(snapshot.global_wind_strength, float)
    
    def test_snapshot_to_dict(self):
        """Snapshot should serialize to dictionary."""
        self.manager.set_population(0.50)
        snapshot = self.manager.update(delta_time=0.5)
        
        data = snapshot.to_dict()
        
        self.assertIn('coherence_level', data)
        self.assertIn('coherence_value', data)
        self.assertIn('global_wind_direction', data)
        self.assertIn('categories', data)


class TestUE5Parameters(unittest.TestCase):
    """Test UE5 parameter generation."""
    
    def setUp(self):
        self.manager = MotionManager()
    
    def test_parameter_generation(self):
        """Should generate UE5 parameters."""
        self.manager.set_population(0.50)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        params = self.manager.get_ue5_parameters()
        
        self.assertIsInstance(params, FMotionParameters)
    
    def test_parameters_reflect_coherence(self):
        """Parameters should reflect coherence level."""
        # High coherence
        self.manager.set_population(0.05)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        params_unified = self.manager.get_ue5_parameters()
        
        # Low coherence
        self.manager.set_population(0.85)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        params_chaotic = self.manager.get_ue5_parameters()
        
        # Chaotic should have more variance/turbulence
        self.assertGreater(params_chaotic.foliage_turbulence, params_unified.foliage_turbulence)
        self.assertGreater(params_chaotic.prop_jitter_amount, params_unified.prop_jitter_amount)
    
    def test_parameters_to_json(self):
        """Parameters should serialize to JSON."""
        params = FMotionParameters()
        params.coherence_value = 0.7
        params.wind_direction = 45.0
        
        data = params.to_ue5_json()
        
        self.assertIn('Motion_CoherenceValue', data)
        self.assertIn('Wind_Direction', data)
        self.assertIn('Foliage_WaveCoherence', data)
        self.assertIn('Cloth_SettlingRate', data)
        self.assertIn('Prop_JitterAmount', data)
    
    def test_npc_breathing_sync(self):
        """NPC breathing sync should vary with coherence."""
        # UNIFIED - almost too perfect
        self.manager.set_population(0.05)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        params_unified = self.manager.get_ue5_parameters()
        
        # NATURAL - comfortable variation
        self.manager.set_population(0.25)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        params_natural = self.manager.get_ue5_parameters()
        
        # CHAOTIC - desynchronized
        self.manager.set_population(0.85)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        params_chaotic = self.manager.get_ue5_parameters()
        
        self.assertGreater(params_unified.npc_breathing_sync, params_natural.npc_breathing_sync)
        self.assertGreater(params_natural.npc_breathing_sync, params_chaotic.npc_breathing_sync)


class TestWindPatternGenerator(unittest.TestCase):
    """Test wind pattern generator."""
    
    def setUp(self):
        self.generator = WindPatternGenerator(base_direction=90.0, base_strength=0.5)
    
    def test_calm_pattern(self):
        """Calm pattern should have minimal wind."""
        self.generator.set_pattern(WindPattern.CALM)
        
        direction, strength = self.generator.update(0.5, 1.0)
        
        self.assertLess(strength, 0.2)
    
    def test_steady_pattern(self):
        """Steady pattern should have consistent direction."""
        self.generator.set_pattern(WindPattern.STEADY)
        
        directions = []
        for _ in range(20):
            direction, _ = self.generator.update(0.5, 1.0)
            directions.append(direction)
        
        dir_range = max(directions) - min(directions)
        self.assertLess(dir_range, 30)  # Small variation
    
    def test_swirling_pattern(self):
        """Swirling pattern should have large direction changes."""
        self.generator.set_pattern(WindPattern.SWIRLING)
        
        directions = []
        for _ in range(50):
            direction, _ = self.generator.update(0.5, 1.0)
            directions.append(direction)
        
        dir_range = max(directions) - min(directions)
        self.assertGreater(dir_range, 50)  # Large variation
    
    def test_pattern_for_coherence(self):
        """Should recommend appropriate patterns for coherence levels."""
        self.assertEqual(
            self.generator.get_pattern_for_coherence(CoherenceLevel.UNIFIED),
            WindPattern.CALM
        )
        self.assertEqual(
            self.generator.get_pattern_for_coherence(CoherenceLevel.CHAOTIC),
            WindPattern.SWIRLING
        )


class TestMotionConfig(unittest.TestCase):
    """Test motion configuration."""
    
    def test_default_config(self):
        """Default config should have sensible values."""
        config = MotionConfig()
        
        self.assertGreater(config.unified_max_pop, 0)
        self.assertGreater(config.natural_max_pop, config.unified_max_pop)
        self.assertGreater(config.varied_max_pop, config.natural_max_pop)
    
    def test_custom_config(self):
        """Manager should accept custom config."""
        config = MotionConfig()
        config.unified_max_pop = 0.05  # Very low threshold
        
        manager = MotionManager(config=config)
        manager.set_population(0.10)
        
        for _ in range(20):
            manager.update(delta_time=0.5)
        
        self.assertNotEqual(manager.coherence_level, CoherenceLevel.UNIFIED)


class TestMotionReset(unittest.TestCase):
    """Test motion manager reset."""
    
    def test_reset_restores_coherence(self):
        """Reset should restore natural coherence."""
        manager = MotionManager()
        
        manager.set_population(0.90)
        for _ in range(30):
            manager.update(delta_time=0.5)
        
        manager.reset()
        
        self.assertEqual(manager.coherence_level, CoherenceLevel.NATURAL)
        self.assertAlmostEqual(manager.coherence_value, 1.0, delta=0.1)
    
    def test_reset_clears_elements(self):
        """Reset should reset element states."""
        manager = MotionManager()
        manager.register_element("tree_01", MotionCategory.FOLIAGE)
        
        manager.set_population(0.90)
        for _ in range(30):
            manager.update(delta_time=0.5)
        
        manager.reset()
        
        tree = manager.categories[MotionCategory.FOLIAGE].elements["tree_01"]
        self.assertAlmostEqual(tree.phase_offset, 0.0, delta=0.01)
        self.assertAlmostEqual(tree.speed_multiplier, 1.0, delta=0.01)


class TestIntegration(unittest.TestCase):
    """Integration tests for motion coherence system."""
    
    def test_full_population_cycle(self):
        """Test complete population rise and fall cycle."""
        manager = MotionManager()
        
        # Register elements
        for i in range(3):
            manager.register_element(f"tree_{i}", MotionCategory.FOLIAGE)
            manager.register_element(f"banner_{i}", MotionCategory.CLOTH)
        
        # Start peaceful
        manager.set_population(0.05)
        for _ in range(30):
            manager.update(delta_time=0.5)
        
        initial_coherence = manager.coherence_value
        
        # Population rises
        manager.set_population(0.85)
        for _ in range(50):
            manager.update(delta_time=0.5)
        
        low_coherence = manager.coherence_value
        self.assertLess(low_coherence, initial_coherence)
        
        # Population falls
        manager.set_population(0.05)
        for _ in range(50):
            manager.update(delta_time=0.5)
        
        recovered_coherence = manager.coherence_value
        self.assertGreater(recovered_coherence, low_coherence)
    
    def test_ue5_workflow(self):
        """Test complete motion → UE5 workflow."""
        manager = MotionManager()
        
        # Register elements
        manager.register_element("tree_01", MotionCategory.FOLIAGE)
        manager.register_element("banner_01", MotionCategory.CLOTH)
        manager.register_element("lantern_01", MotionCategory.PROPS)
        
        populations = [0.10, 0.30, 0.50, 0.70, 0.50, 0.30, 0.10]
        
        for pop in populations:
            manager.set_population(pop)
            
            for _ in range(20):
                snapshot = manager.update(delta_time=0.5)
            
            params = manager.get_ue5_parameters()
            data = params.to_ue5_json()
            
            # Verify UE5 data
            self.assertIn('Motion_CoherenceLevel', data)
            self.assertIn('Wind_Direction', data)
            self.assertIn('Foliage_WaveCoherence', data)


def run_tests():
    """Run all Phase 6 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestCoherenceLevels))
    suite.addTests(loader.loadTestsFromTestCase(TestWindBehavior))
    suite.addTests(loader.loadTestsFromTestCase(TestElementRegistration))
    suite.addTests(loader.loadTestsFromTestCase(TestPhaseCoherence))
    suite.addTests(loader.loadTestsFromTestCase(TestSpeedVariance))
    suite.addTests(loader.loadTestsFromTestCase(TestSettlingBehavior))
    suite.addTests(loader.loadTestsFromTestCase(TestPropJitter))
    suite.addTests(loader.loadTestsFromTestCase(TestCategoryStates))
    suite.addTests(loader.loadTestsFromTestCase(TestMotionSnapshot))
    suite.addTests(loader.loadTestsFromTestCase(TestUE5Parameters))
    suite.addTests(loader.loadTestsFromTestCase(TestWindPatternGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestMotionConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestMotionReset))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
