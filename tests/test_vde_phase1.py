"""
VDE Phase 1 Tests: Core VDE

Tests:
- VDI calculation across population levels
- Phase transitions
- Wildlife state machine with recovery lag
- Environmental wear accumulation/decay
- Output parameter generation
- Factor weight verification
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from vde import (
    VDICalculator, VDIResult, VDIFactors, VDEConfig,
    VisualPhase, WildlifeState,
    OutputGenerator, VDEOutputState,
    PostProcessParams, MaterialParams, SpawnParams,
    ParticleParams, MotionParams, AttractionParams,
)


class TestVisualPhases(unittest.TestCase):
    """Test phase determination from population."""
    
    def setUp(self):
        self.calc = VDICalculator()
    
    def test_pristine_phase(self):
        """Population 0-10% should be PRISTINE."""
        for pop in [0.0, 0.05, 0.09]:
            result = self.calc.calculate(population=pop, delta_time=0.5)
            self.assertEqual(result.phase, VisualPhase.PRISTINE,
                           f"Pop {pop} should be PRISTINE, got {result.phase}")
    
    def test_healthy_phase(self):
        """Population 10-20% should be HEALTHY."""
        for pop in [0.10, 0.15, 0.19]:
            result = self.calc.calculate(population=pop, delta_time=0.5)
            self.assertEqual(result.phase, VisualPhase.HEALTHY,
                           f"Pop {pop} should be HEALTHY, got {result.phase}")
    
    def test_occupied_phase(self):
        """Population 20-35% should be OCCUPIED."""
        for pop in [0.20, 0.28, 0.34]:
            result = self.calc.calculate(population=pop, delta_time=0.5)
            self.assertEqual(result.phase, VisualPhase.OCCUPIED,
                           f"Pop {pop} should be OCCUPIED, got {result.phase}")
    
    def test_busy_phase(self):
        """Population 35-50% should be BUSY."""
        for pop in [0.35, 0.42, 0.49]:
            result = self.calc.calculate(population=pop, delta_time=0.5)
            self.assertEqual(result.phase, VisualPhase.BUSY,
                           f"Pop {pop} should be BUSY, got {result.phase}")
    
    def test_crowded_phase(self):
        """Population 50-70% should be CROWDED."""
        for pop in [0.50, 0.60, 0.69]:
            result = self.calc.calculate(population=pop, delta_time=0.5)
            self.assertEqual(result.phase, VisualPhase.CROWDED,
                           f"Pop {pop} should be CROWDED, got {result.phase}")
    
    def test_saturated_phase(self):
        """Population 70%+ should be SATURATED."""
        for pop in [0.70, 0.85, 1.0]:
            result = self.calc.calculate(population=pop, delta_time=0.5)
            self.assertEqual(result.phase, VisualPhase.SATURATED,
                           f"Pop {pop} should be SATURATED, got {result.phase}")


class TestVDICalculation(unittest.TestCase):
    """Test VDI value calculation."""
    
    def setUp(self):
        self.calc = VDICalculator()
    
    def test_low_population_negative_vdi(self):
        """Low population should produce negative VDI (comfortable)."""
        # Run several ticks to stabilize
        for _ in range(20):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        
        self.assertLess(result.smoothed_vdi, 0,
                       "Low pop should have negative VDI")
    
    def test_high_population_positive_vdi(self):
        """High population should produce positive VDI (uncomfortable)."""
        for _ in range(30):
            result = self.calc.calculate(population=0.85, delta_time=0.5)
        
        self.assertGreater(result.smoothed_vdi, 0.3,
                          "High pop should have significant positive VDI")
    
    def test_vdi_range(self):
        """VDI should stay within -1.0 to 1.0."""
        for pop in [0.0, 0.25, 0.50, 0.75, 1.0]:
            for _ in range(20):
                result = self.calc.calculate(population=pop, delta_time=0.5)
            
            self.assertGreaterEqual(result.smoothed_vdi, -1.0)
            self.assertLessEqual(result.smoothed_vdi, 1.0)
    
    def test_vdi_increases_with_population(self):
        """VDI should generally increase with population."""
        values = []
        
        for pop in [0.10, 0.30, 0.50, 0.70, 0.90]:
            self.calc.reset()
            for _ in range(25):
                result = self.calc.calculate(population=pop, delta_time=0.5)
            values.append(result.smoothed_vdi)
        
        # Each value should be greater than or equal to previous
        for i in range(1, len(values)):
            self.assertGreaterEqual(values[i], values[i-1] - 0.05,
                                   f"VDI should increase: {values}")
    
    def test_smoothing_prevents_instant_changes(self):
        """VDI should change gradually, not instantly."""
        # Start at low population
        for _ in range(20):
            self.calc.calculate(population=0.10, delta_time=0.5)
        
        initial_vdi = self.calc.current_vdi
        
        # Jump to high population
        result = self.calc.calculate(population=0.90, delta_time=0.5)
        
        # Should not have jumped to final value
        self.assertLess(abs(result.smoothed_vdi - initial_vdi), 0.3,
                       "VDI should change gradually due to smoothing")


class TestWildlifeState(unittest.TestCase):
    """Test wildlife state machine."""
    
    def setUp(self):
        self.calc = VDICalculator()
    
    def test_wildlife_thriving_at_low_pop(self):
        """Wildlife should thrive at very low population."""
        for _ in range(30):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        
        self.assertEqual(result.wildlife_state, WildlifeState.THRIVING)
    
    def test_wildlife_absent_at_high_pop(self):
        """Wildlife should be absent at high population."""
        for _ in range(50):
            result = self.calc.calculate(population=0.80, delta_time=0.5)
        
        self.assertEqual(result.wildlife_state, WildlifeState.ABSENT)
    
    def test_wildlife_flees_fast(self):
        """Wildlife should flee quickly when population rises."""
        # Start thriving
        for _ in range(20):
            self.calc.calculate(population=0.05, delta_time=0.5)
        
        self.assertEqual(self.calc.wildlife_state, WildlifeState.THRIVING)
        
        # High population - wildlife should flee within 10 ticks
        for _ in range(15):
            result = self.calc.calculate(population=0.80, delta_time=0.5)
        
        self.assertNotEqual(result.wildlife_state, WildlifeState.THRIVING,
                           "Wildlife should have started fleeing")
    
    def test_wildlife_returns_slowly(self):
        """Wildlife should return slowly when population drops."""
        # Start with absent wildlife
        for _ in range(50):
            self.calc.calculate(population=0.90, delta_time=0.5)
        
        self.assertEqual(self.calc.wildlife_state, WildlifeState.ABSENT)
        
        # Drop population - wildlife should still be absent/retreating
        for _ in range(10):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        
        # Wildlife shouldn't have fully returned yet
        self.assertNotEqual(result.wildlife_state, WildlifeState.THRIVING,
                           "Wildlife should return slowly")
    
    def test_wildlife_visibility_tracks_state(self):
        """Wildlife visibility should correspond to state."""
        # Thriving = high visibility
        for _ in range(30):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        
        self.assertGreater(result.wildlife_visibility, 0.8)
        
        # Absent = low visibility
        self.calc.reset()
        for _ in range(50):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        
        self.assertLess(result.wildlife_visibility, 0.2)


class TestEnvironmentalWear(unittest.TestCase):
    """Test environmental wear accumulation and decay."""
    
    def setUp(self):
        self.calc = VDICalculator()
    
    def test_wear_accumulates_at_high_pop(self):
        """Wear should accumulate at high population."""
        self.assertEqual(self.calc.accumulated_wear, 0.0)
        
        for _ in range(50):
            self.calc.calculate(population=0.80, delta_time=0.5)
        
        self.assertGreater(self.calc.accumulated_wear, 0.1,
                          "Wear should have accumulated")
    
    def test_wear_decays_at_low_pop(self):
        """Wear should decay at low population."""
        # First accumulate some wear
        for _ in range(50):
            self.calc.calculate(population=0.80, delta_time=0.5)
        
        initial_wear = self.calc.accumulated_wear
        self.assertGreater(initial_wear, 0)
        
        # Now decay at low pop
        for _ in range(100):
            self.calc.calculate(population=0.05, delta_time=0.5)
        
        self.assertLess(self.calc.accumulated_wear, initial_wear,
                       "Wear should have decayed")
    
    def test_wear_maxes_at_one(self):
        """Wear should not exceed 1.0."""
        for _ in range(500):
            self.calc.calculate(population=1.0, delta_time=0.5)
        
        self.assertLessEqual(self.calc.accumulated_wear, 1.0)
    
    def test_wear_mins_at_zero(self):
        """Wear should not go below 0.0."""
        for _ in range(100):
            self.calc.calculate(population=0.0, delta_time=0.5)
        
        self.assertGreaterEqual(self.calc.accumulated_wear, 0.0)


class TestVDIFactors(unittest.TestCase):
    """Test VDI factor calculation."""
    
    def setUp(self):
        self.calc = VDICalculator()
    
    def test_comfort_factors_at_low_pop(self):
        """Low population should have comfort factors active."""
        for _ in range(20):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        
        factors = result.factors
        
        # Comfort factors should be negative
        self.assertLess(factors.comfort_total, 0,
                       "Comfort factors should be active at low pop")
        
        # Specific comfort factors
        self.assertLess(factors.motion_coherence, 0)
        self.assertLess(factors.visual_clarity, 0)
    
    def test_discomfort_factors_at_high_pop(self):
        """High population should have discomfort factors active."""
        for _ in range(50):
            result = self.calc.calculate(population=0.85, delta_time=0.5)
        
        factors = result.factors
        
        # Discomfort factors should be positive
        self.assertGreater(factors.discomfort_total, 0,
                          "Discomfort factors should be active at high pop")
        
        # Specific discomfort factors
        self.assertGreater(factors.motion_incoherence, 0)
        self.assertGreater(factors.wildlife_absence, 0)
    
    def test_wildlife_absence_factor(self):
        """Wildlife absence factor should track wildlife visibility."""
        # Low pop, wildlife present
        for _ in range(30):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        
        low_pop_absence = result.factors.wildlife_absence
        
        # High pop, wildlife absent
        self.calc.reset()
        for _ in range(50):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        
        high_pop_absence = result.factors.wildlife_absence
        
        self.assertGreater(high_pop_absence, low_pop_absence,
                          "Wildlife absence factor should be higher when wildlife gone")
    
    def test_environmental_wear_factor(self):
        """Environmental wear factor should track accumulated wear."""
        # No wear initially
        result = self.calc.calculate(population=0.50, delta_time=0.5)
        initial_wear_factor = result.factors.environmental_wear
        
        # Accumulate wear
        for _ in range(100):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        
        self.assertGreater(result.factors.environmental_wear, initial_wear_factor,
                          "Wear factor should increase with accumulated wear")


class TestOutputGenerator(unittest.TestCase):
    """Test output parameter generation."""
    
    def setUp(self):
        self.calc = VDICalculator()
        self.gen = OutputGenerator()
    
    def test_output_structure(self):
        """Output should have all required parameter groups."""
        result = self.calc.calculate(population=0.50, delta_time=0.5)
        output = self.gen.generate(result)
        
        self.assertIsInstance(output.post_process, PostProcessParams)
        self.assertIsInstance(output.materials, MaterialParams)
        self.assertIsInstance(output.spawning, SpawnParams)
        self.assertIsInstance(output.particles, ParticleParams)
        self.assertIsInstance(output.motion, MotionParams)
        self.assertIsInstance(output.attraction, AttractionParams)
    
    def test_post_process_at_high_vdi(self):
        """High VDI should produce post-process effects."""
        for _ in range(50):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        
        output = self.gen.generate(result)
        pp = output.post_process
        
        self.assertGreater(pp.bloom_intensity_mod, 0.1)
        self.assertGreater(pp.contrast_reduction, 0.1)
        self.assertGreater(pp.shadow_softness, 0.1)
        self.assertLess(pp.saturation_mod, 1.0)
        self.assertGreater(pp.haze_density, 0.05)
    
    def test_post_process_neutral_at_low_vdi(self):
        """Low VDI should have minimal post-process effects."""
        for _ in range(30):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        
        output = self.gen.generate(result)
        pp = output.post_process
        
        self.assertLess(pp.bloom_intensity_mod, 0.05)
        self.assertLess(pp.contrast_reduction, 0.05)
        self.assertGreaterEqual(pp.saturation_mod, 0.98)
    
    def test_spawning_wildlife_state(self):
        """Spawning params should reflect wildlife state."""
        # Low pop - thriving
        for _ in range(30):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        
        output = self.gen.generate(result)
        self.assertEqual(output.spawning.wildlife_state, "thriving")
        self.assertGreater(output.spawning.wildlife_spawn_rate, 0.8)
        
        # High pop - absent
        self.calc.reset()
        for _ in range(50):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        
        output = self.gen.generate(result)
        self.assertEqual(output.spawning.wildlife_state, "absent")
        self.assertLess(output.spawning.wildlife_spawn_rate, 0.1)
    
    def test_motion_coherence_degrades(self):
        """Motion coherence should degrade with VDI."""
        # Low VDI - coherent
        for _ in range(30):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        
        output = self.gen.generate(result)
        self.assertGreater(output.motion.animation_phase_sync, 0.95)
        self.assertLess(output.motion.wind_direction_variance, 0.05)
        
        # High VDI - incoherent
        self.calc.reset()
        for _ in range(50):
            result = self.calc.calculate(population=0.90, delta_time=0.5)
        
        output = self.gen.generate(result)
        self.assertLess(output.motion.animation_phase_sync, 0.85)
        self.assertGreater(output.motion.wind_direction_variance, 0.1)
    
    def test_attraction_at_low_pop(self):
        """Low population areas should have attraction params."""
        for _ in range(20):
            result = self.calc.calculate(population=0.05, delta_time=0.5)
        
        output = self.gen.generate(result)
        attr = output.attraction
        
        self.assertTrue(attr.is_attracting)
        self.assertGreater(attr.light_temp_boost, 50)
        self.assertGreater(attr.wildlife_spawn_bonus, 0.1)
    
    def test_no_attraction_at_high_pop(self):
        """High population areas should not attract."""
        for _ in range(30):
            result = self.calc.calculate(population=0.50, delta_time=0.5)
        
        output = self.gen.generate(result)
        self.assertFalse(output.attraction.is_attracting)
    
    def test_output_to_dict(self):
        """Output should serialize to dict."""
        result = self.calc.calculate(population=0.50, delta_time=0.5)
        output = self.gen.generate(result)
        
        d = output.to_dict()
        
        self.assertIn('post_process', d)
        self.assertIn('materials', d)
        self.assertIn('spawning', d)
        self.assertIn('particles', d)
        self.assertIn('motion', d)
        self.assertIn('attraction', d)
        self.assertIn('phase', d)
        self.assertIn('vdi', d)


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading."""
    
    def test_default_config(self):
        """Calculator should work with default config."""
        calc = VDICalculator()
        result = calc.calculate(population=0.50, delta_time=0.5)
        
        self.assertIsInstance(result, VDIResult)
    
    def test_custom_config(self):
        """Calculator should accept custom config."""
        config = VDEConfig()
        config.pristine_max = 0.05  # Smaller pristine range
        
        calc = VDICalculator(config=config)
        
        # 7% should now be HEALTHY, not PRISTINE
        result = calc.calculate(population=0.07, delta_time=0.5)
        self.assertEqual(result.phase, VisualPhase.HEALTHY)
    
    def test_config_from_json(self):
        """Config should load from JSON file."""
        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'config', 'vde.json'
        )
        
        if os.path.exists(config_path):
            config = VDEConfig.from_json(config_path)
            calc = VDICalculator(config=config)
            result = calc.calculate(population=0.50, delta_time=0.5)
            
            self.assertIsInstance(result, VDIResult)


