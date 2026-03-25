"""Architectural smell detection with LLM-powered explanations."""

from dataclasses import dataclass, field

import networkx as nx

from arcade_next.facts import DependencyGraph
from arcade_next.llm import ask_claude_json, MOCK_MODE
from arcade_next.recovery import Architecture


@dataclass
class SmellInstance:
    """A detected architectural smell."""
    smell_type: str
    severity: str  # "high", "medium", "low"
    affected_components: list[str]
    description: str
    explanation: str
    suggestion: str


def detect_smells(
    architecture: Architecture,
    dep_graph: DependencyGraph,
) -> list[SmellInstance]:
    """Detect architectural smells in the recovered architecture.

    Detects three smell types:
    1. Dependency cycles (structural, via NetworkX SCC)
    2. Concern overload (LLM-based)
    3. Scattered functionality (LLM-based)
    """
    smells: list[SmellInstance] = []

    # 1. Dependency cycles (algorithmic — same approach as original ARCADE)
    cycle_smells = _detect_dependency_cycles(architecture, dep_graph)
    smells.extend(cycle_smells)

    # 2 & 3. Concern overload + scattered functionality
    if MOCK_MODE:
        heuristic_smells = _detect_heuristic_smells(architecture)
        smells.extend(heuristic_smells)
    else:
        llm_smells = _detect_llm_smells(architecture, dep_graph)
        smells.extend(llm_smells)

    return smells


def _detect_dependency_cycles(
    architecture: Architecture,
    dep_graph: DependencyGraph,
) -> list[SmellInstance]:
    """Detect dependency cycles at the component level using Kosaraju's algorithm."""
    # Build component-level directed graph
    G = nx.DiGraph()
    for comp in architecture.components:
        G.add_node(comp.name)
    for src_comp, tgt_comp in architecture.component_dependencies(dep_graph):
        G.add_edge(src_comp, tgt_comp)

    # Find strongly connected components with > 1 node (= cycles)
    smells = []
    for scc in nx.strongly_connected_components(G):
        if len(scc) > 1:
            cycle_members = sorted(scc)
            # Determine severity by cycle size
            if len(cycle_members) >= 5:
                severity = "high"
            elif len(cycle_members) >= 3:
                severity = "medium"
            else:
                severity = "low"

            smells.append(SmellInstance(
                smell_type="Dependency Cycle",
                severity=severity,
                affected_components=cycle_members,
                description=(
                    f"Circular dependency among {len(cycle_members)} components: "
                    f"{' <-> '.join(cycle_members)}"
                ),
                explanation=(
                    "Dependency cycles make components tightly coupled — you cannot "
                    "change, test, or deploy any component in the cycle independently. "
                    "This hinders maintainability, increases build times, and makes "
                    "the system harder to understand."
                ),
                suggestion=(
                    "Break the cycle by introducing an interface/abstraction that "
                    "one component depends on, inverting the dependency direction. "
                    "Consider the Dependency Inversion Principle (DIP)."
                ),
            ))
    return smells


def _detect_llm_smells(
    architecture: Architecture,
    dep_graph: DependencyGraph,
) -> list[SmellInstance]:
    """Use Claude to detect concern overload and scattered functionality."""
    # Build component summary for the LLM
    comp_summary = []
    for comp in architecture.components:
        comp_deps = [
            tgt for src, tgt in architecture.component_dependencies(dep_graph)
            if src == comp.name
        ]
        comp_summary.append({
            "name": comp.name,
            "responsibility": comp.responsibility,
            "num_classes": len(comp.classes),
            "classes": comp.classes[:20],  # limit for token budget
            "depends_on": comp_deps,
        })

    import json
    prompt = f"""Analyze this software architecture for architectural smells.

## Architecture Components
{json.dumps(comp_summary, indent=2)}

Look for these specific smell types:

1. **Concern Overload**: A component has too many responsibilities or contains classes
   that serve unrelated purposes. Signs: large class count, vague responsibility, classes
   with diverse naming patterns.

2. **Scattered Functionality**: A single concern (e.g., logging, security, data validation)
   is spread across many unrelated components instead of being centralized. Signs: similar
   class names or patterns appearing in multiple components.

Respond with ONLY valid JSON:
{{
    "smells": [
        {{
            "smell_type": "Concern Overload" or "Scattered Functionality",
            "severity": "high" or "medium" or "low",
            "affected_components": ["ComponentA", "ComponentB"],
            "description": "What the smell is",
            "explanation": "Why this is a problem for maintainability and evolution",
            "suggestion": "Concrete refactoring action to fix it"
        }}
    ]
}}

If no smells are found, return {{"smells": []}}.
Be conservative — only report clear, actionable smells, not speculative ones."""

    result = ask_claude_json(prompt)

    smells = []
    for s in result.get("smells", []):
        smells.append(SmellInstance(
            smell_type=s["smell_type"],
            severity=s["severity"],
            affected_components=s["affected_components"],
            description=s["description"],
            explanation=s["explanation"],
            suggestion=s["suggestion"],
        ))
    return smells


def _detect_heuristic_smells(architecture: Architecture) -> list[SmellInstance]:
    """Heuristic smell detection (mock mode — no LLM)."""
    smells = []
    # Concern overload: component with > 20 classes
    for comp in architecture.components:
        if len(comp.classes) > 20:
            smells.append(SmellInstance(
                smell_type="Concern Overload",
                severity="high" if len(comp.classes) > 40 else "medium",
                affected_components=[comp.name],
                description=f"{comp.name} contains {len(comp.classes)} classes, suggesting multiple responsibilities.",
                explanation="Large components are harder to understand, test, and maintain. They often indicate that multiple concerns have been mixed together.",
                suggestion=f"Consider splitting {comp.name} into smaller, focused components with single responsibilities.",
            ))
    return smells
