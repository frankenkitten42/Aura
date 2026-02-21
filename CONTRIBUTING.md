# Contributing to AURA

Thank you for your interest in contributing to AURA! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git

### Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/aura.git
   cd aura
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific phase tests
python -m pytest tests/test_vde_phase1.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - Python version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs or error messages

### Suggesting Features

1. Check existing issues/discussions
2. Describe the use case
3. Explain how it fits AURA's design philosophy (subtle, invisible influence)

### Submitting Code

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the code style guidelines

3. Add tests for new functionality

4. Ensure all tests pass:
   ```bash
   python -m pytest tests/ -v
   ```

5. Commit with clear messages:
   ```bash
   git commit -m "Add: brief description of change"
   ```

6. Push and create a Pull Request

## Code Style

### Python

- Follow PEP 8
- Use type hints for function signatures
- Document classes and public methods with docstrings
- Keep functions focused and small

### Example

```python
def calculate_pressure(population: float, config: PressureConfig) -> float:
    """
    Calculate environmental pressure from population.
    
    Args:
        population: Population ratio (0.0 to 1.0)
        config: Pressure configuration
        
    Returns:
        Pressure value (-1.0 to 1.0)
    """
    # Implementation...
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `WildlifeManager` |
| Functions | snake_case | `calculate_pressure` |
| Constants | UPPER_SNAKE | `MAX_POPULATION` |
| Config classes | PascalCase + Config | `WildlifeConfig` |
| Snapshot classes | PascalCase + Snapshot | `WildlifeSnapshot` |
| UE5 params | F + PascalCase | `FWildlifeParameters` |

### File Organization

```
src/vde/
├── module_name.py      # Main implementation
│   ├── Enums           # At top
│   ├── Config class    # Configuration dataclass
│   ├── State classes   # Internal state
│   ├── Snapshot class  # Public state snapshot
│   ├── Manager class   # Main logic
│   └── UE5 params      # FParameters class
```

## Design Philosophy

When contributing, keep these principles in mind:

### 1. Invisibility

The system should never be obvious to players. If a feature would be noticeable as a "game mechanic," reconsider the approach.

### 2. Subtlety

- Gradual changes, not sudden shifts
- Multiple small effects, not one large effect
- Cross-modal (audio + visual), not single-channel

### 3. Plausibility

Effects should have logical explanations:
- ✓ "Wildlife left because it's crowded"
- ✓ "The grass is worn from foot traffic"
- ✗ "The screen turned gray to punish you"

### 4. Asymmetry

- Rise fast, recover slow
- Audio leads, visual follows
- Never synchronize peaks

## Testing Guidelines

### Test Structure

Each module should have corresponding tests:

```
tests/
├── test_vde_phase1.py  # Core VDI tests
├── test_vde_phase2.py  # UE5 integration tests
...
```

### What to Test

- State transitions
- Edge cases (0%, 100% population)
- Configuration variations
- Reset functionality
- UE5 parameter generation
- Integration scenarios

### Test Naming

```python
def test_wildlife_flees_at_threshold():
    """Wildlife should transition to FLEEING at flee_threshold."""
    ...

def test_high_population_causes_stressed_comfort():
    """NPCs should become STRESSED above 70% population."""
    ...
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure CI passes
4. Request review from maintainers
5. Address feedback
6. Squash commits if requested

## Questions?

Open a discussion or issue if you have questions about contributing.

Thank you for helping make AURA better!
