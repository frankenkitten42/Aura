"""
VDE Phase 7 Tests: Attraction System

Tests:
- Attraction strength from population
- Signal boosts
- Distant cues
- Cross-region coordination
- Neighbor pressure influence
- UE5 parameter generation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from vde.attraction_system import (
    AttractionManager, AttractionConfig, AttractionSnapshot,
    AttractionSignal, AttractionStrength, DistantCue,
    RegionAttractionState, AttractionCoordinator,
    FAttractionParameters, DistantCueGenerator, DistantCueCommand,
)


class TestAttractionStrength(unittest.TestCase):
    """Test attraction strength based on population."""
    
    def setUp(self):
        self.manager = AttractionManager("test_region")
    
    def test_low_pop_high_attraction(self):
        """Low population should create high attraction."""
        self.manager.set_population(0.05)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.attraction_strength, AttractionStrength.BEACON)
    
    def test_medium_low_pop_strong(self):
        """Medium-low population should create STRONG attraction."""
        self.manager.set_population(0.20)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.attraction_strength, AttractionStrength.STRONG)
    
    def test_medium_pop_moderate(self):
        """Medium population should create MODERATE attraction."""
        self.manager.set_population(0.35)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.attraction_strength, AttractionStrength.MODERATE)
    
    def test_medium_high_pop_subtle(self):
        """Medium-high population should create SUBTLE attraction."""
        self.manager.set_population(0.55)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.attraction_strength, AttractionStrength.SUBTLE)
    
    def test_high_pop_no_attraction(self):
        """High population should create NO attraction."""
        self.manager.set_population(0.80)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.attraction_strength, AttractionStrength.NONE)
    
    def test_attraction_value_inversely_correlates(self):
        """Attraction value should be higher for lower population."""
        self.manager.set_population(0.05)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        low_pop_attraction = self.manager.attraction_value
        
        self.manager.reset()
        self.manager.set_population(0.80)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        high_pop_attraction = self.manager.attraction_value
        
        self.assertGreater(low_pop_attraction, high_pop_attraction)


class TestSignalBoosts(unittest.TestCase):
    """Test attraction signal boosts."""
    
    def setUp(self):
        self.manager = AttractionManager("test_region")
    
    def test_beacon_has_all_boosts(self):
        """BEACON strength should have all signal boosts."""
        self.manager.set_population(0.05)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        state = self.manager.state
        
        for signal in AttractionSignal:
            self.assertGreater(state.signal_boosts[signal], 0)
    
    def test_no_attraction_no_boosts(self):
        """NONE strength should have no signal boosts."""
        self.manager.set_population(0.80)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        state = self.manager.state
        
        for signal in AttractionSignal:
            self.assertLess(state.signal_boosts[signal], 0.01)
    
    def test_wildlife_surge_highest_boost(self):
        """Wildlife surge should be the highest boost at BEACON."""
        self.manager.set_population(0.05)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        state = self.manager.state
        wildlife = state.signal_boosts[AttractionSignal.WILDLIFE_SURGE]
        light = state.signal_boosts[AttractionSignal.LIGHT_QUALITY]
        
        self.assertGreater(wildlife, light)
    
    def test_boosts_increase_with_attraction(self):
        """Boosts should increase with attraction strength."""
        # Low attraction (high pop)
        self.manager.set_population(0.55)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        subtle_light = self.manager.state.signal_boosts[AttractionSignal.LIGHT_QUALITY]
        
        # High attraction (low pop)
        self.manager.reset()
        self.manager.set_population(0.05)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        beacon_light = self.manager.state.signal_boosts[AttractionSignal.LIGHT_QUALITY]
        
        self.assertGreater(beacon_light, subtle_light)


class TestDistantCues(unittest.TestCase):
    """Test distant visual cue activation."""
    
    def setUp(self):
        self.manager = AttractionManager("test_region")
    
    def test_beacon_has_cues(self):
        """BEACON strength should activate distant cues."""
        self.manager.set_population(0.05)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        self.assertGreater(len(self.manager.state.active_cues), 0)
    
    def test_no_attraction_no_cues(self):
        """NONE strength should have no active cues."""
        self.manager.set_population(0.80)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(len(self.manager.state.active_cues), 0)
    
    def test_bird_activity_early_threshold(self):
        """Bird activity should appear at SUBTLE strength."""
        self.manager.set_population(0.55)  # SUBTLE
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        self.assertIn(DistantCue.BIRD_ACTIVITY, self.manager.state.active_cues)
    
    def test_clear_sky_late_threshold(self):
        """Clear sky should only appear at STRONG or above."""
        self.manager.set_population(0.35)  # MODERATE
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        # Should NOT have clear sky at MODERATE
        self.assertNotIn(DistantCue.CLEAR_SKY, self.manager.state.active_cues)
        
        # Should have at STRONG
        self.manager.reset()
        self.manager.set_population(0.20)  # STRONG
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        self.assertIn(DistantCue.CLEAR_SKY, self.manager.state.active_cues)
    
    def test_cue_intensities(self):
        """Cue intensities should scale with strength."""
        self.manager.set_population(0.05)  # BEACON
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        # All active cues should have positive intensity
        for cue in self.manager.state.active_cues:
            self.assertGreater(self.manager.state.cue_intensities[cue], 0)


class TestNeighborPressure(unittest.TestCase):
    """Test neighbor pressure influence."""
    
    def setUp(self):
        self.manager = AttractionManager("test_region")
    
    def test_neighbor_pressure_boosts_attraction(self):
        """High neighbor pressure should boost attraction."""
        # Medium population, no pressure
        self.manager.set_population(0.45)
        self.manager.set_neighbor_pressure(0.0)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        no_pressure_strength = self.manager.attraction_strength
        
        # Same population, high pressure
        self.manager.reset()
        self.manager.set_population(0.45)
        self.manager.set_neighbor_pressure(0.80)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        high_pressure_strength = self.manager.attraction_strength
        
        # Pressure should boost by one level
        strength_order = [
            AttractionStrength.NONE,
            AttractionStrength.SUBTLE,
            AttractionStrength.MODERATE,
            AttractionStrength.STRONG,
            AttractionStrength.BEACON,
        ]
        
        no_idx = strength_order.index(no_pressure_strength)
        high_idx = strength_order.index(high_pressure_strength)
        
        self.assertGreater(high_idx, no_idx)
    
    def test_is_overflow_target(self):
        """High neighbor pressure should mark as overflow target."""
        self.manager.set_population(0.30)
        self.manager.set_neighbor_pressure(0.70)
        
        for _ in range(10):
            self.manager.update(delta_time=0.5)
        
        self.assertTrue(self.manager.state.is_receiving_overflow)


class TestAttractionCoordinator(unittest.TestCase):
    """Test cross-region coordination."""
    
    def setUp(self):
        self.coordinator = AttractionCoordinator()
        self.coordinator.add_region("marketplace", position=(0, 0))
        self.coordinator.add_region("forest_path", position=(500, 0))
        self.coordinator.add_region("quiet_grove", position=(800, 0))
    
    def test_add_regions(self):
        """Should add regions correctly."""
        self.assertEqual(len(self.coordinator.regions), 3)
        self.assertIn("marketplace", self.coordinator.regions)
    
    def test_set_population(self):
        """Should set population for specific region."""
        self.coordinator.set_population("marketplace", 0.80)
        
        self.assertEqual(
            self.coordinator.regions["marketplace"].state.population,
            0.80
        )
    
    def test_update_all_regions(self):
        """Should update all regions."""
        self.coordinator.set_population("marketplace", 0.80)
        self.coordinator.set_population("quiet_grove", 0.10)
        
        snapshots = self.coordinator.update(delta_time=0.5)
        
        self.assertEqual(len(snapshots), 3)
    
    def test_crowded_neighbor_influences_quiet(self):
        """Crowded neighbor should boost quiet region's attraction."""
        self.coordinator.set_population("marketplace", 0.90)  # Crowded
        self.coordinator.set_population("forest_path", 0.20)  # Quiet, close
        self.coordinator.set_population("quiet_grove", 0.20)  # Quiet, farther
        
        for _ in range(30):
            self.coordinator.update(delta_time=0.5)
        
        forest_pressure = self.coordinator.regions["forest_path"].state.neighbor_pressure
        grove_pressure = self.coordinator.regions["quiet_grove"].state.neighbor_pressure
        
        # Forest should receive more pressure (closer)
        self.assertGreater(forest_pressure, grove_pressure)
    
    def test_get_most_attractive_region(self):
        """Should identify most attractive region."""
        self.coordinator.set_population("marketplace", 0.90)
        self.coordinator.set_population("forest_path", 0.50)
        self.coordinator.set_population("quiet_grove", 0.05)
        
        for _ in range(30):
            self.coordinator.update(delta_time=0.5)
        
        most_attractive = self.coordinator.get_most_attractive_region()
        
        self.assertEqual(most_attractive, "quiet_grove")
    
    def test_pressure_map(self):
        """Should generate pressure map."""
        self.coordinator.set_population("marketplace", 0.80)
        self.coordinator.set_population("quiet_grove", 0.10)
        
        pressure_map = self.coordinator.get_pressure_map()
        
        self.assertIn("marketplace", pressure_map)
        self.assertIn("quiet_grove", pressure_map)
        self.assertGreater(pressure_map["marketplace"], pressure_map["quiet_grove"])
    
    def test_attraction_map(self):
        """Should generate attraction map."""
        self.coordinator.set_population("marketplace", 0.80)
        self.coordinator.set_population("quiet_grove", 0.10)
        
        for _ in range(30):
            self.coordinator.update(delta_time=0.5)
        
        attraction_map = self.coordinator.get_attraction_map()
        
        self.assertIn("marketplace", attraction_map)
        self.assertIn("quiet_grove", attraction_map)
        self.assertGreater(attraction_map["quiet_grove"], attraction_map["marketplace"])


