# Contributing

## Development setup

```bash
conda create -n holdings-monitor python=3.12 -y
conda activate holdings-monitor
pip install -e .[dev]
```

## Expected checks

```bash
ruff check .
pytest
```

## Scope guidance

High-value contributions:
- new source adapters
- parser fixtures and regression tests
- storage backends
- notification channels
- deployment templates

Avoid unrelated refactors that increase complexity without improving correctness, safety, or extensibility.
