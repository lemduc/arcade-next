# ARCADE-Next

AI-powered software architecture recovery, change, and decay evaluator.

ARCADE-Next is a reimagining of [ARCADE](https://bitbucket.org/joshuaga/arcade) that replaces manual setup, commercial tooling, and statistical topic modeling with **tree-sitter** for dependency extraction and the **Claude CLI** for AI-driven architecture recovery and smell explanation. Point it at a Java project and get back an interactive HTML report with recovered components, dependency diagrams, and actionable architectural smell descriptions — zero configuration required.

## Quick Start

```bash
# Set up
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Analyze a local Java project
python -m arcade_next /path/to/java/project

# Analyze a remote repo
python -m arcade_next https://github.com/apache/struts

# Output
open arcade_report.html
```

### Prerequisites

- Python 3.12+
- [Claude Code CLI](https://claude.ai/code) installed and authenticated (`claude` command available in PATH)

## Usage

```
usage: arcade-next [-h] [-o OUTPUT] [--work-dir WORK_DIR] [--skip-smells] source

positional arguments:
  source                Git repository URL or local directory path

options:
  -h, --help            show this help message and exit
  -o, --output OUTPUT   Output HTML report path (default: arcade_report.html)
  --work-dir WORK_DIR   Working directory for cloned repos (default: temp dir)
  --skip-smells         Skip smell detection (faster, fewer LLM calls)
```

### Examples

```bash
# Analyze a local project, custom output path
python -m arcade_next ./my-java-app -o my_report.html

# Analyze a GitHub repo into a specific working directory
python -m arcade_next https://github.com/apache/hadoop --work-dir ./repos

# Fast mode: skip LLM-based smell detection
python -m arcade_next ./my-java-app --skip-smells
```

## Pipeline

```
[1/4] Ingest       Clone repo (or use local path), detect version from git tags
                    ↓
[2/4] Extract       Parse .java files with tree-sitter → dependency graph
                    (imports, extends, implements)
                    ↓
[3/4] Recover       Send dependency graph + package structure to Claude →
                    component groupings with semantic names and rationale
                    ↓
[4/4] Detect        Dependency cycles (NetworkX SCC) +
                    Concern overload & scattered functionality (Claude)
                    ↓
      Report        HTML with Mermaid.js architecture diagram,
                    component table, smell cards with explanations
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ARCADE_MODEL` | `sonnet` | Claude model to use (`sonnet`, `haiku`, `opus`) |
| `ARCADE_MOCK` | _(unset)_ | Set to `1` to skip all LLM calls and use package-based heuristics instead. Useful for testing or when no Claude CLI is available. |

```bash
# Use a faster/cheaper model
ARCADE_MODEL=haiku python -m arcade_next ./my-project

# Run without any LLM calls (package-based fallback)
ARCADE_MOCK=1 python -m arcade_next ./my-project
```

## Project Structure

```
arcade_next/
├── pyproject.toml          # Dependencies and build config
├── arcade_next/
│   ├── __main__.py         # CLI entry point — orchestrates the pipeline
│   ├── ingestion.py        # Git clone, version detection, file discovery
│   ├── facts.py            # tree-sitter Java parsing → dependency graph
│   ├── recovery.py         # LLM-based architecture recovery (+ package fallback)
│   ├── smells.py           # Smell detection: cycles (NetworkX) + LLM analysis
│   ├── report.py           # Jinja2 HTML report with Mermaid.js diagrams
│   └── llm.py              # Claude CLI wrapper (subprocess, mock mode)
├── examples/               # Example analysis results
│   ├── ARCADE_SELF_ANALYSIS.md   # Self-analysis of ARCADE's own codebase
│   ├── arcade_report.html        # Package-level recovery report
│   └── arcade_report_ai.html     # AI-based recovery report
└── README.md
```

### Module Details

| Module | What it does |
|--------|-------------|
| **ingestion.py** | Accepts a Git URL or local path. Clones remote repos (shallow), detects the latest version tag, and collects all `.java` files. |
| **facts.py** | Parses Java source with tree-sitter (no compilation needed). Extracts class/interface/enum declarations, import statements, `extends`/`implements` relationships, and builds a `DependencyGraph` with entities, typed edges, and package groupings. |
| **recovery.py** | Sends the dependency graph and package structure to Claude, which identifies logical architectural components, assigns every class to a component, and explains the rationale. In mock mode, falls back to grouping by package hierarchy. |
| **smells.py** | Detects three architectural smell types: (1) **Dependency Cycles** via NetworkX strongly connected components (Kosaraju's algorithm — same approach as original ARCADE), (2) **Concern Overload** and (3) **Scattered Functionality** via Claude analysis. Each smell includes severity, affected components, explanation, and a suggested fix. |
| **report.py** | Renders an HTML report using Jinja2. Architecture diagram is generated as a Mermaid.js flowchart (no GraphViz dependency). Includes stat cards, component table, smell cards with color-coded severity, and a package summary. |
| **llm.py** | Wraps the local `claude` CLI in print mode (`claude -p`). No API key needed — uses your existing Claude Code authentication. Strips the `CLAUDECODE` env var to allow nested invocation from within a Claude Code session. |

## How It Compares to Original ARCADE

| | ARCADE (Java/Maven) | ARCADE-Next |
|--|---------------------|-------------|
| **Setup** | Hours: install SciTools Understand, configure directory layout, rename version folders, tune Mallet parameters, select stopword lists | **One command** — point at a repo URL or directory |
| **Dependency extraction** | SciTools Understand (commercial license) or Classycle (Java bytecode only) | **tree-sitter** (free, open source, no compilation needed) |
| **Semantic analysis** | Mallet LDA: 50 fixed topics, bag-of-words, manual stopword lists | **Claude**: contextual code understanding, no configuration |
| **Architecture recovery** | 4 clustering algorithms (ACDC, ARC, WCA, Limbo) with auto-generated cluster IDs | **Claude**: semantically named components with responsibility descriptions |
| **Smell detection** | 11 rule-based detectors, outputs JSON with component IDs | **3 detectors** (cycles + LLM-based), outputs plain English with "why" and "how to fix" |
| **Output** | RSF text files + JSON | **Interactive HTML** with Mermaid.js diagrams |
| **Language** | Java only (some C/C++ support) | Java (more languages planned via tree-sitter grammars) |

## Detected Smell Types

| Smell | Detection Method | Description |
|-------|-----------------|-------------|
| **Dependency Cycle** | NetworkX SCC (algorithmic) | Circular dependencies between components — prevents independent development and testing |
| **Concern Overload** | Claude analysis | A component has too many unrelated responsibilities |
| **Scattered Functionality** | Claude analysis | A single concern is spread across many unrelated components |

## Examples

We analyzed ARCADE's own codebase with ARCADE-Next. See the results:

- **[Self-Analysis Write-up](examples/ARCADE_SELF_ANALYSIS.md)** — Detailed findings from running ARCADE-Next on ARCADE Core v1.2.0 (162 classes, 465 dependency edges, 2 HIGH-severity smells)
- **[Package-Level Report](examples/arcade_report.html)** — HTML report using package-based clustering (deterministic, no LLM)
- **[AI-Based Report](examples/arcade_report_ai.html)** — HTML report using Claude-powered semantic clustering

Key findings: 6 of 10 recovered components are locked in a dependency cycle, and the utility module is a concern-overloaded dumping ground mixing JSON, graphs, CLI, and statistics. The tool designed to detect these smells has these exact smells.

## Limitations

- **Java only** — tree-sitter grammars for other languages (Python, C++, TypeScript, Go) are available but not yet wired up
- **Single version** — analyzes one version at a time; multi-version evolution tracking is planned
- **3 of 11 smells** — only detects dependency cycles, concern overload, and scattered functionality (original ARCADE detects 11 smell types)
- **No classical clustering** — the 4 classical algorithms (ACDC, ARC, WCA, Limbo) are not yet ported; recovery is LLM-only or package-based
- **LLM latency** — full analysis with Claude takes ~2-3 minutes vs. seconds for mock mode

## License

Research software. See the original [ARCADE project](https://bitbucket.org/joshuaga/arcade) for licensing details.
