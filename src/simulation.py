"""
Simulation runner for the Living Soundscape Engine.

Provides a high-level interface for running simulations with:
- Configurable scenarios
- Time progression
- Environment changes
- Output logging
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
import json
import csv
import io


@dataclass
class ScenarioStep:
    """A single step in a simulation scenario."""
    time: float  # When this step occurs
    action: str  # "set_biome", "set_weather", "set_time", "set_population", "trigger_sound"
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""
    duration: float = 300.0  # Total simulation duration (seconds)
    tick_interval: float = 1.0  # Time between ticks
    seed: Optional[int] = 42  # Random seed
    
    # Initial environment
    initial_biome: str = "forest"
    initial_weather: str = "clear"
    initial_time_of_day: str = "day"
    initial_population: float = 0.0
    
    # Scenario steps (time-based changes)
    scenario: List[ScenarioStep] = field(default_factory=list)
    
    # Logging
    log_events: bool = True
    log_sdi: bool = True
    log_interval: float = 5.0  # How often to log SDI (seconds)


class SimulationRunner:
    """
    Runs LSE simulations with scenarios and logging.
    
    Example:
        >>> runner = SimulationRunner(config_path="config/")
        >>> runner.configure(duration=60.0, initial_biome="forest")
        >>> runner.add_step(30.0, "set_population", {"ratio": 0.5})
        >>> results = runner.run()
        >>> print(results.summary())
    """
    
    def __init__(self, config_path: Optional[str] = None, 
                 config: Optional[Any] = None,
                 seed: Optional[int] = None):
        """
        Initialize the runner.
        
        Args:
            config_path: Path to config directory
            config: Pre-loaded LSEConfig object
            seed: Random seed
        """
        self.config_path = config_path
        self.lse_config = config
        self.seed = seed
        
        self.sim_config = SimulationConfig(seed=seed)
        self._engine = None
        
        # Results
        self._events: List[Dict] = []
        self._sdi_log: List[Dict] = []
        self._step_log: List[Dict] = []
    
    def configure(self, **kwargs) -> 'SimulationRunner':
        """
        Configure simulation parameters.
        
        Returns self for chaining.
        """
        for key, value in kwargs.items():
            if hasattr(self.sim_config, key):
                setattr(self.sim_config, key, value)
        return self
    
    def add_step(self, time: float, action: str, params: Dict[str, Any] = None) -> 'SimulationRunner':
        """
        Add a scenario step.
        
        Args:
            time: When the step occurs
            action: Action type
            params: Action parameters
            
        Returns self for chaining.
        """
        step = ScenarioStep(time=time, action=action, params=params or {})
        self.sim_config.scenario.append(step)
        return self
    
    def set_scenario(self, steps: List[Tuple[float, str, Dict]]) -> 'SimulationRunner':
        """
        Set the full scenario.
        
        Args:
            steps: List of (time, action, params) tuples
        """
        self.sim_config.scenario = [
            ScenarioStep(time=t, action=a, params=p)
            for t, a, p in steps
        ]
        return self
    
    def run(self, progress_callback: Optional[Callable] = None) -> 'SimulationResults':
        """
        Run the simulation.
        
        Args:
            progress_callback: Optional callback(current_time, total_time)
            
        Returns:
            SimulationResults object
        """
        # Initialize engine
        try:
            from .engine import LSEEngine
        except ImportError:
            from engine import LSEEngine
        
        self._engine = LSEEngine(
            config_path=self.config_path,
            config=self.lse_config,
            seed=self.sim_config.seed,
        )
        
        # Set initial environment
        self._engine.set_environment(
            biome_id=self.sim_config.initial_biome,
            weather=self.sim_config.initial_weather,
            time_of_day=self.sim_config.initial_time_of_day,
        )
        self._engine.set_population(self.sim_config.initial_population)
        
        # Clear logs
        self._events = []
        self._sdi_log = []
        self._step_log = []
        
        # Sort scenario by time
        scenario = sorted(self.sim_config.scenario, key=lambda s: s.time)
        scenario_index = 0
        
        # Run simulation
        current_time = 0.0
        last_log_time = 0.0
        tick_interval = self.sim_config.tick_interval
        duration = self.sim_config.duration
        
        while current_time < duration:
            # Process scenario steps
            while scenario_index < len(scenario) and scenario[scenario_index].time <= current_time:
                step = scenario[scenario_index]
                self._execute_step(step, current_time)
                scenario_index += 1
            
            # Run tick
            events = self._engine.tick(delta_time=tick_interval)
            
            # Log events
            if self.sim_config.log_events:
                for event in events:
                    self._events.append({
                        'time': current_time,
                        **event.to_dict()
                    })
            
            # Log SDI periodically
            if self.sim_config.log_sdi and current_time - last_log_time >= self.sim_config.log_interval:
                self._log_sdi(current_time)
                last_log_time = current_time
            
            # Progress callback
            if progress_callback:
                progress_callback(current_time, duration)
            
            current_time += tick_interval
        
        # Final SDI log
        self._log_sdi(current_time)
        
        return SimulationResults(
            events=self._events,
            sdi_log=self._sdi_log,
            step_log=self._step_log,
            final_state=self._engine.get_state(),
            stats=self._engine.stats.to_dict(),
            config=self.sim_config,
        )
    
    def _execute_step(self, step: ScenarioStep, current_time: float) -> None:
        """Execute a scenario step."""
        action = step.action
        params = step.params
        
        if action == "set_biome":
            self._engine.set_biome(params.get("biome_id", "forest"))
        elif action == "set_weather":
            self._engine.set_weather(params.get("weather", "clear"))
        elif action == "set_time":
            self._engine.set_time_of_day(params.get("time_of_day", "day"))
        elif action == "set_population":
            self._engine.set_population(params.get("ratio", 0.0))
        elif action == "trigger_sound":
            self._engine.trigger_sound(
                sound_id=params.get("sound_id"),
                duration=params.get("duration"),
                intensity=params.get("intensity"),
            )
        elif action == "notify_transition":
            self._engine.notify_transition()
        elif action == "notify_resolution":
            self._engine.notify_resolution()
        
        # Log the step
        self._step_log.append({
            'time': current_time,
            'action': action,
            'params': params,
        })
    
    def _log_sdi(self, current_time: float) -> None:
        """Log current SDI state."""
        state = self._engine.get_state()
        breakdown = self._engine.get_sdi_breakdown()
        
        log_entry = {
            'time': current_time,
            'sdi': state['sdi']['current'],
            'target': state['sdi']['target'],
            'delta': state['sdi']['delta'],
            'active_sounds': state['stats']['active_sounds'],
            'population': state['environment']['population_ratio'],
            'biome': state['environment']['biome_id'],
            'weather': state['environment']['weather'],
            **{k: v for k, v in breakdown.items() if k not in ['raw_sdi', 'smoothed_sdi', 'target_sdi', 'delta']}
        }
        self._sdi_log.append(log_entry)


@dataclass
class SimulationResults:
    """Results from a simulation run."""
    events: List[Dict]
    sdi_log: List[Dict]
    step_log: List[Dict]
    final_state: Dict[str, Any]
    stats: Dict[str, Any]
    config: SimulationConfig
    
    def summary(self) -> str:
        """Get a text summary of the simulation."""
        lines = [
            "=" * 60,
            "SIMULATION RESULTS",
            "=" * 60,
            "",
            f"Duration: {self.config.duration:.0f}s",
            f"Tick interval: {self.config.tick_interval:.1f}s",
            f"Seed: {self.config.seed}",
            "",
            "--- Statistics ---",
            f"Total ticks: {self.stats['total_ticks']}",
            f"Total events: {self.stats['total_events']}",
            f"Sounds started: {self.stats['total_sounds_started']}",
            f"Sounds ended: {self.stats['total_sounds_ended']}",
            f"Sounds interrupted: {self.stats['total_sounds_interrupted']}",
            "",
            "--- Final State ---",
            f"SDI: {self.final_state['sdi']['current']:.3f}",
            f"Target SDI: {self.final_state['sdi']['target']:.3f}",
            f"Delta: {self.final_state['sdi']['delta']:.3f}",
            f"Active sounds: {self.final_state['stats']['active_sounds']}",
            "",
            "--- SDI Range ---",
        ]
        
        if self.sdi_log:
            sdi_values = [entry['sdi'] for entry in self.sdi_log]
            lines.append(f"Min SDI: {min(sdi_values):.3f}")
            lines.append(f"Max SDI: {max(sdi_values):.3f}")
            lines.append(f"Avg SDI: {sum(sdi_values)/len(sdi_values):.3f}")
        
        # Sound breakdown
        lines.extend(["", "--- Sounds Played ---"])
        sound_counts = {}
        for event in self.events:
            if event.get('event_type') == 'sound_start':
                sound_id = event.get('sound_id', 'unknown')
                sound_counts[sound_id] = sound_counts.get(sound_id, 0) + 1
        
        for sound_id, count in sorted(sound_counts.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {sound_id}: {count}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def events_to_csv(self) -> str:
        """Export events to CSV string."""
        if not self.events:
            return ""
        
        output = io.StringIO()
        fieldnames = ['time', 'event_type', 'sound_id', 'instance_id', 'layer', 'duration', 'intensity', 'reason']
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(self.events)
        return output.getvalue()
    
    def sdi_to_csv(self) -> str:
        """Export SDI log to CSV string."""
        if not self.sdi_log:
            return ""
        
        output = io.StringIO()
        fieldnames = list(self.sdi_log[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(self.sdi_log)
        return output.getvalue()
    
    def to_json(self) -> str:
        """Export results to JSON string."""
        return json.dumps({
            'events': self.events,
            'sdi_log': self.sdi_log,
            'step_log': self.step_log,
            'final_state': self.final_state,
            'stats': self.stats,
        }, indent=2)


def run_demo(config_path: str = "config/", duration: float = 60.0, seed: int = 42) -> SimulationResults:
    """
    Run a demo simulation with a sample scenario.
    
    This demonstrates the engine responding to:
    - Time of day changes
    - Weather changes
    - Population changes
    """
    runner = SimulationRunner(config_path=config_path, seed=seed)
    
    # Configure
    runner.configure(
        duration=duration,
        tick_interval=0.5,
        initial_biome="forest",
        initial_weather="clear",
        initial_time_of_day="day",
        initial_population=0.1,
        log_interval=5.0,
    )
    
    # Build scenario
    # Population gradually increases
    for t in range(10, int(duration), 10):
        pop = min(0.8, 0.1 + (t / duration) * 0.7)
        runner.add_step(float(t), "set_population", {"ratio": pop})
    
    # Weather change at 1/3 duration
    runner.add_step(duration / 3, "set_weather", {"weather": "rain"})
    
    # Time change at 2/3 duration
    runner.add_step(duration * 2 / 3, "set_time", {"time_of_day": "dusk"})
    
    # Run with progress output
    def progress(current, total):
        if int(current) % 10 == 0:
            print(f"  Progress: {current:.0f}/{total:.0f}s", end="\r")
    
    print(f"Running demo simulation ({duration}s)...")
    results = runner.run(progress_callback=progress)
    print()
    
    return results
