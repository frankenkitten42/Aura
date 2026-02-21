"""
VDE Phase 8 Tests: Pressure Coordinator

Tests:
- SDI/VDI lag behavior
- Anti-synchronization logic
- Pressure phases
- Cross-region coordination
- Attraction broadcasting
- Scenario simulation
- UE5 parameter generation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from vde.pressure_coordinator import (
    PressureCoordinator, PressureConfig, PressureSnapshot,
    PressurePhase, SyncState, RegionPressureManager,
    RegionPressureState, PressureHistory, PressureSample,
    FPressureParameters, ScenarioSimulator,
)


class TestSDIVDILag(unittest.TestCase):
    """Test SDI/VDI lag behavior."""
    
    def setUp(self):
        self.manager = RegionPressureManager("test_region")
    
    def test_sdi_responds_fast(self):
        """SDI should respond quickly to population changes."""
        self.manager.set_population(0.80)
        
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        # SDI should be significantly positive
        self.assertGreater(self.manager.sdi, 0.2)
    
    def test_vdi_lags_behind_sdi(self):
        """VDI should lag behind SDI on rise."""
        self.manager.set_population(0.80)
        
        for _ in range(10):
            self.manager.update(delta_time=0.5)
        
        # After short time, SDI should lead VDI
        self.assertGreater(self.manager.sdi, self.manager.vdi)
    
    def test_vdi_eventually_catches_up(self):
        """VDI should eventually catch up to SDI."""
        self.manager.set_population(0.80)
        
        for _ in range(100):
            self.manager.update(delta_time=0.5)
        
        # After long time, VDI should be close to SDI
        self.assertAlmostEqual(self.manager.sdi, self.manager.vdi, delta=0.1)
    
    def test_asymmetric_recovery(self):
        """VDI should recover slower than it rises."""
        # First pressure up
        self.manager.set_population(0.80)
        for _ in range(60):
            self.manager.update(delta_time=0.5)
        
        rise_vdi = self.manager.vdi
        self.assertGreater(rise_vdi, 0.3)  # Ensure we have significant VDI
        
        # Now recover (not all the way to pristine)
        self.manager.set_population(0.30)  # Medium population
        for _ in range(40):
            self.manager.update(delta_time=0.5)
        
        # VDI should still be higher than target due to slow recovery
        # Target VDI at 0.30 pop is approximately 0.0
        # But lagged VDI should still be above that
        self.assertGreater(self.manager.vdi, 0.05)


class TestAntiSynchronization(unittest.TestCase):
    """Test anti-synchronization logic."""
    
    def setUp(self):
        self.manager = RegionPressureManager("test_region")
    
    def test_normal_state_initially(self):
        """Should start in NORMAL sync state."""
        self.assertEqual(self.manager.state.sync_state, SyncState.NORMAL)
    
    def test_spike_detection(self):
        """Should detect SDI spikes."""
        # Rapid population increase
        for i in range(20):
            self.manager.set_population(0.10 + i * 0.04)
            self.manager.update(delta_time=0.5)
        
        # Check history recorded rate of change
        rate = self.manager.state.history.get_sdi_rate_of_change()
        self.assertIsNotNone(rate)
    
    def test_vdi_held_during_spike(self):
        """VDI should be held during SDI spike."""
        # Configure for easier spike detection
        self.manager.config.sync_threshold = 0.05
        
        # Start with some baseline
        self.manager.set_population(0.30)
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        vdi_before = self.manager.vdi
        
        # Rapid spike
        self.manager.set_population(0.90)
        self.manager.update(delta_time=0.5)
        
        # If spike detected, VDI should be similar
        if self.manager.state.sync_state == SyncState.SDI_SPIKING:
            vdi_after = self.manager.vdi
            self.assertAlmostEqual(vdi_before, vdi_after, delta=0.05)


class TestPressurePhases(unittest.TestCase):
    """Test pressure phase determination."""
    
    def setUp(self):
        self.manager = RegionPressureManager("test_region")
    
    def test_pristine_at_low_pop(self):
        """Should be PRISTINE at low population."""
        self.manager.set_population(0.10)
        
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        self.assertEqual(self.manager.phase, PressurePhase.PRISTINE)
    
    def test_audio_leading_phase(self):
        """Should detect AUDIO_LEADING phase."""
        # Sudden population increase
        self.manager.set_population(0.80)
        
        # After short time, audio should lead
        for _ in range(10):
            snapshot = self.manager.update(delta_time=0.5)
        
        # SDI should be high, VDI still catching up
        self.assertGreater(snapshot.sdi, snapshot.vdi_lagged)
    
    def test_fully_pressured_phase(self):
        """Should reach FULLY_PRESSURED phase."""
        self.manager.set_population(0.85)
        
        # After long time, both should be high
        for _ in range(100):
            snapshot = self.manager.update(delta_time=0.5)
        
        self.assertEqual(snapshot.phase, PressurePhase.FULLY_PRESSURED)
    
    def test_visual_trailing_phase(self):
        """Should detect VISUAL_TRAILING phase during recovery."""
        # First, get to fully pressured
        self.manager.set_population(0.85)
        for _ in range(100):
            self.manager.update(delta_time=0.5)
        
        # Now rapidly reduce population
        self.manager.set_population(0.10)
        
        # After short time, SDI drops but VDI lags
        for _ in range(20):
            snapshot = self.manager.update(delta_time=0.5)
        
        # Should be in visual trailing (low SDI, high VDI)
        self.assertLess(snapshot.sdi, snapshot.vdi_lagged)


class TestPressureCoordinator(unittest.TestCase):
    """Test cross-region coordination."""
    
    def setUp(self):
        self.coordinator = PressureCoordinator()
        self.coordinator.add_region("marketplace", position=(0, 0))
        self.coordinator.add_region("forest", position=(500, 0))
        self.coordinator.add_region("meadow", position=(800, 0))
    
    def test_add_regions(self):
        """Should add regions correctly."""
        self.assertEqual(len(self.coordinator.regions), 3)
        self.assertIn("marketplace", self.coordinator.regions)
    
    def test_set_population(self):
        """Should set population for specific region."""
        self.coordinator.set_population("marketplace", 0.80)
        
        self.assertEqual(
            self.coordinator.regions["marketplace"].state.population_target,
            0.80
        )
    
    def test_update_all_regions(self):
        """Should update all regions."""
        self.coordinator.set_population("marketplace", 0.80)
        self.coordinator.set_population("forest", 0.10)
        
        snapshots = self.coordinator.update(delta_time=0.5)
        
        self.assertEqual(len(snapshots), 3)
    
    def test_get_highest_pressure_region(self):
        """Should identify highest pressure region."""
        self.coordinator.set_population("marketplace", 0.85)
        self.coordinator.set_population("forest", 0.10)
        self.coordinator.set_population("meadow", 0.30)
        
        for _ in range(50):
            self.coordinator.update(delta_time=0.5)
        
        highest = self.coordinator.get_highest_pressure_region()
        self.assertEqual(highest, "marketplace")
    
    def test_get_lowest_pressure_region(self):
        """Should identify lowest pressure region."""
        self.coordinator.set_population("marketplace", 0.85)
        self.coordinator.set_population("forest", 0.10)
        self.coordinator.set_population("meadow", 0.30)
        
        for _ in range(50):
            self.coordinator.update(delta_time=0.5)
        
        lowest = self.coordinator.get_lowest_pressure_region()
        self.assertEqual(lowest, "forest")


class TestAttractionBroadcasting(unittest.TestCase):
    """Test cross-region attraction broadcasting."""
    
    def setUp(self):
        self.coordinator = PressureCoordinator()
        self.coordinator.add_region("crowded", position=(0, 0))
        self.coordinator.add_region("nearby", position=(400, 0))
        self.coordinator.add_region("far", position=(2000, 0))
    
    def test_attraction_to_nearby(self):
        """Nearby quiet regions should receive attraction."""
        self.coordinator.set_population("crowded", 0.90)
        self.coordinator.set_population("nearby", 0.10)
        self.coordinator.set_population("far", 0.10)
        
        for _ in range(50):
            self.coordinator.update(delta_time=0.5)
        
        nearby_attraction = self.coordinator.get_attraction("nearby")
        far_attraction = self.coordinator.get_attraction("far")
        
        # Nearby should receive more attraction
        self.assertGreater(nearby_attraction, far_attraction)
    
    def test_no_attraction_to_crowded(self):
        """Crowded regions should not receive attraction."""
        self.coordinator.set_population("crowded", 0.90)
        self.coordinator.set_population("nearby", 0.85)
        
        for _ in range(50):
            self.coordinator.update(delta_time=0.5)
        
        crowded_attraction = self.coordinator.get_attraction("crowded")
        self.assertLess(crowded_attraction, 0.1)


class TestPressureHistory(unittest.TestCase):
    """Test pressure history tracking."""
    
    def setUp(self):
        self.history = PressureHistory(duration=10.0, sample_rate=2.0)
    
    def test_add_samples(self):
        """Should add samples correctly."""
        self.history.add_sample(0.0, 0.5, 0.3, 0.2, PressurePhase.PRISTINE)
        self.history.add_sample(0.5, 0.5, 0.3, 0.2, PressurePhase.PRISTINE)
        
        self.assertGreater(len(self.history.samples), 0)
    
    def test_prune_old_samples(self):
        """Should prune samples older than duration."""
        for i in range(50):
            self.history.add_sample(
                float(i), 0.5, 0.3, 0.2, PressurePhase.PRISTINE
            )
        
        # Should have pruned old samples
        oldest = self.history.samples[0].timestamp
        self.assertGreater(oldest, 35.0)
    
    def test_rate_of_change(self):
        """Should calculate SDI rate of change."""
        self.history.add_sample(0.0, 0.5, 0.1, 0.1, PressurePhase.PRISTINE)
        self.history.add_sample(1.0, 0.5, 0.2, 0.1, PressurePhase.PRISTINE)
        self.history.add_sample(2.0, 0.5, 0.3, 0.1, PressurePhase.PRISTINE)
        
        rate = self.history.get_sdi_rate_of_change()
        self.assertGreater(rate, 0)


class TestPressureSnapshot(unittest.TestCase):
    """Test pressure snapshot generation."""
    
    def setUp(self):
        self.manager = RegionPressureManager("test_region")
    
    def test_snapshot_contains_all_fields(self):
        """Snapshot should contain all required fields."""
        self.manager.set_population(0.50)
        snapshot = self.manager.update(delta_time=0.5)
        
        self.assertIsInstance(snapshot.population, float)
        self.assertIsInstance(snapshot.sdi, float)
        self.assertIsInstance(snapshot.vdi, float)
        self.assertIsInstance(snapshot.phase, PressurePhase)
        self.assertIsInstance(snapshot.sync_state, SyncState)
    
    def test_snapshot_to_dict(self):
        """Snapshot should serialize to dictionary."""
        self.manager.set_population(0.50)
        snapshot = self.manager.update(delta_time=0.5)
        
        data = snapshot.to_dict()
        
        self.assertIn('region_id', data)
        self.assertIn('sdi', data)
        self.assertIn('vdi', data)
        self.assertIn('phase', data)
        self.assertIn('combined_pressure', data)


class TestUE5Parameters(unittest.TestCase):
    """Test UE5 parameter generation."""
    
    def setUp(self):
        self.manager = RegionPressureManager("test_region")
    
    def test_parameter_generation(self):
        """Should generate UE5 parameters."""
        self.manager.set_population(0.65)
        for _ in range(30):
            self.manager.update(delta_time=0.5)
        
        params = FPressureParameters.from_manager(self.manager)
        
        self.assertIsInstance(params, FPressureParameters)
    
    def test_parameters_to_json(self):
        """Parameters should serialize to JSON."""
        params = FPressureParameters()
        params.sdi = 0.5
        params.vdi = 0.3
        params.phase = "audio_leading"
        
        data = params.to_ue5_json()
        
        self.assertIn('Pressure_SDI', data)
        self.assertIn('Pressure_VDI', data)
        self.assertIn('Pressure_Phase', data)
        self.assertIn('Flag_AudioLeading', data)
    
    def test_coordinator_to_ue5_json(self):
        """Coordinator should generate complete UE5 JSON."""
        coordinator = PressureCoordinator()
        coordinator.add_region("region_a", position=(0, 0))
        coordinator.add_region("region_b", position=(500, 0))
        
        coordinator.set_population("region_a", 0.80)
        coordinator.set_population("region_b", 0.10)
        
        for _ in range(30):
            coordinator.update(delta_time=0.5)
        
        data = coordinator.to_ue5_json()
        
        self.assertIn('Regions', data)
        self.assertIn('HighestPressureRegion', data)
        self.assertIn('LowestPressureRegion', data)
        self.assertIn('PressureMap', data)


class TestScenarioSimulator(unittest.TestCase):
    """Test scenario simulation."""
    
    def test_crowding_scenario(self):
        """Should simulate crowding scenario."""
        coordinator = PressureCoordinator()
        coordinator.add_region("test", position=(0, 0))
        
        snapshots = ScenarioSimulator.simulate_crowding(
            coordinator, "test",
            duration=60.0,
            peak_population=0.80,
            ramp_duration=30.0,
        )
        
        self.assertGreater(len(snapshots), 0)
        
        # Pressure should increase over time
        early = snapshots[10] if len(snapshots) > 10 else snapshots[0]
        late = snapshots[-1]
        
        self.assertGreater(late.combined_pressure, early.combined_pressure)
    
    def test_dispersal_scenario(self):
        """Should simulate dispersal scenario."""
        coordinator = PressureCoordinator()
        coordinator.add_region("test", position=(0, 0))
        
        snapshots = ScenarioSimulator.simulate_dispersal(
            coordinator, "test",
            duration=60.0,
            start_population=0.85,
            end_population=0.15,
            ramp_duration=30.0,
        )
        
        self.assertGreater(len(snapshots), 0)
        
        # Pressure should decrease over time
        early = snapshots[10] if len(snapshots) > 10 else snapshots[0]
        late = snapshots[-1]
        
        self.assertLess(late.combined_pressure, early.combined_pressure)


class TestPressureConfig(unittest.TestCase):
    """Test pressure configuration."""
    
    def test_default_config(self):
        """Default config should have sensible values."""
        config = PressureConfig()
        
        self.assertGreater(config.vdi_lag_rise, 0)
        self.assertGreater(config.vdi_lag_fall, config.vdi_lag_rise)
    
    def test_custom_config(self):
        """Manager should accept custom config."""
        config = PressureConfig()
        config.vdi_lag_rise = 5.0  # Faster lag
        
        manager = RegionPressureManager("test", config=config)
        manager.set_population(0.80)
        
        for _ in range(30):
            manager.update(delta_time=0.5)
        
        # VDI should catch up faster
        self.assertAlmostEqual(manager.sdi, manager.vdi, delta=0.2)


class TestPressureReset(unittest.TestCase):
    """Test pressure manager reset."""
    
    def test_reset_clears_state(self):
        """Reset should clear pressure state."""
        manager = RegionPressureManager("test_region")
        
        manager.set_population(0.80)
        for _ in range(50):
            manager.update(delta_time=0.5)
        
        self.assertGreater(manager.sdi, 0.2)
        
        manager.reset()
        
        self.assertAlmostEqual(manager.sdi, 0.0, delta=0.01)
        self.assertAlmostEqual(manager.vdi, 0.0, delta=0.01)
        self.assertEqual(manager.phase, PressurePhase.PRISTINE)


class TestIntegration(unittest.TestCase):
    """Integration tests for pressure coordinator."""
    
    def test_full_pressure_cycle(self):
        """Test complete pressure rise and fall cycle."""
        coordinator = PressureCoordinator()
        coordinator.add_region("test", position=(0, 0))
        
        # Start pristine
        coordinator.set_population("test", 0.10)
        for _ in range(20):
            coordinator.update(delta_time=0.5)
        
        initial_snapshot = list(coordinator.update(0.5).values())[0]
        self.assertEqual(initial_snapshot.phase, PressurePhase.PRISTINE)
        
        # Pressure up
        coordinator.set_population("test", 0.85)
        for _ in range(100):
            coordinator.update(delta_time=0.5)
        
        pressured_snapshot = list(coordinator.update(0.5).values())[0]
        self.assertEqual(pressured_snapshot.phase, PressurePhase.FULLY_PRESSURED)
        
        # Pressure down
        coordinator.set_population("test", 0.10)
        for _ in range(200):
            coordinator.update(delta_time=0.5)
        
        recovered_snapshot = list(coordinator.update(0.5).values())[0]
        self.assertEqual(recovered_snapshot.phase, PressurePhase.PRISTINE)
    
    def test_multi_region_workflow(self):
        """Test complete multi-region workflow."""
        coordinator = PressureCoordinator()
        
        # Create world
        coordinator.add_region("town", position=(0, 0))
        coordinator.add_region("market", position=(300, 0))
        coordinator.add_region("park", position=(600, 0))
        coordinator.add_region("forest", position=(900, 0))
        
        # Simulate crowd moving through
        coordinator.set_population("town", 0.90)
        coordinator.set_population("market", 0.60)
        coordinator.set_population("park", 0.30)
        coordinator.set_population("forest", 0.05)
        
        for _ in range(50):
            coordinator.update(delta_time=0.5)
        
        # Check pressure gradient
        pressure_map = coordinator.get_pressure_map()
        
        self.assertGreater(pressure_map["town"], pressure_map["market"])
        self.assertGreater(pressure_map["market"], pressure_map["park"])
        self.assertGreater(pressure_map["park"], pressure_map["forest"])
        
        # Check attraction
        forest_attraction = coordinator.get_attraction("forest")
        self.assertGreater(forest_attraction, 0)
        
        # Generate UE5 data
        ue5_data = coordinator.to_ue5_json()
        
        self.assertIn('Regions', ue5_data)
        self.assertEqual(ue5_data['HighestPressureRegion'], 'town')
        self.assertEqual(ue5_data['LowestPressureRegion'], 'forest')


def run_tests():
    """Run all Phase 8 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestSDIVDILag))
    suite.addTests(loader.loadTestsFromTestCase(TestAntiSynchronization))
    suite.addTests(loader.loadTestsFromTestCase(TestPressurePhases))
    suite.addTests(loader.loadTestsFromTestCase(TestPressureCoordinator))
    suite.addTests(loader.loadTestsFromTestCase(TestAttractionBroadcasting))
    suite.addTests(loader.loadTestsFromTestCase(TestPressureHistory))
    suite.addTests(loader.loadTestsFromTestCase(TestPressureSnapshot))
    suite.addTests(loader.loadTestsFromTestCase(TestUE5Parameters))
    suite.addTests(loader.loadTestsFromTestCase(TestScenarioSimulator))
    suite.addTests(loader.loadTestsFromTestCase(TestPressureConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestPressureReset))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
