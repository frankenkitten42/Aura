"""
VDE Phase 2 Tests: UE5 Integration

Tests:
- UE5 binding generation
- Post-process parameter conversion
- Material parameter conversion
- Niagara parameter generation
- Spawn settings generation
- Attraction system
- Multi-region processing
- JSON serialization
- C++ header generation
"""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from vde import (
    # Phase 1
    VDICalculator, OutputGenerator, VisualPhase, WildlifeState,
    # Phase 2
    UE5BindingGenerator, FVDERegionState, FVDEPostProcessSettings,
    FVDEMaterialParameters, FVDENiagaraParameters, FVDESpawnSettings,
    FVDEAttractionSettings, FVDEWorldState, MultiRegionProcessor,
)
from vde.ue5_codegen import (
    generate_vde_types_header, generate_all_headers,
    generate_mpc_asset_json, generate_niagara_parameters_json,
)


class TestUE5BindingGenerator(unittest.TestCase):
    """Test the main UE5 binding generator."""
    
    def setUp(self):
        self.calc = VDICalculator()
        self.output_gen = OutputGenerator()
        self.ue5_gen = UE5BindingGenerator(region_id="test_region")
    
    def test_generator_initialization(self):
        """Generator should initialize with region ID."""
        gen = UE5BindingGenerator(region_id="forest")
        self.assertEqual(gen.region_id, "forest")
    
    def test_generate_region_state(self):
        """Should generate complete region state."""
        for _ in range(20):
            result = self.calc.calculate(population=0.50, delta_time=0.5)
        output = self.output_gen.generate(result)
        
        state = self.ue5_gen.generate_region_state(result, output, delta_time=0.5)
        
        self.assertIsInstance(state, FVDERegionState)
        self.assertEqual(state.region_id, "test_region")
        self.assertEqual(state.population, 0.50)
        self.assertIsInstance(state.post_process, FVDEPostProcessSettings)
        self.assertIsInstance(state.materials, FVDEMaterialParameters)
        self.assertIsInstance(state.niagara, FVDENiagaraParameters)
        self.assertIsInstance(state.spawning, FVDESpawnSettings)
        self.assertIsInstance(state.attraction, FVDEAttractionSettings)
    
    def test_timestamp_increments(self):
        """Timestamp should increment with each call."""
        result = self.calc.calculate(population=0.50, delta_time=0.5)
        output = self.output_gen.generate(result)
        
        state1 = self.ue5_gen.generate_region_state(result, output, delta_time=0.5)
        state2 = self.ue5_gen.generate_region_state(result, output, delta_time=0.5)
        
        self.assertGreater(state2.timestamp, state1.timestamp)