class TestReset(unittest.TestCase):
    """Test state reset functionality."""
    
    def test_calculator_reset(self):
        """Reset should clear all state."""
        calc = VDICalculator()
        
        # Accumulate state
        for _ in range(50):
            calc.calculate(population=0.90, delta_time=0.5)
        
        self.assertGreater(calc.current_vdi, 0)
        self.assertGreater(calc.accumulated_wear, 0)
        self.assertNotEqual(calc.wildlife_state, WildlifeState.THRIVING)
        
        # Reset
        calc.reset()
        
        self.assertEqual(calc.current_vdi, 0.0)
        self.assertEqual(calc.accumulated_wear, 0.0)
        self.assertEqual(calc.wildlife_state, WildlifeState.THRIVING)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflow."""
    
    def test_full_population_sweep(self):
        """Test complete population sweep with outputs."""
        calc = VDICalculator()
        gen = OutputGenerator()
        
        results = []
        
        for pop in [0.05, 0.15, 0.25, 0.40, 0.55, 0.75, 0.95]:
            calc.reset()
            
            # Stabilize
            for _ in range(30):
                result = calc.calculate(population=pop, delta_time=0.5)
            
            output = gen.generate(result)
            results.append({
                'pop': pop,
                'phase': result.phase.value,
                'vdi': result.smoothed_vdi,
                'wildlife': result.wildlife_state.value,
                'bloom': output.post_process.bloom_intensity_mod,
            })
        
        # Verify progression
        for i in range(1, len(results)):
            self.assertGreaterEqual(
                results[i]['vdi'], 
                results[i-1]['vdi'] - 0.1,
                f"VDI should increase with population"
            )
    
    def test_population_spike_and_recovery(self):
        """Test rapid population change and recovery."""
        calc = VDICalculator()
        gen = OutputGenerator()
        
        # Start peaceful
        for _ in range(30):
            result = calc.calculate(population=0.05, delta_time=0.5)
        
        initial_vdi = result.smoothed_vdi
        initial_wildlife = result.wildlife_visibility
        
        self.assertLess(initial_vdi, 0)
        self.assertGreater(initial_wildlife, 0.8)
        
        # Spike to crowded
        for _ in range(30):
            result = calc.calculate(population=0.85, delta_time=0.5)
        
        spike_vdi = result.smoothed_vdi
        spike_wildlife = result.wildlife_visibility
        
        self.assertGreater(spike_vdi, 0.3)
        self.assertLess(spike_wildlife, 0.5)
        
        # Recover
        for _ in range(60):
            result = calc.calculate(population=0.05, delta_time=0.5)
        
        recovered_vdi = result.smoothed_vdi
        
        # Should be recovering toward initial
        self.assertLess(recovered_vdi, spike_vdi)


def run_tests():
    """Run all Phase 1 tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestVisualPhases))
    suite.addTests(loader.loadTestsFromTestCase(TestVDICalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestWildlifeState))
    suite.addTests(loader.loadTestsFromTestCase(TestEnvironmentalWear))
    suite.addTests(loader.loadTestsFromTestCase(TestVDIFactors))
    suite.addTests(loader.loadTestsFromTestCase(TestOutputGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestReset))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
