#!/usr/bin/env python3
"""
VDE Phase 1 Interactive Simulator

Demonstrates the Visual Discomfort Engine in action.

Usage:
    python vde_simulate.py [--seed N]
    
Commands:
    pop N       - Set population to N%
    tick [N]    - Run N ticks (default: 1)
    status      - Show current VDE state
    factors     - Show VDI factor breakdown
    output      - Show UE5 output parameters
    wildlife    - Show wildlife state details
    wear        - Show environmental wear details
    scenario X  - Run predefined scenario
    reset       - Reset all state
    help        - Show this help
    quit        - Exit simulator
"""

import sys
import os
import argparse
import cmd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vde import (
    VDICalculator, VDEConfig, OutputGenerator,
    VisualPhase, WildlifeState
)


class VDESimulator(cmd.Cmd):
    """Interactive VDE simulator."""
    
    intro = """
╔═══════════════════════════════════════════════════════════════════╗
║           VDE Phase 1: Core Visual Discomfort Engine              ║
╠═══════════════════════════════════════════════════════════════════╣
║  Commands: pop N, tick [N], status, factors, output, reset, quit  ║
║  Scenarios: sweep, spike, recovery, wear                          ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    prompt = 'vde> '
    
    def __init__(self, seed: int = None):
        super().__init__()
        
        # Load config if available
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'vde.json')
        if os.path.exists(config_path):
            self.config = VDEConfig.from_json(config_path)
        else:
            self.config = VDEConfig()
        
        self.calc = VDICalculator(config=self.config)
        self.gen = OutputGenerator()
        
        self.population = 0.10
        self.tick_count = 0
        self.last_result = None
        self.last_output = None
        
        # Initialize with a few ticks
        for _ in range(5):
            self._do_tick()
    
    def _do_tick(self, count: int = 1):
        """Run simulation ticks."""
        for _ in range(count):
            self.last_result = self.calc.calculate(
                population=self.population,
                delta_time=0.5
            )
            self.last_output = self.gen.generate(self.last_result)
            self.tick_count += 1
    
    def do_pop(self, arg):
        """Set population percentage: pop 45"""
        try:
            value = float(arg)
            if 0 <= value <= 100:
                self.population = value / 100.0
                print(f"Population set to {value:.0f}%")
            else:
                print("Population must be 0-100")
        except ValueError:
            print("Usage: pop <percentage>")
    
    def do_tick(self, arg):
        """Run simulation ticks: tick [count]"""
        try:
            count = int(arg) if arg else 1
            self._do_tick(count)
            self._show_brief_status()
        except ValueError:
            print("Usage: tick [count]")
    
    def do_status(self, arg):
        """Show current VDE status."""
        if not self.last_result:
            print("No data yet. Run 'tick' first.")
            return
        
        r = self.last_result
        o = self.last_output
        
        print()
        print("╔════════════════════════════════════════════════════════╗")
        print("║                    VDE STATUS                          ║")
        print("╠════════════════════════════════════════════════════════╣")
        print(f"║  Tick: {self.tick_count:4d}        Population: {self.population*100:5.1f}%            ║")
        print("╠════════════════════════════════════════════════════════╣")
        print(f"║  Phase: {r.phase.value.upper():12s}                             ║")
        print(f"║  VDI:   {r.smoothed_vdi:+.3f} (raw: {r.raw_vdi:+.3f}, target: {r.target_vdi:+.3f}) ║")
        print(f"║  Delta: {r.delta:+.3f} ({r.delta_category})                         ║")
        print("╠════════════════════════════════════════════════════════╣")
        print(f"║  Wildlife: {r.wildlife_state.value:12s} (visibility: {r.wildlife_visibility:.0%})    ║")
        print(f"║  Wear:     {r.accumulated_wear:.0%}                                      ║")
        print("╠════════════════════════════════════════════════════════╣")
        print("║  Key Outputs:                                          ║")
        print(f"║    Bloom:       {o.post_process.bloom_intensity_mod:.3f}                            ║")
        print(f"║    Haze:        {o.post_process.haze_density:.3f}                            ║")
        print(f"║    Foliage:     {o.materials.foliage_restlessness:.3f} (restlessness)          ║")
        print(f"║    Ground Wear: {o.materials.ground_wear:.3f}                            ║")
        print(f"║    Motion Sync: {o.motion.animation_phase_sync:.3f}                            ║")
        print("╚════════════════════════════════════════════════════════╝")
        print()
    
    def _show_brief_status(self):
        """Show brief status after tick."""
        if not self.last_result:
            return
        
        r = self.last_result
        print(f"[Tick {self.tick_count}] Phase: {r.phase.value:10s} VDI: {r.smoothed_vdi:+.3f} "
              f"Wildlife: {r.wildlife_state.value:10s} Wear: {r.accumulated_wear:.0%}")
    
    def do_factors(self, arg):
        """Show VDI factor breakdown."""
        if not self.last_result:
            print("No data yet. Run 'tick' first.")
            return
        
        f = self.last_result.factors
        
        print()
        print("═══════════════ VDI FACTORS ═══════════════")
        print()
        print("DISCOMFORT (positive):")
        print(f"  motion_incoherence:   {f.motion_incoherence:+.4f}")
        print(f"  visual_density:       {f.visual_density:+.4f}")
        print(f"  light_diffusion:      {f.light_diffusion:+.4f}")
        print(f"  environmental_wear:   {f.environmental_wear:+.4f}")
        print(f"  wildlife_absence:     {f.wildlife_absence:+.4f}")
        print(f"  npc_unease:           {f.npc_unease:+.4f}")
        print(f"  spatial_noise:        {f.spatial_noise:+.4f}")
        print(f"  ─────────────────────────────────")
        print(f"  SUBTOTAL:             {f.discomfort_total:+.4f}")
        print()
        print("COMFORT (negative):")
        print(f"  motion_coherence:     {f.motion_coherence:+.4f}")
        print(f"  visual_clarity:       {f.visual_clarity:+.4f}")
        print(f"  light_quality:        {f.light_quality:+.4f}")
        print(f"  environmental_health: {f.environmental_health:+.4f}")
        print(f"  wildlife_presence:    {f.wildlife_presence:+.4f}")
        print(f"  npc_comfort:          {f.npc_comfort:+.4f}")
        print(f"  spatial_invitation:   {f.spatial_invitation:+.4f}")
        print(f"  ─────────────────────────────────")
        print(f"  SUBTOTAL:             {f.comfort_total:+.4f}")
        print()
        print(f"═══════════════════════════════════════════")
        print(f"  NET VDI:              {f.total:+.4f}")
        print()
    
    def do_output(self, arg):
        """Show UE5 output parameters."""
        if not self.last_output:
            print("No data yet. Run 'tick' first.")
            return
        
        o = self.last_output
        
        print()
        print("═══════════════ UE5 OUTPUT PARAMETERS ═══════════════")
        print()
        print("POST-PROCESS:")
        pp = o.post_process
        print(f"  bloom_intensity_mod:  {pp.bloom_intensity_mod:.4f}")
        print(f"  contrast_reduction:   {pp.contrast_reduction:.4f}")
        print(f"  shadow_softness:      {pp.shadow_softness:.4f}")
        print(f"  saturation_mod:       {pp.saturation_mod:.4f}")
        print(f"  haze_density:         {pp.haze_density:.4f}")
        print(f"  vignette:             {pp.vignette:.4f}")
        print(f"  color_temp_shift:     {pp.color_temp_shift:.1f}K")
        print()
        print("MATERIALS:")
        m = o.materials
        print(f"  foliage_restlessness: {m.foliage_restlessness:.4f}")
        print(f"  cloth_settle_time:    {m.cloth_settle_time:.2f}s")
        print(f"  water_clarity:        {m.water_clarity:.4f}")
        print(f"  ground_wear:          {m.ground_wear:.4f}")
        print(f"  prop_jitter:          {m.prop_jitter:.4f}")
        print(f"  grass_trampling:      {m.grass_trampling:.4f}")
        print()
        print("SPAWNING:")
        s = o.spawning
        print(f"  wildlife_spawn_rate:  {s.wildlife_spawn_rate:.2f}")
        print(f"  bird_landing_chance:  {s.bird_landing_chance:.2f}")
        print(f"  npc_idle_variety:     {s.npc_idle_variety:.2f}")
        print(f"  npc_comfort_level:    {s.npc_comfort_level:.2f}")
        print(f"  wildlife_state:       {s.wildlife_state}")
        print()
        print("MOTION:")
        mo = o.motion
        print(f"  wind_variance:        {mo.wind_direction_variance:.4f}")
        print(f"  animation_sync:       {mo.animation_phase_sync:.4f}")
        print(f"  foliage_coherence:    {mo.foliage_wave_coherence:.4f}")
        print(f"  cloth_rest:           {mo.cloth_rest_achieved:.4f}")
        print(f"  prop_stability:       {mo.prop_stability:.4f}")
        print()
        print("PARTICLES:")
        p = o.particles
        print(f"  dust_density:         {p.dust_density:.4f}")
        print(f"  pollen_intensity:     {p.pollen_intensity:.4f}")
        print(f"  debris_frequency:     {p.debris_frequency:.4f}")
        print(f"  particle_coherence:   {p.particle_coherence:.4f}")
        print()
        if o.attraction.is_attracting:
            print("ATTRACTION (active):")
            a = o.attraction
            print(f"  light_temp_boost:     {a.light_temp_boost:.1f}K")
            print(f"  god_ray_probability:  {a.god_ray_probability:.2f}")
            print(f"  wildlife_spawn_bonus: {a.wildlife_spawn_bonus:.2f}")
            print(f"  discovery_visibility: {a.discovery_visibility:.2f}")
            print()
    
    def do_wildlife(self, arg):
        """Show wildlife state details."""
        if not self.last_result:
            print("No data yet. Run 'tick' first.")
            return
        
        r = self.last_result
        s = self.last_output.spawning
        
        print()
        print("═══════════════ WILDLIFE STATE ═══════════════")
        print()
        print(f"  Current State:   {r.wildlife_state.value.upper()}")
        print(f"  Visibility:      {r.wildlife_visibility:.0%}")
        print()
        print("  Spawn Rates:")
        print(f"    Wildlife:      {s.wildlife_spawn_rate:.0%}")
        print(f"    Birds Landing: {s.bird_landing_chance:.0%}")
        print(f"    Insects:       {s.insect_density:.0%}")
        print(f"    Ambient:       {s.ambient_creature_rate:.0%}")
        print()
        print("  State Thresholds:")
        print(f"    THRIVING:   pop < {self.config.wildlife_thriving_max:.0%}")
        print(f"    WARY:       pop < {self.config.wildlife_wary_max:.0%}")
        print(f"    RETREATING: pop < {self.config.wildlife_retreating_max:.0%}")
        print(f"    ABSENT:     pop >= {self.config.wildlife_retreating_max:.0%}")
        print()
    
    def do_wear(self, arg):
        """Show environmental wear details."""
        if not self.last_result:
            print("No data yet. Run 'tick' first.")
            return
        
        r = self.last_result
        m = self.last_output.materials
        
        print()
        print("═══════════════ ENVIRONMENTAL WEAR ═══════════════")
        print()
        print(f"  Accumulated Wear: {r.accumulated_wear:.1%}")
        print()
        print("  Material Effects:")
        print(f"    Ground Wear:     {m.ground_wear:.2f}")
        print(f"    Water Clarity:   {m.water_clarity:.2f}")
        print(f"    Grass Trampling: {m.grass_trampling:.2f}")
        print()
        print("  Thresholds:")
        print(f"    Growth starts:  pop > {self.config.wear_growth_threshold:.0%}")
        print(f"    Decay starts:   pop < {self.config.wear_decay_threshold:.0%}")
        print()
        
        # Progress bar
        wear_pct = int(r.accumulated_wear * 20)
        bar = "█" * wear_pct + "░" * (20 - wear_pct)
        print(f"  [{bar}] {r.accumulated_wear:.0%}")
        print()
    
    def do_scenario(self, arg):
        """Run a predefined scenario: scenario sweep|spike|recovery|wear"""
        scenarios = {
            'sweep': self._scenario_sweep,
            'spike': self._scenario_spike,
            'recovery': self._scenario_recovery,
            'wear': self._scenario_wear,
        }
        
        if arg in scenarios:
            scenarios[arg]()
        else:
            print(f"Unknown scenario. Available: {', '.join(scenarios.keys())}")
    
    def _scenario_sweep(self):
        """Population sweep from 5% to 95%."""
        print("\n═══════════════ SCENARIO: POPULATION SWEEP ═══════════════\n")
        
        self.calc.reset()
        self.tick_count = 0
        
        print("Pop%  │ Phase      │   VDI   │ Wildlife    │ Bloom  │ Motion")
        print("──────┼────────────┼─────────┼─────────────┼────────┼────────")
        
        for pop in [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]:
            self.population = pop / 100.0
            
            for _ in range(25):
                self._do_tick()
            
            r = self.last_result
            o = self.last_output
            
            print(f" {pop:2d}%  │ {r.phase.value:10s} │ {r.smoothed_vdi:+.3f}  │ {r.wildlife_state.value:11s} │ "
                  f"{o.post_process.bloom_intensity_mod:.3f}  │ {o.motion.animation_phase_sync:.3f}")
        
        print()
    
    def _scenario_spike(self):
        """Rapid population spike."""
        print("\n═══════════════ SCENARIO: POPULATION SPIKE ═══════════════\n")
        
        self.calc.reset()
        self.tick_count = 0
        self.population = 0.05
        
        print("Phase 1: Peaceful start (5% population)")
        for _ in range(20):
            self._do_tick()
        print(f"  VDI: {self.last_result.smoothed_vdi:+.3f}, Wildlife: {self.last_result.wildlife_state.value}")
        
        print("\nPhase 2: Sudden spike to 90%")
        self.population = 0.90
        for i in range(15):
            self._do_tick()
            if i % 5 == 0:
                print(f"  Tick {self.tick_count}: VDI: {self.last_result.smoothed_vdi:+.3f}, "
                      f"Wildlife: {self.last_result.wildlife_state.value}")
        
        print("\nPhase 3: Stabilize at high pressure")
        for _ in range(20):
            self._do_tick()
        print(f"  Final VDI: {self.last_result.smoothed_vdi:+.3f}")
        print(f"  Wildlife: {self.last_result.wildlife_state.value}")
        print(f"  Wear: {self.last_result.accumulated_wear:.1%}")
        print()
    
    def _scenario_recovery(self):
        """Recovery after high pressure."""
        print("\n═══════════════ SCENARIO: RECOVERY ═══════════════\n")
        
        self.calc.reset()
        self.tick_count = 0
        
        print("Phase 1: High pressure (85%)")
        self.population = 0.85
        for _ in range(40):
            self._do_tick()
        
        initial_vdi = self.last_result.smoothed_vdi
        initial_wear = self.last_result.accumulated_wear
        print(f"  VDI: {initial_vdi:+.3f}, Wear: {initial_wear:.1%}")
        
        print("\nPhase 2: Population drops to 10%")
        self.population = 0.10
        
        checkpoints = [10, 20, 40, 60, 80]
        for target in checkpoints:
            while self.tick_count < 40 + target:
                self._do_tick()
            r = self.last_result
            print(f"  +{target} ticks: VDI: {r.smoothed_vdi:+.3f}, "
                  f"Wildlife: {r.wildlife_state.value}, Wear: {r.accumulated_wear:.1%}")
        
        print(f"\nRecovery: VDI {initial_vdi:+.3f} → {self.last_result.smoothed_vdi:+.3f}")
        print(f"          Wear {initial_wear:.1%} → {self.last_result.accumulated_wear:.1%}")
        print()
    
    def _scenario_wear(self):
        """Environmental wear accumulation."""
        print("\n═══════════════ SCENARIO: WEAR ACCUMULATION ═══════════════\n")
        
        self.calc.reset()
        self.tick_count = 0
        
        print("High population sustained wear test...")
        print()
        self.population = 0.80
        
        print("Tick │ Wear  │ Ground │ Water  │ Grass")
        print("─────┼───────┼────────┼────────┼───────")
        
        for i in range(100):
            self._do_tick()
            if i % 20 == 0:
                r = self.last_result
                m = self.last_output.materials
                print(f" {self.tick_count:3d} │ {r.accumulated_wear:4.0%}  │ {m.ground_wear:.3f}  │ "
                      f"{m.water_clarity:.3f}  │ {m.grass_trampling:.3f}")
        
        print()
    
    def do_reset(self, arg):
        """Reset all state."""
        self.calc.reset()
        self.tick_count = 0
        self.population = 0.10
        
        for _ in range(5):
            self._do_tick()
        
        print("State reset. Population: 10%")
    
    def do_help(self, arg):
        """Show help."""
        print(__doc__)
    
    def do_quit(self, arg):
        """Exit the simulator."""
        print("Goodbye!")
        return True
    
    def do_exit(self, arg):
        """Exit the simulator."""
        return self.do_quit(arg)
    
    def do_q(self, arg):
        """Exit the simulator."""
        return self.do_quit(arg)
    
    def default(self, line):
        """Handle unknown commands."""
        print(f"Unknown command: {line}")
        print("Type 'help' for available commands.")
    
    def emptyline(self):
        """Handle empty input."""
        pass


def main():
    parser = argparse.ArgumentParser(description='VDE Phase 1 Simulator')
    parser.add_argument('--seed', type=int, help='Random seed')
    args = parser.parse_args()
    
    sim = VDESimulator(seed=args.seed)
    
    try:
        sim.cmdloop()
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == '__main__':
    main()