class TestAttractionSnapshot(unittest.TestCase):
    """Test attraction snapshot generation."""
    
    def setUp(self):
        self.manager = AttractionManager("test_region")
    
    def test_snapshot_contains_all_fields(self):
        """Snapshot should contain all required fields."""
        self.manager.set_population(0.20)
        snapshot = self.manager.update(delta_time=0.5)
        
        self.assertIsInstance(snapshot.population, float)
        self.assertIsInstance(snapshot.attraction_strength, AttractionStrength)
        self.assertIsInstance(snapshot.attraction_value, float)
        self.assertIsInstance(snapshot.signal_boosts, dict)
        self.assertIsInstance(snapshot.active_cues, list)
    
    def test_snapshot_to_dict(self):
        """Snapshot should serialize to dictionary."""
        self.manager.set_population(0.20)
        snapshot = self.manager.update(delta_time=0.5)
        
        data = snapshot.to_dict()
        
        self.assertIn('region_id', data)
        self.assertIn('attraction_strength', data)
        self.assertIn('signal_boosts', data)
        self.assertIn('active_cues', data)


class TestUE5Parameters(unittest.TestCase):
    """Test UE5 parameter generation."""
    
    def setUp(self):
        self.manager = AttractionManager("test_region")
    
    def test_parameter_generation(self):
        """Should generate UE5 parameters."""
        self.manager.set_population(0.15)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        params = self.manager.get_ue5_parameters()
        
        self.assertIsInstance(params, FAttractionParameters)
    
    def test_parameters_reflect_attraction(self):
        """Parameters should reflect attraction level."""
        # High attraction
        self.manager.set_population(0.05)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        params_high = self.manager.get_ue5_parameters()
        
        # Low attraction
        self.manager.reset()
        self.manager.set_population(0.80)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        params_low = self.manager.get_ue5_parameters()
        
        self.assertGreater(params_high.wildlife_surge_boost, params_low.wildlife_surge_boost)
        self.assertGreater(params_high.light_quality_boost, params_low.light_quality_boost)
    
    def test_parameters_to_json(self):
        """Parameters should serialize to JSON."""
        params = FAttractionParameters()
        params.attraction_value = 0.8
        params.light_quality_boost = 0.15
        
        data = params.to_ue5_json()
        
        self.assertIn('Attraction_Strength', data)
        self.assertIn('Boost_LightQuality', data)
        self.assertIn('Cue_LightShafts', data)
        self.assertIn('CrossRegion_NeighborPressure', data)
    
    def test_coordinator_to_ue5_json(self):
        """Coordinator should generate complete UE5 JSON."""
        coordinator = AttractionCoordinator()
        coordinator.add_region("region_a", position=(0, 0))
        coordinator.add_region("region_b", position=(500, 0))
        
        coordinator.set_population("region_a", 0.80)
        coordinator.set_population("region_b", 0.10)
        
        for _ in range(30):
            coordinator.update(delta_time=0.5)
        
        data = coordinator.to_ue5_json()
        
        self.assertIn('Regions', data)
        self.assertIn('MostAttractiveRegion', data)
        self.assertIn('PressureMap', data)
        self.assertIn('AttractionMap', data)


