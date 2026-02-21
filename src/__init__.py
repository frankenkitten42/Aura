"""
Living Soundscape Engine (LSE)

A system-driven soundscape logic engine paired with a Sensory Discomfort Index (SDI)
for dynamic audio environment management in games.

Main entry points:
- LSEEngine: The main engine class for integration
- SimulationRunner: For running simulations and demos
- load_config: For loading configuration from JSON files

Example:
    >>> from src import LSEEngine
    >>> engine = LSEEngine(config_path="config/")
    >>> engine.set_environment(biome_id="forest")
    >>> events = engine.tick(delta_time=1.0)
"""

__version__ = "0.5.0"
__author__ = "LSE Project"

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == 'LSEEngine':
        from .engine import LSEEngine
        return LSEEngine
    elif name == 'EnvironmentState':
        from .engine import EnvironmentState
        return EnvironmentState
    elif name == 'EngineStats':
        from .engine import EngineStats
        return EngineStats
    elif name == 'SimulationRunner':
        from .simulation import SimulationRunner
        return SimulationRunner
    elif name == 'SimulationResults':
        from .simulation import SimulationResults
        return SimulationResults
    elif name == 'run_demo':
        from .simulation import run_demo
        return run_demo
    elif name == 'load_config':
        from .config import load_config
        return load_config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'LSEEngine',
    'EnvironmentState',
    'EngineStats',
    'SimulationRunner',
    'SimulationResults',
    'run_demo',
    'load_config',
]