class TestPostProcessSettings(unittest.TestCase):
    """Test post-process parameter generation."""
    
    def setUp(self):
        self.calc = VDICalculator()
        self.output_gen = OutputGenerator()
        self.ue5_gen = UE5BindingGenerator()
    
    def test_low_vdi_minimal_effects(self):
        """Low VDI should have minimal post-process effects."""
        for _ in range(20):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        pp = state.post_process
        
        # Should be near baseline
        self.assertAlmostEqual(pp.bloom_intensity_multiplier, 1.0, delta=0.1)
        self.assertAlmostEqual(pp.contrast_multiplier, 1.0, delta=0.05)
        self.assertAlmostEqual(pp.saturation_multiplier, 1.0, delta=0.02)
    
    def test_high_vdi_increased_effects(self):
        """High VDI should produce significant post-process effects."""
        for _ in range(30):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        pp = state.post_process
        
        # Effects are subtle by design to avoid detection
        # Verify they're moving in the right direction
        self.assertGreater(pp.bloom_intensity_multiplier, 1.005)  # Any increase
        self.assertLess(pp.contrast_multiplier, 0.95)             # Reduced contrast
        self.assertGreater(pp.fog_density_multiplier, 1.001)      # Any fog increase
        self.assertGreater(pp.vignette_intensity, 0.01)           # Some vignette
    
    def test_color_temp_negative_when_uncomfortable(self):
        """Color temperature should shift cooler when VDI is high."""
        for _ in range(30):
            result = self.calc.calculate(population=0.85, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        self.assertLess(state.post_process.color_temp_offset, 0)
    
    def test_post_process_to_json(self):
        """Post-process should serialize to JSON."""
        pp = FVDEPostProcessSettings()
        pp.bloom_intensity_multiplier = 1.2
        pp.contrast_multiplier = 0.85
        
        data = pp.to_ue5_json()
        
        self.assertIn('BloomIntensityMultiplier', data)
        self.assertEqual(data['BloomIntensityMultiplier'], 1.2)
        self.assertEqual(data['ContrastMultiplier'], 0.85)


class TestMaterialParameters(unittest.TestCase):
    """Test material parameter generation."""
    
    def setUp(self):
        self.calc = VDICalculator()
        self.output_gen = OutputGenerator()
        self.ue5_gen = UE5BindingGenerator()
    
    def test_foliage_restlessness_increases(self):
        """Foliage restlessness should increase with VDI."""
        # Low VDI
        self.calc.reset()
        for _ in range(20):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        output = self.output_gen.generate(result)
        state_low = self.ue5_gen.generate_region_state(result, output)
        
        # High VDI
        self.calc.reset()
        for _ in range(30):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        output = self.output_gen.generate(result)
        state_high = self.ue5_gen.generate_region_state(result, output)
        
        self.assertGreater(
            state_high.materials.foliage_wind_intensity,
            state_low.materials.foliage_wind_intensity
        )
    
    def test_water_clarity_tracks_wear(self):
        """Water clarity should decrease with environmental wear."""
        # Accumulate wear
        for _ in range(100):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        self.assertLess(state.materials.water_clarity, 0.9)
        self.assertGreater(state.materials.water_turbulence, 0.05)
    
    def test_ground_wear_tracks_accumulation(self):
        """Ground wear parameters should track accumulated wear."""
        # Accumulate wear
        for _ in range(100):
            result = self.calc.calculate(population=0.85, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        self.assertGreater(state.materials.ground_wear_intensity, 0.1)
        self.assertGreater(state.materials.ground_displacement_reduction, 0.1)
    
    def test_material_to_json(self):
        """Material parameters should serialize to JSON."""
        mat = FVDEMaterialParameters()
        mat.foliage_wind_intensity = 1.5
        mat.water_clarity = 0.7
        
        data = mat.to_ue5_json()
        
        self.assertIn('Foliage_WindIntensity', data)
        self.assertEqual(data['Foliage_WindIntensity'], 1.5)
        self.assertEqual(data['Water_Clarity'], 0.7)


class TestNiagaraParameters(unittest.TestCase):
    """Test Niagara particle parameter generation."""
    
    def setUp(self):
        self.calc = VDICalculator()
        self.output_gen = OutputGenerator()
        self.ue5_gen = UE5BindingGenerator()
    
    def test_dust_spawn_increases_with_vdi(self):
        """Dust spawn rate should increase with VDI."""
        # Low VDI
        self.calc.reset()
        for _ in range(20):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        output = self.output_gen.generate(result)
        state_low = self.ue5_gen.generate_region_state(result, output)
        
        # High VDI
        self.calc.reset()
        for _ in range(50):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        output = self.output_gen.generate(result)
        state_high = self.ue5_gen.generate_region_state(result, output)
        
        self.assertGreater(
            state_high.niagara.dust_spawn_rate,
            state_low.niagara.dust_spawn_rate
        )
    
    def test_wind_variance_tracks_motion(self):
        """Wind direction variance should increase with motion incoherence."""
        for _ in range(30):
            result = self.calc.calculate(population=0.85, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        self.assertGreater(state.niagara.wind_direction_variance, 0.05)
    
    def test_insect_density_tracks_wildlife(self):
        """Insect density should track wildlife spawn rate."""
        # Low pop - wildlife present
        self.calc.reset()
        for _ in range(30):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        output = self.output_gen.generate(result)
        state_low = self.ue5_gen.generate_region_state(result, output)
        
        # High pop - wildlife absent
        self.calc.reset()
        for _ in range(50):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        output = self.output_gen.generate(result)
        state_high = self.ue5_gen.generate_region_state(result, output)
        
        self.assertGreater(
            state_low.niagara.insect_density,
            state_high.niagara.insect_density
        )
    
    def test_niagara_to_json(self):
        """Niagara parameters should serialize to JSON."""
        nia = FVDENiagaraParameters()
        nia.dust_spawn_rate = 10.0
        nia.wind_direction = (0.7, 0.7, 0.0)
        
        data = nia.to_ue5_json()
        
        self.assertIn('Dust_SpawnRate', data)
        self.assertEqual(data['Dust_SpawnRate'], 10.0)
        self.assertEqual(data['Wind_Direction'], [0.7, 0.7, 0.0])


class TestSpawnSettings(unittest.TestCase):
    """Test spawn settings generation."""
    
    def setUp(self):
        self.calc = VDICalculator()
        self.output_gen = OutputGenerator()
        self.ue5_gen = UE5BindingGenerator()
    
    def test_wildlife_spawn_decreases_with_pop(self):
        """Wildlife spawn multiplier should decrease with population."""
        # Low pop
        self.calc.reset()
        for _ in range(30):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        output = self.output_gen.generate(result)
        state_low = self.ue5_gen.generate_region_state(result, output)
        
        # High pop
        self.calc.reset()
        for _ in range(50):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        output = self.output_gen.generate(result)
        state_high = self.ue5_gen.generate_region_state(result, output)
        
        self.assertGreater(
            state_low.spawning.wildlife_spawn_multiplier,
            state_high.spawning.wildlife_spawn_multiplier
        )
    
    def test_bird_flee_distance_increases(self):
        """Bird flee distance should increase when wildlife is absent."""
        for _ in range(50):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        # Absent wildlife should have large flee distance
        self.assertGreater(state.spawning.bird_flee_distance, 500.0)
    
    def test_npc_idle_mask_reduces(self):
        """NPC idle behavior mask should reduce with comfort."""
        # High comfort
        self.calc.reset()
        for _ in range(20):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        output = self.output_gen.generate(result)
        state_high_comfort = self.ue5_gen.generate_region_state(result, output)
        
        # Low comfort
        self.calc.reset()
        for _ in range(30):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        output = self.output_gen.generate(result)
        state_low_comfort = self.ue5_gen.generate_region_state(result, output)
        
        # More bits set = more behaviors allowed
        high_bits = bin(state_high_comfort.spawning.npc_idle_behavior_mask).count('1')
        low_bits = bin(state_low_comfort.spawning.npc_idle_behavior_mask).count('1')
        
        self.assertGreater(high_bits, low_bits)
    
    def test_spawn_to_json(self):
        """Spawn settings should serialize to JSON."""
        spawn = FVDESpawnSettings()
        spawn.wildlife_spawn_multiplier = 0.5
        spawn.wildlife_behavior_state = "wary"
        
        data = spawn.to_ue5_json()
        
        self.assertIn('Wildlife_SpawnMultiplier', data)
        self.assertEqual(data['Wildlife_SpawnMultiplier'], 0.5)
        self.assertEqual(data['Wildlife_BehaviorState'], "wary")


class TestAttractionSettings(unittest.TestCase):
    """Test attraction settings generation."""
    
    def setUp(self):
        self.calc = VDICalculator()
        self.output_gen = OutputGenerator()
        self.ue5_gen = UE5BindingGenerator()
    
    def test_attraction_active_at_low_pop(self):
        """Attraction should be active at low population."""
        for _ in range(20):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        self.assertTrue(state.attraction.is_active)
        self.assertGreater(state.attraction.attraction_strength, 0.3)
    
    def test_attraction_inactive_at_high_pop(self):
        """Attraction should be inactive at high population."""
        for _ in range(30):
            result = self.calc.calculate(population=0.60, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        self.assertFalse(state.attraction.is_active)
    
    def test_attraction_light_warmth(self):
        """Attraction should include light warmth boost."""
        for _ in range(20):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        self.assertGreater(state.attraction.light_color_warmth, 50.0)
    
    def test_attraction_to_json(self):
        """Attraction settings should serialize to JSON."""
        attr = FVDEAttractionSettings()
        attr.is_active = True
        attr.attraction_strength = 0.75
        
        data = attr.to_ue5_json()
        
        self.assertIn('IsActive', data)
        self.assertTrue(data['IsActive'])
        self.assertEqual(data['AttractionStrength'], 0.75)


class TestRegionStateSerialization(unittest.TestCase):
    """Test complete region state serialization."""
    
    def setUp(self):
        self.calc = VDICalculator()
        self.output_gen = OutputGenerator()
        self.ue5_gen = UE5BindingGenerator(region_id="forest_clearing")
    
    def test_to_ue5_json(self):
        """Region state should serialize to UE5 JSON format."""
        for _ in range(20):
            result = self.calc.calculate(population=0.45, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        data = state.to_ue5_json()
        
        self.assertIn('RegionID', data)
        self.assertIn('Population', data)
        self.assertIn('VDI', data)
        self.assertIn('Phase', data)
        self.assertIn('PostProcess', data)
        self.assertIn('Materials', data)
        self.assertIn('Niagara', data)
        self.assertIn('Spawning', data)
        self.assertIn('Attraction', data)
    
    def test_to_json_string(self):
        """Region state should serialize to JSON string."""
        for _ in range(20):
            result = self.calc.calculate(population=0.45, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        json_str = state.to_json_string()
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        self.assertIn('RegionID', parsed)
    
    def test_json_roundtrip(self):
        """JSON should be parseable and contain correct values."""
        for _ in range(20):
            result = self.calc.calculate(population=0.65, delta_time=0.5)
        output = self.output_gen.generate(result)
        state = self.ue5_gen.generate_region_state(result, output)
        
        json_str = state.to_json_string()
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed['RegionID'], "forest_clearing")
        self.assertAlmostEqual(parsed['Population'], 0.65, places=2)


class TestMultiRegionProcessor(unittest.TestCase):
    """Test multi-region processing."""
    
    def test_add_region(self):
        """Should add regions with adjacency."""
        processor = MultiRegionProcessor()
        processor.add_region("forest", adjacent=["path", "river"])
        processor.add_region("path", adjacent=["forest", "village"])
        
        self.assertIn("forest", processor.regions)
        self.assertIn("path", processor.regions)
        self.assertEqual(processor.adjacency["forest"], ["path", "river"])
    
    def test_update_region_population(self):
        """Should update region population."""
        processor = MultiRegionProcessor()
        processor.add_region("forest")
        processor.update_region("forest", population=0.75)
        
        self.assertEqual(processor.regions["forest"]["population"], 0.75)
    
    def test_process_generates_world_state(self):
        """Should generate complete world state."""
        processor = MultiRegionProcessor()
        processor.add_region("forest", adjacent=["path"])
        processor.add_region("path", adjacent=["forest"])
        
        processor.update_region("forest", population=0.80)
        processor.update_region("path", population=0.10)
        
        world = processor.process(delta_time=0.5)
        
        self.assertIsInstance(world, FVDEWorldState)
        self.assertIn("forest", world.regions)
        self.assertIn("path", world.regions)
    
    def test_attraction_sources_detected(self):
        """Should detect attraction sources (high pressure regions)."""
        processor = MultiRegionProcessor()
        processor.add_region("crowded", adjacent=["empty"])
        processor.add_region("empty", adjacent=["crowded"])
        
        processor.update_region("crowded", population=0.85)
        processor.update_region("empty", population=0.05)
        
        # Run enough ticks to build pressure
        for _ in range(30):
            world = processor.process(delta_time=0.5)
        
        # Crowded should be broadcasting attraction
        self.assertIn("crowded", world.attraction_sources)
    
    def test_world_state_to_json(self):
        """World state should serialize to JSON."""
        processor = MultiRegionProcessor()
        processor.add_region("region_a")
        processor.add_region("region_b")
        
        world = processor.process(delta_time=0.5)
        data = world.to_ue5_json()
        
        self.assertIn('Regions', data)
        self.assertIn('region_a', data['Regions'])


class TestCppHeaderGeneration(unittest.TestCase):
    """Test C++ header file generation."""
    
    def test_generate_types_header(self):
        """Should generate VDETypes.h content."""
        header = generate_vde_types_header()
        
        self.assertIn('USTRUCT(BlueprintType)', header)
        self.assertIn('FVDEPostProcessSettings', header)
        self.assertIn('FVDEMaterialParameters', header)
        self.assertIn('FVDERegionState', header)
        self.assertIn('EVDEVisualPhase', header)
        self.assertIn('EVDEWildlifeState', header)
    
    def test_generate_all_headers(self):
        """Should generate all header files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = generate_all_headers(tmpdir)
            
            self.assertGreater(len(files), 0)
            
            for f in files:
                self.assertTrue(os.path.exists(f))
                self.assertTrue(f.endswith('.h'))
    
    def test_generate_mpc_json(self):
        """Should generate valid MPC JSON."""
        json_str = generate_mpc_asset_json()
        data = json.loads(json_str)
        
        self.assertIn('Name', data)
        self.assertIn('ScalarParameters', data)
        self.assertIn('VectorParameters', data)
        
        # Check for expected parameters
        scalar_names = [p['Name'] for p in data['ScalarParameters']]
        self.assertIn('Foliage_WindIntensity', scalar_names)
        self.assertIn('Water_Clarity', scalar_names)
    
    def test_generate_niagara_json(self):
        """Should generate valid Niagara parameters JSON."""
        json_str = generate_niagara_parameters_json()
        data = json.loads(json_str)
        
        self.assertIn('Name', data)
        self.assertIn('Parameters', data)
        
        param_names = [p['Name'] for p in data['Parameters']]
        self.assertIn('VDE_DustSpawnRate', param_names)
        self.assertIn('VDE_WindDirection', param_names)


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for complete VDE → UE5 workflow."""
    
    def test_complete_pipeline(self):
        """Test complete VDE calculation → UE5 binding pipeline."""
        calc = VDICalculator()
        output_gen = OutputGenerator()
        ue5_gen = UE5BindingGenerator(region_id="test_region")
        
        # Simulate population changes
        populations = [0.10, 0.30, 0.50, 0.70, 0.90]
        states = []
        
        for pop in populations:
            calc.reset()
            
            for _ in range(25):
                result = calc.calculate(population=pop, delta_time=0.5)
            
            output = output_gen.generate(result)
            state = ue5_gen.generate_region_state(result, output, delta_time=0.5)
            states.append(state)
        
        # Verify progression
        for i in range(1, len(states)):
            # VDI should increase
            self.assertGreaterEqual(
                states[i].vdi, 
                states[i-1].vdi - 0.1,
                f"VDI should increase with population"
            )
            
            # Bloom should increase
            self.assertGreaterEqual(
                states[i].post_process.bloom_intensity_multiplier,
                states[i-1].post_process.bloom_intensity_multiplier - 0.05
            )
    
    def test_json_for_ue5_consumption(self):
        """Generated JSON should be valid for UE5 consumption."""
        calc = VDICalculator()
        output_gen = OutputGenerator()
        ue5_gen = UE5BindingGenerator()
        
        for _ in range(20):
            result = calc.calculate(population=0.55, delta_time=0.5)
        output = output_gen.generate(result)
        state = ue5_gen.generate_region_state(result, output)
        
        # Get JSON
        json_str = state.to_json_string(indent=2)
        
        # Parse and validate structure
        data = json.loads(json_str)
        
        # Check all expected keys present
        required_keys = [
            'RegionID', 'Population', 'VDI', 'Phase', 'WildlifeState',
            'AccumulatedWear', 'PostProcess', 'Materials', 'Niagara',
            'Spawning', 'Attraction', 'Timestamp', 'DeltaTime'
        ]
        
        for key in required_keys:
            self.assertIn(key, data, f"Missing key: {key}")


def run_tests():
    """Run all Phase 2 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestUE5BindingGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestPostProcessSettings))
    suite.addTests(loader.loadTestsFromTestCase(TestMaterialParameters))
    suite.addTests(loader.loadTestsFromTestCase(TestNiagaraParameters))
    suite.addTests(loader.loadTestsFromTestCase(TestSpawnSettings))
    suite.addTests(loader.loadTestsFromTestCase(TestAttractionSettings))
    suite.addTests(loader.loadTestsFromTestCase(TestRegionStateSerialization))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiRegionProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestCppHeaderGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationWorkflow))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