class TestDistantCueGenerator(unittest.TestCase):
    """Test distant cue command generation."""
    
    def setUp(self):
        self.manager = AttractionManager("test_region", position=(100, 200))
        self.generator = DistantCueGenerator()
    
    def test_generate_cues(self):
        """Should generate cue commands for active cues."""
        self.manager.set_population(0.05)  # BEACON
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        commands = self.generator.generate_cues(self.manager)
        
        self.assertGreater(len(commands), 0)
    
    def test_cue_command_structure(self):
        """Cue commands should have correct structure."""
        self.manager.set_population(0.05)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        commands = self.generator.generate_cues(self.manager)
        
        if commands:
            cmd = commands[0]
            self.assertIsInstance(cmd.cue_type, DistantCue)
            self.assertIsInstance(cmd.intensity, float)
            self.assertIsInstance(cmd.position, tuple)
            self.assertEqual(len(cmd.position), 3)
    
    def test_cue_command_to_json(self):
        """Cue commands should serialize to JSON."""
        cmd = DistantCueCommand(
            cue_type=DistantCue.LIGHT_SHAFTS,
            intensity=0.8,
            position=(100.0, 200.0, 500.0),
            scale=1.2,
        )
        
        data = cmd.to_ue5_json()
        
        self.assertIn('CueType', data)
        self.assertIn('Intensity', data)
        self.assertIn('Position', data)
        self.assertIn('Scale', data)


