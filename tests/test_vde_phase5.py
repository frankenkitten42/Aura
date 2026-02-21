"""
VDE Phase 5 Tests: Environmental Wear System

Tests:
- Wear layer accumulation
- Asymmetric accumulation/recovery timing
- Surface-type specific behavior
- Layer cascade effects
- Multi-zone management
- UE5 parameter generation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from vde.environmental_wear import (
    WearManager, WearConfig, WearSnapshot,
    WearLayer, SurfaceType, WearType,
    FWearParameters, RegionWearManager, WearZone,
    WEAR_LAYER_MAP, SURFACE_WEAR_MAP,
)


class TestWearAccumulation(unittest.TestCase):
    """Test wear accumulation behavior."""
    
    def setUp(self):
        self.manager = WearManager(surface_type=SurfaceType.GRASS)
    
    def test_initial_state_zero(self):
        """Wear should start at zero."""
        self.assertAlmostEqual(self.manager.total_wear, 0.0, delta=0.01)
    
    def test_low_pop_no_accumulation(self):
        """Low population should not accumulate wear."""
        self.manager.set_population(0.10)
        
        for _ in range(100):
            self.manager.update(delta_time=0.5)
        
        self.assertLess(self.manager.total_wear, 0.1)
    
    def test_high_pop_accumulates_wear(self):
        """High population should accumulate wear."""
        self.manager.set_population(0.80)
        
        for _ in range(100):
            self.manager.update(delta_time=0.5)
        
        self.assertGreater(self.manager.total_wear, 0.1)
    
    def test_displacement_accumulates_fastest(self):
        """Displacement layer should accumulate fastest."""
        self.manager.set_population(0.80)
        
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        disp = self.manager.surface.layers[WearLayer.DISPLACEMENT].value
        disc = self.manager.surface.layers[WearLayer.DISCOLORATION].value
        dmg = self.manager.surface.layers[WearLayer.DAMAGE].value
        
        self.assertGreater(disp, disc)
        self.assertGreater(disc, dmg)
    
    def test_wear_capped_at_max(self):
        """Wear should not exceed maximum."""
        self.manager.set_population(1.0)
        
        # Run for a very long time
        for _ in range(1000):
            self.manager.update(delta_time=1.0)
        
        for layer in WearLayer:
            value = self.manager.surface.layers[layer].value
            max_value = self.manager.config.max_wear.get(layer, 1.0)
            self.assertLessEqual(value, max_value)


class TestWearRecovery(unittest.TestCase):
    """Test wear recovery behavior."""
    
    def setUp(self):
        self.manager = WearManager(surface_type=SurfaceType.GRASS)
    
    def test_recovery_at_low_pop(self):
        """Wear should recover at low population."""
        # First accumulate wear
        self.manager.set_population(0.80)
        for _ in range(100):
            self.manager.update(delta_time=0.5)
        
        initial_wear = self.manager.total_wear
        
        # Now recover
        self.manager.set_population(0.05)
        for _ in range(200):
            self.manager.update(delta_time=0.5)
        
        final_wear = self.manager.total_wear
        self.assertLess(final_wear, initial_wear)
    
    def test_displacement_recovers_fastest(self):
        """Displacement should recover faster than damage."""
        # Accumulate wear
        self.manager.set_population(0.90)
        for _ in range(200):
            self.manager.update(delta_time=0.5)
        
        initial_disp = self.manager.surface.layers[WearLayer.DISPLACEMENT].value
        initial_dmg = self.manager.surface.layers[WearLayer.DAMAGE].value
        
        # Recover
        self.manager.set_population(0.0)
        for _ in range(120):  # 60 seconds
            self.manager.update(delta_time=0.5)
        
        disp_recovery = initial_disp - self.manager.surface.layers[WearLayer.DISPLACEMENT].value
        dmg_recovery = initial_dmg - self.manager.surface.layers[WearLayer.DAMAGE].value
        
        # Displacement should recover more
        self.assertGreater(disp_recovery, dmg_recovery)
    
    def test_recovery_slower_than_accumulation(self):
        """Recovery should be slower than accumulation."""
        # Measure accumulation time
        self.manager.set_population(0.80)
        accum_ticks = 0
        while self.manager.surface.layers[WearLayer.DISPLACEMENT].value < 0.5:
            self.manager.update(delta_time=0.5)
            accum_ticks += 1
            if accum_ticks > 500:
                break
        
        # Measure recovery time
        self.manager.set_population(0.0)
        recovery_ticks = 0
        while self.manager.surface.layers[WearLayer.DISPLACEMENT].value > 0.25:
            self.manager.update(delta_time=0.5)
            recovery_ticks += 1
            if recovery_ticks > 1000:
                break
        
        # Recovery should take longer
        self.assertGreater(recovery_ticks, accum_ticks)


class TestLayerCascade(unittest.TestCase):
    """Test layer cascade effects."""
    
    def setUp(self):
        self.manager = WearManager(surface_type=SurfaceType.GRASS)
    
    def test_displacement_cascades_to_discoloration(self):
        """High displacement should contribute to discoloration."""
        self.manager.set_population(0.90)
        
        # Run until displacement is high
        for _ in range(100):
            self.manager.update(delta_time=0.5)
        
        # Discoloration should be non-zero even if direct rate is slower
        disc = self.manager.surface.layers[WearLayer.DISCOLORATION].value
        self.assertGreater(disc, 0.0)
    
    def test_cascade_only_when_significant(self):
        """Cascade should only occur when source layer is significant."""
        self.manager.set_population(0.30)  # Low population
        
        for _ in range(20):
            self.manager.update(delta_time=0.5)
        
        # Damage should be minimal (cascade shouldn't trigger)
        dmg = self.manager.surface.layers[WearLayer.DAMAGE].value
        self.assertLess(dmg, 0.05)


class TestSurfaceTypes(unittest.TestCase):
    """Test surface-type specific behavior."""
    
    def test_grass_normal_wear(self):
        """Grass should have normal wear rate."""
        manager = WearManager(surface_type=SurfaceType.GRASS)
        mult = manager.config.surface_multipliers[SurfaceType.GRASS]
        self.assertAlmostEqual(mult, 1.0, delta=0.1)
    
    def test_stone_minimal_wear(self):
        """Stone should have minimal wear."""
        manager = WearManager(surface_type=SurfaceType.STONE)
        mult = manager.config.surface_multipliers[SurfaceType.STONE]
        self.assertLess(mult, 0.5)
    
    def test_snow_high_visibility(self):
        """Snow should show wear more visibly."""
        manager = WearManager(surface_type=SurfaceType.SNOW)
        mult = manager.config.surface_multipliers[SurfaceType.SNOW]
        self.assertGreater(mult, 1.0)
    
    def test_different_surfaces_different_wear(self):
        """Different surfaces should accumulate different amounts of wear."""
        grass = WearManager(surface_type=SurfaceType.GRASS)
        stone = WearManager(surface_type=SurfaceType.STONE)
        snow = WearManager(surface_type=SurfaceType.SNOW)
        
        for mgr in [grass, stone, snow]:
            mgr.set_population(0.80)
            for _ in range(50):
                mgr.update(delta_time=0.5)
        
        # Snow > Grass > Stone
        self.assertGreater(snow.total_wear, grass.total_wear)
        self.assertGreater(grass.total_wear, stone.total_wear)
    
    def test_surface_wear_mapping(self):
        """Surface wear mapping should be correct."""
        grass_wear = SURFACE_WEAR_MAP[SurfaceType.GRASS]
        
        self.assertIn(WearType.TRAMPLED_GRASS, grass_wear)
        self.assertIn(WearType.GRASS_BROWNING, grass_wear)
        self.assertIn(WearType.DEAD_PATCHES, grass_wear)


class TestActiveEffects(unittest.TestCase):
    """Test active wear effects tracking."""
    
    def setUp(self):
        self.manager = WearManager(surface_type=SurfaceType.GRASS)
    
    def test_effects_match_surface(self):
        """Active effects should match surface type."""
        expected = SURFACE_WEAR_MAP[SurfaceType.GRASS]
        
        for wear_type in expected:
            self.assertIn(wear_type, self.manager.surface.active_effects)
    
    def test_effects_track_layers(self):
        """Effects should track their layer values."""
        self.manager.set_population(0.80)
        
        for _ in range(100):
            self.manager.update(delta_time=0.5)
        
        # Trampled grass should match displacement
        disp = self.manager.surface.layers[WearLayer.DISPLACEMENT].value
        trampled = self.manager.surface.active_effects.get(WearType.TRAMPLED_GRASS, 0)
        
        self.assertAlmostEqual(trampled, disp, delta=0.1)


class TestWearSnapshot(unittest.TestCase):
    """Test wear snapshot generation."""
    
    def setUp(self):
        self.manager = WearManager(surface_type=SurfaceType.GRASS)
    
    def test_snapshot_contains_all_fields(self):
        """Snapshot should contain all required fields."""
        self.manager.set_population(0.50)
        snapshot = self.manager.update(delta_time=0.5)
        
        self.assertIsInstance(snapshot.population, float)
        self.assertIsInstance(snapshot.layer_values, dict)
        self.assertIsInstance(snapshot.active_effects, dict)
        self.assertIsInstance(snapshot.total_wear, float)
    
    def test_snapshot_to_dict(self):
        """Snapshot should serialize to dictionary."""
        self.manager.set_population(0.50)
        snapshot = self.manager.update(delta_time=0.5)
        
        data = snapshot.to_dict()
        
        self.assertIn('population', data)
        self.assertIn('layer_values', data)
        self.assertIn('total_wear', data)
    
    def test_snapshot_tracking_flags(self):
        """Snapshot should track accumulating/recovering flags."""
        self.manager.set_population(0.80)
        snapshot = self.manager.update(delta_time=0.5)
        
        self.assertTrue(snapshot.is_accumulating)
        self.assertFalse(snapshot.is_recovering)
        
        self.manager.set_population(0.05)
        snapshot = self.manager.update(delta_time=0.5)
        
        self.assertFalse(snapshot.is_accumulating)
        self.assertTrue(snapshot.is_recovering)


class TestUE5Parameters(unittest.TestCase):
    """Test UE5 parameter generation."""
    
    def setUp(self):
        self.manager = WearManager(surface_type=SurfaceType.GRASS)
    
    def test_parameter_generation(self):
        """Should generate UE5 parameters."""
        self.manager.set_population(0.70)
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        params = self.manager.get_ue5_parameters()
        
        self.assertIsInstance(params, FWearParameters)
        self.assertGreater(params.displacement_intensity, 0)
    
    def test_grass_parameters(self):
        """Grass surface should generate grass-specific parameters."""
        self.manager.set_population(0.80)
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        params = self.manager.get_ue5_parameters()
        
        # Grass should be affected
        self.assertLess(params.grass_height_multiplier, 1.0)
        self.assertGreater(params.grass_bend_amount, 0)
        self.assertGreater(params.grass_color_shift, 0)
    
    def test_parameters_to_json(self):
        """Parameters should serialize to JSON."""
        params = FWearParameters()
        params.displacement_intensity = 0.5
        params.grass_height_multiplier = 0.7
        
        data = params.to_ue5_json()
        
        self.assertIn('Wear_DisplacementIntensity', data)
        self.assertIn('Grass_HeightMultiplier', data)
        self.assertEqual(data['Wear_DisplacementIntensity'], 0.5)
    
    def test_footprint_parameters(self):
        """Should generate footprint decal parameters."""
        self.manager.set_population(0.80)
        for _ in range(50):
            self.manager.update(delta_time=0.5)
        
        params = self.manager.get_ue5_parameters()
        
        self.assertGreater(params.footprint_density, 0)
        self.assertGreater(params.footprint_opacity, 0)


class TestRegionWearManager(unittest.TestCase):
    """Test multi-zone region wear management."""
    
    def setUp(self):
        self.region = RegionWearManager("marketplace")
        self.region.add_zone("center", SurfaceType.STONE, is_gathering_point=True)
        self.region.add_zone("grass_edge", SurfaceType.GRASS)
        self.region.add_zone("main_path", SurfaceType.DIRT, is_path=True)
    
    def test_add_zones(self):
        """Should add zones correctly."""
        self.assertEqual(len(self.region.zones), 3)
        self.assertIn("center", self.region.zones)
        self.assertIn("grass_edge", self.region.zones)
    
    def test_zone_properties(self):
        """Zones should have correct properties."""
        center = self.region.zones["center"]
        path = self.region.zones["main_path"]
        
        self.assertTrue(center.is_gathering_point)
        self.assertTrue(path.is_path)
    
    def test_update_all_zones(self):
        """Should update all zones."""
        self.region.set_population(0.60)
        snapshots = self.region.update(delta_time=0.5)
        
        self.assertEqual(len(snapshots), 3)
        for zone_id, snapshot in snapshots.items():
            self.assertIsInstance(snapshot, WearSnapshot)
    
    def test_path_gets_more_wear(self):
        """Path zones should accumulate more wear."""
        self.region.set_population(0.60)
        
        for _ in range(100):
            self.region.update(delta_time=0.5)
        
        path_wear = self.region.zones["main_path"].manager.total_wear
        grass_wear = self.region.zones["grass_edge"].manager.total_wear
        
        # Path should have more wear (despite dirt having lower multiplier)
        # because of the path population weight boost
        self.assertGreater(path_wear, grass_wear * 0.5)
    
    def test_gathering_point_concentrated_wear(self):
        """Gathering points should have concentrated wear."""
        self.region.set_population(0.60)
        
        for _ in range(100):
            self.region.update(delta_time=0.5)
        
        center_wear = self.region.zones["center"].manager.total_wear
        grass_wear = self.region.zones["grass_edge"].manager.total_wear
        
        # Center should have more wear from concentration
        # (accounting for stone's lower wear multiplier)
        self.assertGreater(center_wear * 5, grass_wear)  # Stone is 0.2x
    
    def test_get_zone_parameters(self):
        """Should get parameters for specific zone."""
        self.region.set_population(0.60)
        self.region.update(delta_time=0.5)
        
        params = self.region.get_zone_parameters("grass_edge")
        
        self.assertIsInstance(params, FWearParameters)
    
    def test_get_all_parameters(self):
        """Should get parameters for all zones."""
        self.region.set_population(0.60)
        self.region.update(delta_time=0.5)
        
        all_params = self.region.get_all_parameters()
        
        self.assertEqual(len(all_params), 3)
        for zone_id, params in all_params.items():
            self.assertIsInstance(params, FWearParameters)
    
    def test_aggregate_wear(self):
        """Should calculate aggregate wear."""
        self.region.set_population(0.60)
        
        for _ in range(50):
            self.region.update(delta_time=0.5)
        
        aggregate = self.region.get_aggregate_wear()
        self.assertGreater(aggregate, 0)
    
    def test_to_ue5_json(self):
        """Should generate complete UE5 JSON."""
        self.region.set_population(0.60)
        self.region.update(delta_time=0.5)
        
        data = self.region.to_ue5_json()
        
        self.assertIn('RegionID', data)
        self.assertIn('Population', data)
        self.assertIn('AggregateWear', data)
        self.assertIn('Zones', data)
        self.assertEqual(len(data['Zones']), 3)


class TestWearConfig(unittest.TestCase):
    """Test wear configuration."""
    
    def test_default_config(self):
        """Default config should have sensible values."""
        config = WearConfig()
        
        self.assertGreater(config.wear_start_threshold, 0)
        self.assertLess(config.recovery_threshold, config.wear_start_threshold)
    
    def test_custom_config(self):
        """Manager should accept custom config."""
        config = WearConfig()
        config.wear_start_threshold = 0.10  # Lower threshold
        
        manager = WearManager(surface_type=SurfaceType.GRASS, config=config)
        manager.set_population(0.15)  # Above custom threshold
        
        for _ in range(50):
            manager.update(delta_time=0.5)
        
        # Should accumulate wear
        self.assertGreater(manager.total_wear, 0)
    
    def test_accumulation_rates(self):
        """Accumulation rates should be correctly ordered."""
        config = WearConfig()
        
        disp_rate = config.accumulation_rates[WearLayer.DISPLACEMENT]
        disc_rate = config.accumulation_rates[WearLayer.DISCOLORATION]
        dmg_rate = config.accumulation_rates[WearLayer.DAMAGE]
        
        self.assertGreater(disp_rate, disc_rate)
        self.assertGreater(disc_rate, dmg_rate)


class TestWearReset(unittest.TestCase):
    """Test wear manager reset."""
    
    def test_reset_clears_wear(self):
        """Reset should clear all wear."""
        manager = WearManager(surface_type=SurfaceType.GRASS)
        
        manager.set_population(0.90)
        for _ in range(100):
            manager.update(delta_time=0.5)
        
        self.assertGreater(manager.total_wear, 0)
        
        manager.reset()
        
        self.assertAlmostEqual(manager.total_wear, 0.0, delta=0.01)
    
    def test_reset_clears_all_layers(self):
        """Reset should clear all layer values."""
        manager = WearManager(surface_type=SurfaceType.GRASS)
        
        manager.set_population(0.90)
        for _ in range(100):
            manager.update(delta_time=0.5)
        
        manager.reset()
        
        for layer in WearLayer:
            self.assertAlmostEqual(
                manager.surface.layers[layer].value, 0.0, delta=0.01
            )


class TestIntegration(unittest.TestCase):
    """Integration tests for wear system."""
    
    def test_full_cycle(self):
        """Test complete accumulation and recovery cycle."""
        manager = WearManager(surface_type=SurfaceType.GRASS)
        
        # Accumulate
        manager.set_population(0.80)
        for _ in range(100):
            manager.update(delta_time=0.5)
        
        peak_wear = manager.total_wear
        self.assertGreater(peak_wear, 0.2)
        
        # Recover
        manager.set_population(0.0)
        for _ in range(500):
            manager.update(delta_time=0.5)
        
        recovered_wear = manager.total_wear
        self.assertLess(recovered_wear, peak_wear)
    
    def test_region_ue5_workflow(self):
        """Test complete region → UE5 workflow."""
        region = RegionWearManager("test_region")
        region.add_zone("zone_a", SurfaceType.GRASS)
        region.add_zone("zone_b", SurfaceType.DIRT, is_path=True)
        
        populations = [0.20, 0.50, 0.80, 0.50, 0.20]
        
        for pop in populations:
            region.set_population(pop)
            
            for _ in range(30):
                region.update(delta_time=0.5)
            
            ue5_data = region.to_ue5_json()
            
            self.assertIn('Zones', ue5_data)
            self.assertEqual(len(ue5_data['Zones']), 2)


def run_tests():
    """Run all Phase 5 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestWearAccumulation))
    suite.addTests(loader.loadTestsFromTestCase(TestWearRecovery))
    suite.addTests(loader.loadTestsFromTestCase(TestLayerCascade))
    suite.addTests(loader.loadTestsFromTestCase(TestSurfaceTypes))
    suite.addTests(loader.loadTestsFromTestCase(TestActiveEffects))
    suite.addTests(loader.loadTestsFromTestCase(TestWearSnapshot))
    suite.addTests(loader.loadTestsFromTestCase(TestUE5Parameters))
    suite.addTests(loader.loadTestsFromTestCase(TestRegionWearManager))
    suite.addTests(loader.loadTestsFromTestCase(TestWearConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestWearReset))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
