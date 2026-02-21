#!/usr/bin/env python3
"""
Command-Based Living Soundscape Engine Simulator

A simple command-line interface for experimenting with the LSE.
Works in any terminal including Termux.

Usage:
    python simulate.py [--seed SEED] [--biome BIOME]

Commands:
    pop <0-100>     Set population percentage
    weather <type>  Set weather (clear/rain/storm/fog/snow)
    time <period>   Set time (dawn/day/dusk/night)
    biome <name>    Set biome
    tick [count]    Run ticks (default: 10)
    run <seconds>   Run simulation for N seconds
    status          Show current state
    sounds          Show active sounds
    sdi             Show SDI breakdown
    events          Show recent events
    trigger <id>    Trigger a specific sound
    help            Show commands
    quit            Exit

Examples:
    > pop 50
    > weather storm
    > tick 20
    > sdi
"""

import sys
import os
import time
import argparse
import readline  # For command history

# Add src to path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

from engine import LSEEngine
from output import EventLogger, SDILogger


class CommandSimulator:
    """
    Command-based simulator for the LSE.
    """
    
    WEATHERS = ['clear', 'rain', 'storm', 'fog', 'snow']
    TIMES = ['dawn', 'day', 'dusk', 'night']
    BIOMES = ['forest', 'desert', 'swamp', 'mountain', 'coastal', 'cave',
              'meadow', 'tundra', 'jungle', 'volcanic', 'ruins', 'underground']
    
    def __init__(self, config_path: str = "config/", seed: int = None,
                 initial_biome: str = "forest"):
        """Initialize the simulator."""
        self.seed = seed or int(time.time()) % 10000
        
        print(f"Initializing LSE (seed: {self.seed})...")
        
        self.engine = LSEEngine(config_path=config_path, seed=self.seed)
        self.engine.set_environment(
            biome_id=initial_biome,
            weather="clear",
            time_of_day="day"
        )
        self.engine.set_population(0.0)
        
        # Loggers
        self.event_logger = EventLogger(max_events=1000)
        self.sdi_logger = SDILogger(sample_interval=0.5)
        
        # Recent events
        self.recent_events = []
        
        # Register callback
        self.engine.on_event(self._on_event)
        
        print(f"Ready! Type 'help' for commands.\n")
    
    def _on_event(self, event) -> None:
        """Handle events."""
        event_type = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
        
        self.recent_events.append({
            'time': self.engine.simulation_time,
            'type': event_type,
            'sound': event.sound_id,
            'layer': event.layer,
            'duration': event.duration,
        })
        
        if len(self.recent_events) > 50:
            self.recent_events = self.recent_events[-50:]
        
        self.event_logger.log_event(event, self.engine.environment, self.engine.sdi)
    
    def run(self) -> None:
        """Run the command loop."""
        while True:
            try:
                # Show prompt with current state
                env = self.engine.environment
                prompt = f"[{env.biome_id}|{env.weather}|{env.time_of_day}|pop:{int(env.population_ratio*100)}%] > "
                
                line = input(prompt).strip()
                if not line:
                    continue
                
                parts = line.split()
                cmd = parts[0].lower()
                args = parts[1:]
                
                self._handle_command(cmd, args)
                
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit.")
            except EOFError:
                break
    
    def _handle_command(self, cmd: str, args: list) -> None:
        """Handle a command."""
        
        if cmd in ('quit', 'exit', 'q'):
            self._cmd_quit()
            sys.exit(0)
        
        elif cmd == 'help' or cmd == '?':
            self._cmd_help()
        
        elif cmd == 'pop' or cmd == 'population':
            self._cmd_population(args)
        
        elif cmd == 'weather' or cmd == 'w':
            self._cmd_weather(args)
        
        elif cmd == 'time' or cmd == 't':
            self._cmd_time(args)
        
        elif cmd == 'biome' or cmd == 'b':
            self._cmd_biome(args)
        
        elif cmd == 'tick':
            self._cmd_tick(args)
        
        elif cmd == 'run':
            self._cmd_run(args)
        
        elif cmd == 'status' or cmd == 'st':
            self._cmd_status()
        
        elif cmd == 'sounds' or cmd == 's':
            self._cmd_sounds()
        
        elif cmd == 'sdi':
            self._cmd_sdi()
        
        elif cmd == 'events' or cmd == 'e':
            self._cmd_events()
        
        elif cmd == 'trigger' or cmd == 'tr':
            self._cmd_trigger(args)
        
        elif cmd == 'scenario':
            self._cmd_scenario(args)
        
        elif cmd == 'pressure' or cmd == 'pr':
            self._cmd_pressure()
        
        elif cmd == 'export':
            self._cmd_export(args)
        
        else:
            print(f"Unknown command: {cmd}. Type 'help' for commands.")
    
    def _cmd_help(self) -> None:
        """Show help."""
        print("""
Commands:
  pop <0-100>       Set population percentage
  weather <type>    Set weather: clear, rain, storm, fog, snow
  time <period>     Set time: dawn, day, dusk, night
  biome <name>      Set biome: forest, desert, swamp, mountain, etc.
  
  tick [count]      Run N ticks (default: 10)
  run <seconds>     Run simulation for N seconds
  
  status            Show current engine state
  sounds            Show active sounds
  sdi               Show detailed SDI breakdown
  events            Show recent sound events
  
  trigger <sound>   Trigger a specific sound
  scenario <name>   Run a predefined scenario
  export <file>     Export event log to CSV
  
  help              Show this help
  quit              Exit simulator

Scenarios:
  crowding          Simulate increasing population pressure
  storm             Simulate approaching storm
  daynight          Simulate day/night cycle
  stress            High population + storm (stress test)
""")
    
    def _cmd_population(self, args: list) -> None:
        """Set population."""
        if not args:
            print(f"Current population: {int(self.engine.environment.population_ratio * 100)}%")
            return
        
        try:
            pop = int(args[0])
            pop = max(0, min(100, pop)) / 100.0
            self.engine.set_population(pop)
            print(f"Population set to {int(pop * 100)}%")
        except ValueError:
            print("Usage: pop <0-100>")
    
    def _cmd_weather(self, args: list) -> None:
        """Set weather."""
        if not args:
            print(f"Current weather: {self.engine.environment.weather}")
            print(f"Options: {', '.join(self.WEATHERS)}")
            return
        
        weather = args[0].lower()
        if weather in self.WEATHERS:
            self.engine.set_weather(weather)
            print(f"Weather set to {weather}")
        else:
            print(f"Invalid weather. Options: {', '.join(self.WEATHERS)}")
    
    def _cmd_time(self, args: list) -> None:
        """Set time of day."""
        if not args:
            print(f"Current time: {self.engine.environment.time_of_day}")
            print(f"Options: {', '.join(self.TIMES)}")
            return
        
        time_of_day = args[0].lower()
        if time_of_day in self.TIMES:
            self.engine.set_time_of_day(time_of_day)
            print(f"Time set to {time_of_day}")
        else:
            print(f"Invalid time. Options: {', '.join(self.TIMES)}")
    
    def _cmd_biome(self, args: list) -> None:
        """Set biome."""
        if not args:
            print(f"Current biome: {self.engine.environment.biome_id}")
            print(f"Options: {', '.join(self.BIOMES)}")
            return
        
        biome = args[0].lower()
        if biome in self.BIOMES:
            self.engine.set_biome(biome)
            print(f"Biome set to {biome}")
        else:
            print(f"Invalid biome. Options: {', '.join(self.BIOMES)}")
    
    def _cmd_tick(self, args: list) -> None:
        """Run simulation ticks."""
        count = 10
        if args:
            try:
                count = int(args[0])
            except ValueError:
                print("Usage: tick [count]")
                return
        
        print(f"Running {count} ticks...")
        
        start_sdi = self.engine.sdi
        sounds_before = self.engine.stats.total_sounds_started
        
        for i in range(count):
            events = self.engine.tick(delta_time=0.5)
            
            if self.engine.sdi_result:
                self.sdi_logger.log(
                    self.engine.simulation_time,
                    self.engine.sdi_result,
                    self.engine.environment,
                    len(self.engine.get_active_sounds())
                )
        
        end_sdi = self.engine.sdi
        sounds_after = self.engine.stats.total_sounds_started
        new_sounds = sounds_after - sounds_before
        
        # Show summary
        delta_sdi = end_sdi - start_sdi
        direction = "↑" if delta_sdi > 0 else "↓" if delta_sdi < 0 else "→"
        
        print(f"  Time: {self.engine.simulation_time:.1f}s")
        print(f"  SDI: {start_sdi:.3f} {direction} {end_sdi:.3f} (Δ{delta_sdi:+.3f})")
        print(f"  Target SDI: {self.engine.sdi_result.target_sdi:.3f}")
        print(f"  Sounds started: {new_sounds}")
        print(f"  Active sounds: {len(self.engine.get_active_sounds())}")
    
    def _cmd_run(self, args: list) -> None:
        """Run for a duration."""
        if not args:
            print("Usage: run <seconds>")
            return
        
        try:
            duration = float(args[0])
        except ValueError:
            print("Usage: run <seconds>")
            return
        
        ticks = int(duration / 0.5)
        self._cmd_tick([str(ticks)])
    
    def _cmd_status(self) -> None:
        """Show engine status."""
        env = self.engine.environment
        stats = self.engine.stats
        pressure = self.engine.pressure_state
        
        print(f"""
=== Engine Status ===
  Simulation time: {self.engine.simulation_time:.1f}s
  
  Environment:
    Biome: {env.biome_id}
    Weather: {env.weather}
    Time: {env.time_of_day}
    Population: {int(env.population_ratio * 100)}%
  
  Population Pressure:
    Phase: {self.engine.pressure_phase.upper()}
    Wildlife Suppression: {int(pressure.wildlife_suppression * 100)}%
    Discomfort Boost: {int(pressure.discomfort_boost * 100)}%
    Static Intensity: {int(pressure.static_intensity * 100)}%
  
  SDI:
    Current: {self.engine.sdi:+.3f}
    Target: {self.engine.sdi_result.target_sdi if self.engine.sdi_result else 0:.3f}
    Delta: {self.engine.sdi_delta:+.3f}
  
  Statistics:
    Total ticks: {stats.total_ticks}
    Sounds started: {stats.total_sounds_started}
    Sounds ended: {stats.total_sounds_ended}
    Sounds interrupted: {stats.total_sounds_interrupted}
    Active sounds: {len(self.engine.get_active_sounds())}
""")
    
    def _cmd_sounds(self) -> None:
        """Show active sounds."""
        active = self.engine.get_active_sounds()
        
        if not active:
            print("No active sounds.")
            return
        
        print(f"\nActive Sounds ({len(active)}):")
        print("-" * 50)
        
        for sound in active:
            remaining = sound.time_remaining(self.engine.simulation_time)
            if remaining == float('inf'):
                time_str = "continuous"
            else:
                time_str = f"{remaining:.1f}s remaining"
            
            print(f"  [{sound.layer:10}] {sound.sound_id:25} ({time_str})")
        
        print()
    
    def _cmd_sdi(self) -> None:
        """Show SDI breakdown."""
        if not self.engine.sdi_result:
            print("No SDI data yet. Run some ticks first.")
            return
        
        result = self.engine.sdi_result
        
        print(f"""
=== SDI Breakdown ===
  Raw SDI: {result.raw_sdi:+.3f}
  Smoothed SDI: {result.smoothed_sdi:+.3f}
  Target SDI: {result.target_sdi:+.3f}
  Delta: {result.delta:+.3f} ({result.delta_category})
  
  Baselines:
    Biome: {result.biome_baseline:+.3f}
    Time: {result.time_modifier:+.3f}
    Weather: {result.weather_modifier:+.3f}
  
  Discomfort Factors (positive = more discomfort):
    Density overload: {result.discomfort.density_overload:+.3f}
    Layer conflict: {result.discomfort.layer_conflict:+.3f}
    Rhythm instability: {result.discomfort.rhythm_instability:+.3f}
    Silence deprivation: {result.discomfort.silence_deprivation:+.3f}
    Contextual mismatch: {result.discomfort.contextual_mismatch:+.3f}
    Persistence: {result.discomfort.persistence:+.3f}
    Absence after pattern: {result.discomfort.absence_after_pattern:+.3f}
    TOTAL: {result.discomfort.total:+.3f}
  
  Comfort Factors (negative = more comfort):
    Predictable rhythm: {result.comfort.predictable_rhythm:+.3f}
    Appropriate silence: {result.comfort.appropriate_silence:+.3f}
    Layer harmony: {result.comfort.layer_harmony:+.3f}
    Gradual transition: {result.comfort.gradual_transition:+.3f}
    Resolution: {result.comfort.resolution:+.3f}
    Environmental coherence: {result.comfort.environmental_coherence:+.3f}
    TOTAL: {result.comfort.total:+.3f}
  
  Top Contributors:
    Positive (discomfort): {result.top_positive[0]} ({result.top_positive[1]:+.3f})
    Negative (comfort): {result.top_negative[0]} ({result.top_negative[1]:+.3f})
""")
    
    def _cmd_events(self) -> None:
        """Show recent events."""
        if not self.recent_events:
            print("No events yet.")
            return
        
        print(f"\nRecent Events (last {min(20, len(self.recent_events))}):")
        print("-" * 60)
        
        for event in self.recent_events[-20:]:
            type_char = {
                'sound_start': '▶',
                'sound_end': '■',
                'sound_interrupt': '✕'
            }.get(event['type'], '?')
            
            print(f"  {event['time']:6.1f}s  {type_char} {event['sound']:25} [{event['layer']}]")
        
        print()
    
    def _cmd_trigger(self, args: list) -> None:
        """Trigger a sound."""
        if not args:
            # List available sounds
            sounds = list(self.engine.soundscape.selector.sounds.keys())
            print("Available sounds:")
            for i, s in enumerate(sounds):
                if i % 4 == 0:
                    print()
                print(f"  {s:25}", end="")
            print("\n")
            return
        
        sound_id = args[0]
        event = self.engine.trigger_sound(sound_id)
        
        if event:
            print(f"Triggered: {sound_id} (duration: {event.duration:.1f}s)")
        else:
            print(f"Could not trigger sound: {sound_id}")
    
    def _cmd_scenario(self, args: list) -> None:
        """Run a predefined scenario."""
        if not args:
            print("Scenarios: crowding, storm, daynight, stress, pressure")
            return
        
        scenario = args[0].lower()
        
        if scenario == 'crowding':
            self._scenario_crowding()
        elif scenario == 'storm':
            self._scenario_storm()
        elif scenario == 'daynight':
            self._scenario_daynight()
        elif scenario == 'stress':
            self._scenario_stress()
        elif scenario == 'pressure':
            self._scenario_pressure()
        else:
            print(f"Unknown scenario: {scenario}")
    
    def _cmd_pressure(self) -> None:
        """Show detailed pressure system status."""
        pressure = self.engine.pressure_state
        
        print(f"""
=== Population Pressure System ===
  Population: {int(pressure.population * 100)}%
  Phase: {self.engine.pressure_phase.upper()}
  
  Modifiers:
    Wildlife Suppression: {pressure.wildlife_suppression*100:.0f}% (animals flee area)
    Discomfort Boost: {pressure.discomfort_boost*100:.0f}% (discomfort sound probability)
    Static Intensity: {pressure.static_intensity*100:.0f}% (noise/drone layer)
    Silence Enforcement: {pressure.silence_enforcement*100:.0f}% (forced quiet gaps)
  
  Phase Thresholds:
    NORMAL:   0-15%   - Natural soundscape
    SILENCE:  15-25%  - Wildlife retreats
    SUBTLE:   25-35%  - Faint discomfort sounds
    MODERATE: 35-50%  - Noticeable unease
    INTENSE:  50-70%  - Strong discomfort + static
    CRITICAL: 70%+    - Maximum pressure
""")
    
    def _scenario_crowding(self) -> None:
        """Simulate increasing population pressure."""
        print("\n=== SCENARIO: Population Crowding ===")
        print("Simulating population increasing from 0% to 90%...")
        print()
        
        for pop in [0, 20, 40, 60, 80, 90]:
            self.engine.set_population(pop / 100.0)
            print(f"Population: {pop}%")
            
            # Run 20 ticks
            for _ in range(20):
                self.engine.tick(0.5)
                if self.engine.sdi_result:
                    self.sdi_logger.log(
                        self.engine.simulation_time,
                        self.engine.sdi_result,
                        self.engine.environment,
                        len(self.engine.get_active_sounds())
                    )
            
            # Show results
            target = self.engine.sdi_result.target_sdi if self.engine.sdi_result else 0
            print(f"  SDI: {self.engine.sdi:+.3f} (target: {target:+.3f})")
            print(f"  Active sounds: {len(self.engine.get_active_sounds())}")
            print()
        
        print("OBSERVATION: As population increases, target SDI rises.")
        print("The engine tries to increase discomfort to push players out.")
    
    def _scenario_storm(self) -> None:
        """Simulate approaching storm."""
        print("\n=== SCENARIO: Approaching Storm ===")
        print("Weather progression: clear → fog → rain → storm → rain → clear")
        print()
        
        self.engine.set_population(0.3)  # Moderate population
        
        for weather in ['clear', 'fog', 'rain', 'storm', 'rain', 'clear']:
            self.engine.set_weather(weather)
            print(f"Weather: {weather}")
            
            # Run 15 ticks
            for _ in range(15):
                self.engine.tick(0.5)
            
            print(f"  SDI: {self.engine.sdi:+.3f}")
            print(f"  Active sounds: {len(self.engine.get_active_sounds())}")
            print()
        
        print("OBSERVATION: Weather changes affect available sounds and SDI modifiers.")
    
    def _scenario_daynight(self) -> None:
        """Simulate day/night cycle."""
        print("\n=== SCENARIO: Day/Night Cycle ===")
        print("Time progression: dawn → day → dusk → night → dawn")
        print()
        
        self.engine.set_population(0.2)
        
        for time_of_day in ['dawn', 'day', 'dusk', 'night', 'dawn']:
            self.engine.set_time_of_day(time_of_day)
            print(f"Time: {time_of_day}")
            
            # Run 15 ticks
            for _ in range(15):
                self.engine.tick(0.5)
            
            active = self.engine.get_active_sounds()
            sound_names = [s.sound_id for s in active][:3]
            
            print(f"  SDI: {self.engine.sdi:+.3f}")
            print(f"  Active: {', '.join(sound_names) if sound_names else '(none)'}")
            print()
        
        print("OBSERVATION: Time of day filters available sounds (nocturnal vs diurnal).")
    
    def _scenario_stress(self) -> None:
        """Stress test with high population and storm."""
        print("\n=== SCENARIO: Stress Test ===")
        print("High population (80%) + Storm weather")
        print()
        
        self.engine.set_population(0.8)
        self.engine.set_weather('storm')
        
        print("Running 60 ticks...")
        
        sdi_samples = []
        for i in range(60):
            self.engine.tick(0.5)
            sdi_samples.append(self.engine.sdi)
        
        print(f"\nResults:")
        print(f"  Final SDI: {self.engine.sdi:+.3f}")
        print(f"  Target SDI: {self.engine.sdi_result.target_sdi:+.3f}")
        print(f"  SDI Range: {min(sdi_samples):.3f} to {max(sdi_samples):.3f}")
        print(f"  Active sounds: {len(self.engine.get_active_sounds())}")
        
        # Show top contributors
        result = self.engine.sdi_result
        print(f"\nTop discomfort factor: {result.top_positive[0]} ({result.top_positive[1]:+.3f})")
        print(f"Top comfort factor: {result.top_negative[0]} ({result.top_negative[1]:+.3f})")
        
        print("\nOBSERVATION: High population drives SDI up significantly.")
        print("Players would feel subconscious discomfort and want to leave.")
    
    def _scenario_pressure(self) -> None:
        """Test the population pressure system through all phases."""
        print("\n=== SCENARIO: Population Pressure System ===")
        print("Testing discomfort progression through all pressure phases")
        print()
        
        # Reset to clean state
        self.engine.reset()
        self.engine.set_environment(biome_id="forest", weather="clear", time_of_day="day")
        
        # Define test populations for each phase
        phases = [
            (0.10, "NORMAL", "Natural soundscape"),
            (0.20, "SILENCE", "Wildlife retreating"),
            (0.30, "SUBTLE", "Subtle discomfort begins"),
            (0.42, "MODERATE", "Noticeable unease"),
            (0.60, "INTENSE", "Strong discomfort + static"),
            (0.85, "CRITICAL", "Maximum pressure"),
        ]
        
        for pop, phase_name, description in phases:
            self.engine.set_population(pop)
            print(f"Population: {int(pop*100)}% - {phase_name}")
            print(f"  {description}")
            
            # Run 30 ticks to let the system stabilize
            discomfort_sounds = []
            for _ in range(30):
                events = self.engine.tick(0.5)
                for e in events:
                    if hasattr(e, 'reason') and 'pressure_' in e.reason:
                        discomfort_sounds.append(e.sound_id)
            
            # Show results
            pressure = self.engine.pressure_state
            print(f"  Wildlife Suppression: {int(pressure.wildlife_suppression*100)}%")
            print(f"  Discomfort Boost: {int(pressure.discomfort_boost*100)}%")
            print(f"  Static Intensity: {int(pressure.static_intensity*100)}%")
            print(f"  SDI: {self.engine.sdi:+.3f} (target: {self.engine.sdi_result.target_sdi:+.3f})")
            
            if discomfort_sounds:
                unique = list(set(discomfort_sounds))
                print(f"  Discomfort sounds played: {', '.join(unique[:3])}")
            
            active = self.engine.get_active_sounds()
            if active:
                names = [s.sound_id for s in active][:3]
                print(f"  Active: {', '.join(names)}")
            print()
        
        print("OBSERVATION: Pressure system directly adds discomfort sounds")
        print("at high population, bypassing the regular selection system.")
        print("Wildlife is suppressed, and static/drone sounds emerge.")
    
    def _cmd_export(self, args: list) -> None:
        """Export event log."""
        filename = args[0] if args else "events.csv"
        
        count = self.event_logger.write_csv(filename)
        print(f"Exported {count} events to {filename}")
    
    def _cmd_quit(self) -> None:
        """Clean exit."""
        print(f"\nSession Summary:")
        print(f"  Total ticks: {self.engine.stats.total_ticks}")
        print(f"  Sounds played: {self.engine.stats.total_sounds_started}")
        print(f"  Final SDI: {self.engine.sdi:.3f}")
        print("\nGoodbye!")


def main():
    parser = argparse.ArgumentParser(
        description="Command-based LSE Simulator"
    )
    parser.add_argument('--seed', type=int, help='Random seed')
    parser.add_argument('--biome', default='forest', help='Initial biome')
    parser.add_argument('--config', default='config/', help='Config path')
    
    args = parser.parse_args()
    
    sim = CommandSimulator(
        config_path=args.config,
        seed=args.seed,
        initial_biome=args.biome
    )
    
    sim.run()


if __name__ == "__main__":
    main()
