#!/usr/bin/env python3
"""
AURA Interactive Simulator for Termux

A simple terminal-based simulator that shows real-time parameter output.
Works great in Termux on Android or any terminal.

Usage:
    python termux_simulator.py

Controls:
    UP/DOWN or +/-  : Adjust population
    1-4             : Select region
    r               : Reset
    q               : Quit
    ENTER           : Step simulation
"""

import sys
import os
import time
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vde.pressure_coordinator import PressureCoordinator, PressurePhase
from vde.wildlife import WildlifeManager, WildlifeState
from vde.npc_behavior import NPCManager, NPCType, ComfortLevel
from vde.environmental_wear import WearManager, SurfaceType, WearLayer
from vde.motion_coherence import MotionManager, MotionCategory, CoherenceLevel
from vde.attraction_system import AttractionManager, AttractionStrength


def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_header():
    """Print header."""
    print("=" * 70)
    print("  AURA - Ambient Universal Response Architecture")
    print("=" * 70)
    print()


def print_controls():
    """Print control instructions."""
    print("Controls: [+/-] Population | [1-4] Region | [r] Reset | [q] Quit | [ENTER] Step")
    print("-" * 70)


class TermuxSimulator:
    """Interactive simulator for Termux."""
    
    def __init__(self):
        # Create pressure coordinator with multiple regions
        self.coordinator = PressureCoordinator()
        self.coordinator.add_region("town_square", position=(0, 0))
        self.coordinator.add_region("market", position=(400, 0))
        self.coordinator.add_region("park", position=(700, 0))
        self.coordinator.add_region("forest", position=(1000, 0))
        
        # Create subsystem managers for detailed view
        self.wildlife = WildlifeManager()
        self.npc = NPCManager()
        self.wear = WearManager(surface_type=SurfaceType.GRASS)
        self.motion = MotionManager()
        self.attraction = AttractionManager("current_region")
        
        # Register some elements for motion
        for i in range(3):
            self.motion.register_element(f"tree_{i}", MotionCategory.FOLIAGE)
            self.motion.register_element(f"banner_{i}", MotionCategory.CLOTH)
        
        # Register some NPCs
        for npc_type in [NPCType.VENDOR, NPCType.GUARD, NPCType.AMBIENT, NPCType.CHILD]:
            self.npc.register_npc(f"npc_{npc_type.value}", npc_type)
        
        # State
        self.selected_region = "town_square"
        self.populations = {
            "town_square": 0.30,
            "market": 0.50,
            "park": 0.20,
            "forest": 0.10,
        }
        self.time = 0.0
        self.running = True
        
        # Initialize snapshots (will be populated on first update)
        self.wildlife_snapshot = None
        self.npc_snapshot = None
        self.wear_snapshot = None
        self.motion_snapshot = None
        self.attraction_snapshot = None
        
        # Do initial update to populate snapshots
        self.update(0.01)
    
    def update(self, delta_time: float = 0.5):
        """Update all systems."""
        self.time += delta_time
        
        # Update coordinator
        for region, pop in self.populations.items():
            self.coordinator.set_population(region, pop)
        
        self.coordinator.update(delta_time)
        
        # Update subsystems with selected region's population
        pop = self.populations[self.selected_region]
        
        self.wildlife.set_population(pop)
        self.wildlife_snapshot = self.wildlife.update(delta_time)
        
        self.npc.set_population(pop)
        self.npc_snapshot = self.npc.update(delta_time)
        
        self.wear.set_population(pop)
        self.wear_snapshot = self.wear.update(delta_time)
        
        self.motion.set_population(pop)
        self.motion_snapshot = self.motion.update(delta_time)
        
        self.attraction.set_population(pop)
        self.attraction_snapshot = self.attraction.update(delta_time)
    
    def display(self):
        """Display current state."""
        clear_screen()
        print_header()
        
        pop = self.populations[self.selected_region]
        
        # Region overview
        print(f"Time: {self.time:.1f}s | Selected: {self.selected_region} | Population: {pop:.0%}")
        print()
        
        # All regions pressure
        print("REGION PRESSURE MAP")
        print("-" * 70)
        print(f"{'Region':<15} {'Pop%':>6} {'SDI':>8} {'VDI':>8} {'Phase':<18} {'Attract':>8}")
        print("-" * 70)
        
        for i, (region_id, mgr) in enumerate(self.coordinator.regions.items(), 1):
            state = mgr.state
            attraction = self.coordinator.get_attraction(region_id)
            marker = ">>>" if region_id == self.selected_region else f"[{i}]"
            
            print(f"{marker} {region_id:<11} {state.population:>5.0%} {state.sdi:>+7.3f} "
                  f"{state.vdi_lagged:>+7.3f} {state.phase.value:<18} {attraction:>7.3f}")
        
        print()
        
        # Detailed subsystem view for selected region
        print(f"SUBSYSTEM DETAILS: {self.selected_region}")
        print("-" * 70)
        
        # Wildlife
        ws = self.wildlife_snapshot
        print(f"Wildlife:   State={ws.global_state.value:<10} SpawnRate={ws.total_spawn_rate:.0%}  "
              f"Activity={ws.average_activity:.2f}")
        
        # NPCs
        ns = self.npc_snapshot
        print(f"NPCs:       Comfort={ns.global_comfort.value:<12} EdgePref={ns.average_edge_preference:.0%}  "
              f"Active={ns.active_count}/{ns.active_count + ns.inactive_count}")
        
        # Wear
        wsnap = self.wear_snapshot
        disp = wsnap.layer_values.get(WearLayer.DISPLACEMENT, 0)
        disc = wsnap.layer_values.get(WearLayer.DISCOLORATION, 0)
        print(f"Wear:       Total={wsnap.total_wear:.0%}  Displacement={disp:.0%}  "
              f"Discolor={disc:.0%}")
        
        # Motion
        msnap = self.motion_snapshot
        print(f"Motion:     Coherence={msnap.coherence_level.value:<10} Value={msnap.coherence_value:.2f}  "
              f"Wind={msnap.global_wind_direction:.0f}°")
        
        # Attraction
        asnap = self.attraction_snapshot
        print(f"Attraction: Strength={asnap.attraction_strength.value:<10} Cues={len(asnap.active_cues)}")
        
        print()
        
        # UE5 Parameters Preview
        print("UE5 PARAMETERS (Sample)")
        print("-" * 70)
        
        pressure_mgr = self.coordinator.regions[self.selected_region]
        motion_params = self.motion.get_ue5_parameters()
        wear_params = self.wear.get_ue5_parameters()
        
        print(f"Pressure_SDI:           {pressure_mgr.sdi:>+7.3f}")
        print(f"Pressure_VDI:           {pressure_mgr.vdi:>+7.3f}")
        print(f"Wildlife_SpawnRate:     {ws.total_spawn_rate:>7.2f}")
        print(f"Motion_Coherence:       {motion_params.foliage_wave_coherence:>7.2f}")
        print(f"Wear_Displacement:      {wear_params.ground_displacement:>7.3f}")
        print(f"Wind_Direction:         {motion_params.wind_direction:>7.1f}°")
        
        print()
        print_controls()
    
    def handle_input(self, key: str):
        """Handle user input."""
        if key in ['q', 'Q']:
            self.running = False
        elif key in ['+', '=']:
            self.adjust_population(0.05)
        elif key in ['-', '_']:
            self.adjust_population(-0.05)
        elif key == '1':
            self.selected_region = "town_square"
        elif key == '2':
            self.selected_region = "market"
        elif key == '3':
            self.selected_region = "park"
        elif key == '4':
            self.selected_region = "forest"
        elif key in ['r', 'R']:
            self.reset()
    
    def adjust_population(self, delta: float):
        """Adjust selected region population."""
        current = self.populations[self.selected_region]
        self.populations[self.selected_region] = max(0.0, min(1.0, current + delta))
    
    def reset(self):
        """Reset simulation."""
        self.populations = {
            "town_square": 0.30,
            "market": 0.50,
            "park": 0.20,
            "forest": 0.10,
        }
        self.coordinator.reset()
        self.wildlife.reset()
        self.npc.reset()
        self.wear.reset()
        self.motion.reset()
        self.attraction.reset()
        self.time = 0.0
        
        # Re-initialize snapshots
        self.update(0.01)
    
    def run_interactive(self):
        """Run interactive simulation."""
        try:
            import tty
            import termios
            
            # Save terminal settings
            old_settings = termios.tcgetattr(sys.stdin)
            
            try:
                tty.setcbreak(sys.stdin.fileno())
                
                while self.running:
                    self.update(0.5)
                    self.display()
                    
                    # Non-blocking input check
                    import select
                    if select.select([sys.stdin], [], [], 0.5)[0]:
                        key = sys.stdin.read(1)
                        self.handle_input(key)
                    
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                
        except (ImportError, termios.error):
            # Fallback for systems without tty support
            self.run_simple()
    
    def run_simple(self):
        """Run simple input-based simulation."""
        print("Running in simple mode (press ENTER after each command)")
        print()
        
        while self.running:
            self.update(0.5)
            self.display()
            
            try:
                cmd = input("\nCommand: ").strip()
                if cmd:
                    self.handle_input(cmd[0])
            except EOFError:
                break
    
    def export_json(self, filename: str = "lse_state.json"):
        """Export current state to JSON file."""
        data = self.coordinator.to_ue5_json()
        
        # Add subsystem data
        data['Subsystems'] = {
            'Wildlife': self.wildlife_snapshot.to_dict() if self.wildlife_snapshot else {},
            'Motion': self.motion.get_ue5_parameters().to_ue5_json(),
            'Wear': self.wear.get_ue5_parameters().to_ue5_json(),
            'Attraction': self.attraction.get_ue5_parameters().to_ue5_json(),
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported to {filename}")
        return data


def run_auto_simulation(duration: float = 60.0, output_file: str = None):
    """Run automatic simulation and optionally save results."""
    sim = TermuxSimulator()
    
    print("Running automatic simulation...")
    print(f"Duration: {duration}s")
    print()
    
    results = []
    
    # Simulate crowding scenario
    for t in range(int(duration * 2)):
        time_s = t * 0.5
        
        # Gradually increase town population
        if time_s < 30:
            sim.populations["town_square"] = 0.20 + (0.70 * time_s / 30)
        else:
            sim.populations["town_square"] = 0.90
        
        sim.update(0.5)
        
        # Record state every 5 seconds
        if t % 10 == 0:
            mgr = sim.coordinator.regions["town_square"]
            results.append({
                'time': time_s,
                'population': sim.populations["town_square"],
                'sdi': mgr.sdi,
                'vdi': mgr.vdi,
                'phase': mgr.phase.value,
            })
            
            print(f"t={time_s:5.1f}s  pop={sim.populations['town_square']:.0%}  "
                  f"SDI={mgr.sdi:+.3f}  VDI={mgr.vdi:+.3f}  phase={mgr.phase.value}")
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_file}")
    
    return results


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='LSE/VDE Simulator')
    parser.add_argument('--auto', type=float, help='Run auto simulation for N seconds')
    parser.add_argument('--output', '-o', help='Output JSON file')
    parser.add_argument('--simple', action='store_true', help='Use simple input mode')
    
    args = parser.parse_args()
    
    if args.auto:
        run_auto_simulation(args.auto, args.output)
    else:
        sim = TermuxSimulator()
        
        if args.simple:
            sim.run_simple()
        else:
            sim.run_interactive()