class TestAttractionConfig(unittest.TestCase):
    """Test attraction configuration."""
    
    def test_default_config(self):
        """Default config should have sensible values."""
        config = AttractionConfig()
        
        self.assertGreater(config.beacon_max_pop, 0)
        self.assertGreater(config.strong_max_pop, config.beacon_max_pop)
        self.assertGreater(config.moderate_max_pop, config.strong_max_pop)
    
    def test_custom_config(self):
        """Manager should accept custom config."""
        config = AttractionConfig()
        config.beacon_max_pop = 0.20  # Higher threshold
        
        manager = AttractionManager("test", config=config)
        manager.set_population(0.15)
        
        for _ in range(30):
            manager.update(delta_time=0.5)
        
        self.assertEqual(manager.attraction_strength, AttractionStrength.BEACON)


class TestAttractionReset(unittest.TestCase):
    """Test attraction manager reset."""
    
    def test_reset_clears_attraction(self):
        """Reset should clear attraction state."""
        manager = AttractionManager("test_region")
        
        manager.set_population(0.05)
        for _ in range(30):
            manager.update(delta_time=0.5)
        
        self.assertGreater(manager.attraction_value, 0.5)
        
        manager.reset()
        
        self.assertEqual(manager.attraction_strength, AttractionStrength.NONE)
        self.assertAlmostEqual(manager.attraction_value, 0.0, delta=0.01)
    
    def test_reset_clears_cues(self):
        """Reset should clear active cues."""
        manager = AttractionManager("test_region")
        
        manager.set_population(0.05)
        for _ in range(30):
            manager.update(delta_time=0.5)
        
        manager.reset()
        
        self.assertEqual(len(manager.state.active_cues), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for attraction system."""
    
    def test_full_cross_region_cycle(self):
        """Test complete cross-region attraction cycle."""
        coordinator = AttractionCoordinator()
        
        # Create a small world
        coordinator.add_region("town_center", position=(0, 0))
        coordinator.add_region("market_street", position=(300, 0))
        coordinator.add_region("park", position=(600, 0))
        coordinator.add_region("forest_edge", position=(900, 0))
        
        # Simulate crowd moving through
        # Phase 1: Crowd in town center
        coordinator.set_population("town_center", 0.90)
        coordinator.set_population("market_street", 0.60)
        coordinator.set_population("park", 0.20)
        coordinator.set_population("forest_edge", 0.05)
        
        for _ in range(30):
            coordinator.update(delta_time=0.5)
        
        # Forest edge should be most attractive
        most_attractive = coordinator.get_most_attractive_region()
        self.assertEqual(most_attractive, "forest_edge")
        
        # Market should receive overflow pressure from town
        market_pressure = coordinator.regions["market_street"].state.neighbor_pressure
        self.assertGreater(market_pressure, 0)
    
    def test_ue5_workflow(self):
        """Test complete attraction → UE5 workflow."""
        coordinator = AttractionCoordinator()
        generator = DistantCueGenerator()
        
        coordinator.add_region("region_a", position=(0, 0))
        coordinator.add_region("region_b", position=(500, 0))
        
        coordinator.set_population("region_a", 0.85)
        coordinator.set_population("region_b", 0.10)
        
        for _ in range(30):
            coordinator.update(delta_time=0.5)
        
        # Get UE5 data
        ue5_data = coordinator.to_ue5_json()
        
        self.assertIn('Regions', ue5_data)
        self.assertEqual(ue5_data['MostAttractiveRegion'], 'region_b')
        
        # Generate cues for attractive region
        cues = generator.generate_cues(coordinator.regions["region_b"])
        self.assertGreater(len(cues), 0)


def run_tests():
    """Run all Phase 7 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestAttractionStrength))
    suite.addTests(loader.loadTestsFromTestCase(TestSignalBoosts))
    suite.addTests(loader.loadTestsFromTestCase(TestDistantCues))
    suite.addTests(loader.loadTestsFromTestCase(TestNeighborPressure))
    suite.addTests(loader.loadTestsFromTestCase(TestAttractionCoordinator))
    suite.addTests(loader.loadTestsFromTestCase(TestAttractionSnapshot))
    suite.addTests(loader.loadTestsFromTestCase(TestUE5Parameters))
    suite.addTests(loader.loadTestsFromTestCase(TestDistantCueGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestAttractionConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestAttractionReset))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
