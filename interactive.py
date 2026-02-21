#!/usr/bin/env python3
"""
Interactive Living Soundscape Engine Simulator

A real-time CLI tool for experimenting with the LSE:
- Adjust population pressure and watch SDI respond
- Change weather and time of day
- Observe sound selection behavior
- Monitor the feedback loop in action

Usage:
    python interactive.py [--seed SEED] [--biome BIOME]

Controls:
    Population: 1-9 (10%-90%), 0 (empty), - (decrease), + (increase)
    Weather: w (cycle), W (reverse cycle)
    Time: t (cycle), T (reverse cycle)  
    Biome: b (cycle)
    Speed: [ (slower), ] (faster), SPACE (pause)
    Display: d (toggle details), s (toggle sounds), h (help)
    Quit: q or ESC
"""

import sys
import os
import time
import argparse
from typing import Optional, List, Dict, Any

# Add src to path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

from engine import LSEEngine
from output import EventLogger, SDILogger, DebugLogger, LogLevel


# ANSI escape codes for terminal control
class Term:
    CLEAR = '\033[2J'
    HOME = '\033[H'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    
    # Colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    
    @staticmethod
    def move(row: int, col: int) -> str:
        return f'\033[{row};{col}H'
    
    @staticmethod
    def clear_line() -> str:
        return '\033[K'


