# CLAUDE.md

## What This Is

ARCADE-Next is an AI-powered software architecture recovery tool. It replaces the original ARCADE's manual setup, commercial tooling, and statistical topic modeling with tree-sitter + Claude CLI. Point it at a Java project, get an HTML report with recovered components, dependency diagrams, and architectural smell descriptions.

## Quick Reference

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Run
python -m arcade_next /path/to/java/project
python -m arcade_next https://github.com/user/repo

# Mock mode (no LLM, package-based heuristics)
ARCADE_MOCK=1 python -m arcade_next /path/to/java/project

# Change model
ARCADE_MODEL=haiku python -m arcade_next /path/to/java/project
```

## Architecture

4-stage pipeline orchestrated by `__main__.py`:

```
ingestion.py → facts.py → recovery.py → smells.py → report.py
                                ↑              ↑
                              llm.py         llm.py
```

| Module | Responsibility |
|--------|---------------|
| `ingestion.py` | Clone repos (shallow), detect version tags, collect `.java` files |
| `facts.py` | Parse Java with tree-sitter → `DependencyGraph` (entities, edges, packages) |
| `recovery.py` | Send dependency graph to Claude → named components with rationale. Falls back to package-based grouping in mock mode |
| `smells.py` | Dependency cycles via NetworkX SCC (always algorithmic). Concern overload + scattered functionality via Claude (or heuristic in mock mode) |
| `report.py` | Jinja2 HTML report with Mermaid.js diagrams, component tables, smell cards |
| `llm.py` | Claude CLI subprocess wrapper. Handles mock mode, model selection, env stripping for nested invocation |

## Key Domain Objects

All defined as `@dataclass` in their respective modules:

- `IngestedRepo` — path, name, version, java files
- `JavaEntity` — fully qualified name, kind, package, file path
- `DependencyGraph` — entities dict, typed edges list, package groupings
- `Component` — name, class list, responsibility description
- `Architecture` — components list, rationale string
- `SmellInstance` — smell type, severity, affected components, explanation, suggested fix

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ARCADE_MOCK` | unset | Set to `1` to skip all LLM calls (package-based fallback) |
| `ARCADE_MODEL` | `sonnet` | Claude model: `haiku`, `sonnet`, `opus` |

## Coding Conventions

- **Python 3.12+** — uses PEP 585 syntax: `list[str]`, `str | None` (not `Optional`)
- **Type hints** on all function signatures and return types
- **Dataclasses** for domain objects with typed fields
- **Naming**: `snake_case` functions/modules, `PascalCase` classes, `UPPER_SNAKE_CASE` constants, `_leading_underscore` private functions
- **Docstrings**: Google style with Args/Returns sections
- **Imports**: stdlib → third-party → relative internal (`from arcade_next.facts import ...`)
- **No linter/formatter configured** — follow existing style

## Testing

No test suite yet. Validate manually:
- Run on example projects and inspect HTML output
- Compare against reference reports in `examples/`
- Use `ARCADE_MOCK=1` for fast iteration without LLM calls

## Project Constraints

- Java only (tree-sitter grammars for other languages available but not wired up)
- Single version analysis (no multi-version evolution tracking yet)
- 3 of 11 original ARCADE smell types implemented
- Requires Claude Code CLI installed and authenticated for LLM mode