class InteractiveSimulator:
    """
    Interactive CLI simulator for the Living Soundscape Engine.
    """
    
    WEATHERS = ['clear', 'rain', 'storm', 'fog', 'snow']
    TIMES = ['dawn', 'day', 'dusk', 'night']
    BIOMES = ['forest', 'desert', 'swamp', 'mountain', 'coastal', 'cave', 
              'meadow', 'tundra', 'jungle', 'volcanic', 'ruins', 'underground']
    
    def __init__(self, config_path: str = "config/", seed: Optional[int] = None,
                 initial_biome: str = "forest"):
        """Initialize the simulator."""
        self.config_path = config_path
        self.seed = seed or int(time.time()) % 10000
        
        # Initialize engine
        self.engine = LSEEngine(config_path=config_path, seed=self.seed)
        
        # Set initial state
        self.engine.set_environment(
            biome_id=initial_biome,
            weather="clear",
            time_of_day="day"
        )
        self.engine.set_population(0.0)
        
        # Loggers
        self.event_logger = EventLogger(max_events=100)
        self.sdi_logger = SDILogger(sample_interval=0.5)
        
        # Register event callback
        self.engine.on_event(self._on_event)
        
        # Simulation state
        self.running = True
        self.paused = False
        self.tick_interval = 0.5  # seconds between ticks
        self.simulation_speed = 1.0
        
        # Display options
        self.show_details = True
        self.show_sounds = True
        self.show_help = False
        
        # Recent events for display
        self.recent_events: List[Dict] = []
        self.max_recent = 8
        
        # SDI history for sparkline
        self.sdi_history: List[float] = []
        self.max_history = 40
        
        # Current indices
        self.weather_idx = 0
        self.time_idx = 1  # Start at 'day'
        self.biome_idx = self.BIOMES.index(initial_biome) if initial_biome in self.BIOMES else 0
    
    def _on_event(self, event) -> None:
        """Handle sound events."""
        event_type = event.event_type.value if hasattr(event.event_type, 'value') else event.event_type
        
        self.recent_events.append({
            'time': self.engine.simulation_time,
            'type': event_type,
            'sound': event.sound_id,
            'layer': event.layer,
            'duration': event.duration,
            'intensity': event.intensity,
        })
        
        # Keep only recent
        if len(self.recent_events) > self.max_recent:
            self.recent_events = self.recent_events[-self.max_recent:]
        
        # Log to event logger
        self.event_logger.log_event(event, self.engine.environment, self.engine.sdi)
    
    def run(self) -> None:
        """Run the interactive simulation."""
        # Set up terminal
        self._setup_terminal()
        
        try:
            last_tick = time.time()
            
            while self.running:
                current_time = time.time()
                
                # Process input (non-blocking)
                self._process_input()
                
                # Tick simulation if not paused
                if not self.paused:
                    elapsed = current_time - last_tick
                    if elapsed >= self.tick_interval / self.simulation_speed:
                        self._tick()
                        last_tick = current_time
                
                # Update display
                self._render()
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.05)
        
        finally:
            self._restore_terminal()
    
    def _tick(self) -> None:
        """Run one simulation tick."""
        events = self.engine.tick(delta_time=self.tick_interval)
        
        # Log SDI
        if self.engine.sdi_result:
            self.sdi_logger.log(
                self.engine.simulation_time,
                self.engine.sdi_result,
                self.engine.environment,
                len(self.engine.get_active_sounds())
            )
        
        # Update SDI history
        self.sdi_history.append(self.engine.sdi)
        if len(self.sdi_history) > self.max_history:
            self.sdi_history = self.sdi_history[-self.max_history:]
    
    def _process_input(self) -> None:
        """Process keyboard input."""
        import select
        
        # Check if input available (Unix only)
        if select.select([sys.stdin], [], [], 0)[0]:
            char = sys.stdin.read(1)
            self._handle_key(char)
    
    def _handle_key(self, key: str) -> None:
        """Handle a keypress."""
        # Population controls (0-9)
        if key.isdigit():
            pop = int(key) / 10.0
            self.engine.set_population(pop)
        
        # Population adjustment
        elif key == '+' or key == '=':
            current = self.engine.environment.population_ratio
            self.engine.set_population(min(1.0, current + 0.1))
        elif key == '-' or key == '_':
            current = self.engine.environment.population_ratio
            self.engine.set_population(max(0.0, current - 0.1))
        
        # Weather
        elif key == 'w':
            self.weather_idx = (self.weather_idx + 1) % len(self.WEATHERS)
            self.engine.set_weather(self.WEATHERS[self.weather_idx])
        elif key == 'W':
            self.weather_idx = (self.weather_idx - 1) % len(self.WEATHERS)
            self.engine.set_weather(self.WEATHERS[self.weather_idx])
        
        # Time of day
        elif key == 't':
            self.time_idx = (self.time_idx + 1) % len(self.TIMES)
            self.engine.set_time_of_day(self.TIMES[self.time_idx])
        elif key == 'T':
            self.time_idx = (self.time_idx - 1) % len(self.TIMES)
            self.engine.set_time_of_day(self.TIMES[self.time_idx])
        
        # Biome
        elif key == 'b':
            self.biome_idx = (self.biome_idx + 1) % len(self.BIOMES)
            self.engine.set_biome(self.BIOMES[self.biome_idx])
        elif key == 'B':
            self.biome_idx = (self.biome_idx - 1) % len(self.BIOMES)
            self.engine.set_biome(self.BIOMES[self.biome_idx])
        
        # Speed controls
        elif key == '[':
            self.simulation_speed = max(0.25, self.simulation_speed / 2)
        elif key == ']':
            self.simulation_speed = min(4.0, self.simulation_speed * 2)
        elif key == ' ':
            self.paused = not self.paused
        
        # Display toggles
        elif key == 'd':
            self.show_details = not self.show_details
        elif key == 's':
            self.show_sounds = not self.show_sounds
        elif key == 'h' or key == '?':
            self.show_help = not self.show_help
        
        # Manual sound trigger
        elif key == 'r':
            # Trigger a random reactive sound
            self.engine.trigger_sound("footsteps_leaf_litter")
        
        # Notify transitions/resolutions
        elif key == 'n':
            self.engine.notify_transition()
        elif key == 'N':
            self.engine.notify_resolution()
        
        # Quit
        elif key == 'q' or key == '\x1b':  # ESC
            self.running = False
    
    def _render(self) -> None:
        """Render the display."""
        output = []
        output.append(Term.HOME)
        
        # Header
        output.append(self._render_header())
        output.append("")
        
        # Main panels
        output.append(self._render_environment())
        output.append("")
        output.append(self._render_sdi())
        output.append("")
        
        if self.show_sounds:
            output.append(self._render_sounds())
            output.append("")
        
        if self.show_details:
            output.append(self._render_details())
            output.append("")
        
        if self.show_help:
            output.append(self._render_help())
            output.append("")
        
        # Status bar
        output.append(self._render_status())
        
        # Print all at once
        sys.stdout.write('\n'.join(output))
        sys.stdout.flush()
    
    def _render_header(self) -> str:
        """Render the header."""
        title = f"{Term.BOLD}{Term.CYAN}═══ Living Soundscape Engine ═══{Term.RESET}"
        seed_info = f"{Term.DIM}Seed: {self.seed}{Term.RESET}"
        return f"{title}  {seed_info}"
    
    def _render_environment(self) -> str:
        """Render environment state."""
        env = self.engine.environment
        
        # Biome with color
        biome = f"{Term.GREEN}{env.biome_id.upper()}{Term.RESET}"
        
        # Weather with icon
        weather_icons = {
            'clear': '☀️ ', 'rain': '🌧️ ', 'storm': '⛈️ ',
            'fog': '🌫️ ', 'snow': '❄️ '
        }
        weather_icon = weather_icons.get(env.weather, '')
        weather = f"{weather_icon}{env.weather}"
        
        # Time with icon
        time_icons = {
            'dawn': '🌅', 'day': '☀️', 'dusk': '🌆', 'night': '🌙'
        }
        time_icon = time_icons.get(env.time_of_day, '')
        time_str = f"{time_icon} {env.time_of_day}"
        
        # Population bar
        pop_pct = int(env.population_ratio * 100)
        pop_bar = self._make_bar(env.population_ratio, 20, 
                                  low_color=Term.GREEN, high_color=Term.RED)
        pop_str = f"Population: {pop_bar} {pop_pct:3d}%"
        
        return f"  {biome} │ {weather} │ {time_str} │ {pop_str}"
    
    def _render_sdi(self) -> str:
        """Render SDI information."""
        lines = []
        
        sdi = self.engine.sdi
        target = self.engine.sdi_result.target_sdi if self.engine.sdi_result else 0.0
        delta = self.engine.sdi_delta
        
        # SDI value with color based on level
        if sdi < 0:
            sdi_color = Term.GREEN
        elif sdi < 0.3:
            sdi_color = Term.YELLOW
        else:
            sdi_color = Term.RED
        
        sdi_str = f"{sdi_color}{sdi:+.3f}{Term.RESET}"
        target_str = f"{target:+.3f}"
        delta_str = f"{delta:+.3f}"
        
        # Delta indicator
        if delta > 0.1:
            delta_ind = f"{Term.RED}▲ Need MORE discomfort{Term.RESET}"
        elif delta < -0.1:
            delta_ind = f"{Term.GREEN}▼ Need LESS discomfort{Term.RESET}"
        else:
            delta_ind = f"{Term.YELLOW}● Balanced{Term.RESET}"
        
        lines.append(f"  {Term.BOLD}SDI:{Term.RESET} {sdi_str}  Target: {target_str}  Delta: {delta_str}  {delta_ind}")
        
        # SDI sparkline
        if self.sdi_history:
            sparkline = self._make_sparkline(self.sdi_history)
            lines.append(f"  History: {sparkline}")
        
        # Factor breakdown if details enabled
        if self.show_details and self.engine.sdi_result:
            result = self.engine.sdi_result
            top_pos = result.top_positive
            top_neg = result.top_negative
            
            pos_str = f"{Term.RED}+{top_pos[0]}: {top_pos[1]:.3f}{Term.RESET}" if top_pos[1] > 0 else ""
            neg_str = f"{Term.GREEN}{top_neg[0]}: {top_neg[1]:.3f}{Term.RESET}" if top_neg[1] < 0 else ""
            
            if pos_str or neg_str:
                lines.append(f"  Top factors: {pos_str}  {neg_str}")
        
        return '\n'.join(lines)
    
    def _render_sounds(self) -> str:
        """Render active sounds and recent events."""
        lines = []
        
        # Active sounds
        active = self.engine.get_active_sounds()
        lines.append(f"  {Term.BOLD}Active Sounds ({len(active)}):{Term.RESET}")
        
        if active:
            for sound in active[:6]:  # Show up to 6
                layer_color = {
                    'background': Term.BLUE,
                    'periodic': Term.GREEN,
                    'reactive': Term.YELLOW,
                    'anomalous': Term.MAGENTA,
                }.get(sound.layer, Term.WHITE)
                
                remaining = sound.time_remaining(self.engine.simulation_time)
                if remaining == float('inf'):
                    time_str = "∞"
                else:
                    time_str = f"{remaining:.1f}s"
                
                lines.append(f"    {layer_color}●{Term.RESET} {sound.sound_id} ({time_str})")
        else:
            lines.append(f"    {Term.DIM}(silence){Term.RESET}")
        
        # Recent events
        lines.append("")
        lines.append(f"  {Term.BOLD}Recent Events:{Term.RESET}")
        
        if self.recent_events:
            for event in self.recent_events[-5:]:
                if event['type'] == 'sound_start':
                    icon = f"{Term.GREEN}▶{Term.RESET}"
                elif event['type'] == 'sound_end':
                    icon = f"{Term.YELLOW}■{Term.RESET}"
                else:
                    icon = f"{Term.RED}✕{Term.RESET}"
                
                lines.append(f"    {icon} {event['sound']} [{event['layer']}]")
        else:
            lines.append(f"    {Term.DIM}(no events yet){Term.RESET}")
        
        return '\n'.join(lines)
    
    def _render_details(self) -> str:
        """Render detailed statistics."""
        lines = []
        lines.append(f"  {Term.BOLD}Statistics:{Term.RESET}")
        
        stats = self.engine.stats
        lines.append(f"    Ticks: {stats.total_ticks}  "
                    f"Started: {stats.total_sounds_started}  "
                    f"Ended: {stats.total_sounds_ended}  "
                    f"Interrupted: {stats.total_sounds_interrupted}")
        
        # Memory stats
        state = self.engine.get_state()
        memory = state.get('memory', {})
        lines.append(f"    Patterns: {memory.get('patterns_tracked', 0)}  "
                    f"Silence gaps: {memory.get('silence_gaps', 0)}")
        
        # Layer utilization
        layers = state.get('soundscape', {}).get('layers', {})
        util = layers.get('utilization', {})
        util_str = "  ".join(f"{k[:3]}:{int(v*100)}%" for k, v in util.items())
        lines.append(f"    Layers: {util_str}")
        
        return '\n'.join(lines)
    
    def _render_help(self) -> str:
        """Render help panel."""
        lines = [
            f"  {Term.BOLD}═══ Controls ═══{Term.RESET}",
            f"  {Term.CYAN}Population:{Term.RESET} 0-9 (set %), +/- (adjust)",
            f"  {Term.CYAN}Weather:{Term.RESET} w/W (cycle forward/back)",
            f"  {Term.CYAN}Time:{Term.RESET} t/T (cycle forward/back)",
            f"  {Term.CYAN}Biome:{Term.RESET} b/B (cycle forward/back)",
            f"  {Term.CYAN}Speed:{Term.RESET} [ (slower), ] (faster), SPACE (pause)",
            f"  {Term.CYAN}Display:{Term.RESET} d (details), s (sounds), h (help)",
            f"  {Term.CYAN}Actions:{Term.RESET} r (trigger sound), n/N (transition/resolution)",
            f"  {Term.CYAN}Quit:{Term.RESET} q or ESC",
        ]
        return '\n'.join(lines)
    
    def _render_status(self) -> str:
        """Render status bar."""
        sim_time = self.engine.simulation_time
        
        if self.paused:
            status = f"{Term.BG_YELLOW}{Term.BOLD} PAUSED {Term.RESET}"
        else:
            speed_str = f"{self.simulation_speed:.1f}x" if self.simulation_speed != 1.0 else ""
            status = f"{Term.GREEN}● Running {speed_str}{Term.RESET}"
        
        time_str = f"Time: {sim_time:.1f}s"
        help_hint = f"{Term.DIM}Press 'h' for help, 'q' to quit{Term.RESET}"
        
        return f"  {status}  {time_str}  │  {help_hint}"
    
    def _make_bar(self, value: float, width: int = 20,
                  low_color: str = Term.GREEN, 
                  high_color: str = Term.RED) -> str:
        """Create a colored progress bar."""
        filled = int(value * width)
        empty = width - filled
        
        # Gradient from low to high color
        if value < 0.5:
            color = low_color
        elif value < 0.75:
            color = Term.YELLOW
        else:
            color = high_color
        
        bar = f"{color}{'█' * filled}{Term.DIM}{'░' * empty}{Term.RESET}"
        return f"[{bar}]"
    
    def _make_sparkline(self, values: List[float], width: int = 40) -> str:
        """Create a sparkline from values."""
        if not values:
            return ""
        
        # Sparkline characters (from low to high)
        chars = '▁▂▃▄▅▆▇█'
        
        # Normalize to 0-1 range (SDI is typically -1 to 1)
        min_val = -0.5
        max_val = 0.8
        range_val = max_val - min_val
        
        result = []
        for v in values[-width:]:
            normalized = (v - min_val) / range_val
            normalized = max(0, min(1, normalized))
            idx = int(normalized * (len(chars) - 1))
            
            # Color based on value
            if v < 0:
                color = Term.GREEN
            elif v < 0.3:
                color = Term.YELLOW
            else:
                color = Term.RED
            
            result.append(f"{color}{chars[idx]}{Term.RESET}")
        
        return ''.join(result)
    
    def _setup_terminal(self) -> None:
        """Set up terminal for interactive mode."""
        import tty
        import termios
        
        # Save terminal settings
        self._old_settings = termios.tcgetattr(sys.stdin)
        
        # Set terminal to raw mode (no line buffering)
        tty.setraw(sys.stdin.fileno())
        
        # Clear screen
        sys.stdout.write(Term.CLEAR)
        sys.stdout.flush()
    
    def _restore_terminal(self) -> None:
        """Restore terminal to normal mode."""
        import termios
        
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
        
        # Clear screen and show cursor
        sys.stdout.write(Term.CLEAR + Term.HOME)
        sys.stdout.write('\033[?25h')  # Show cursor
        sys.stdout.flush()
        
        print("\nSimulation ended.")
        print(f"Total ticks: {self.engine.stats.total_ticks}")
        print(f"Total sounds: {self.engine.stats.total_sounds_started}")
        print(f"Final SDI: {self.engine.sdi:.3f}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive Living Soundscape Engine Simulator"
    )
    parser.add_argument('--seed', type=int, help='Random seed')
    parser.add_argument('--biome', default='forest', 
                        choices=InteractiveSimulator.BIOMES,
                        help='Initial biome')
    parser.add_argument('--config', default='config/',
                        help='Path to config directory')
    
    args = parser.parse_args()
    
    print("Starting Interactive LSE Simulator...")
    print("Press any key to begin (or Ctrl+C to cancel)")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return
    
    sim = InteractiveSimulator(
        config_path=args.config,
        seed=args.seed,
        initial_biome=args.biome
    )
    
    try:
        sim.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
