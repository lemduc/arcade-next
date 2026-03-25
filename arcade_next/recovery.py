"""LLM-based software architecture recovery."""

from dataclasses import dataclass, field

from arcade_next.facts import DependencyGraph
from arcade_next.llm import ask_claude_json, MOCK_MODE


@dataclass
class Component:
    """A recovered architectural component."""
    name: str
    responsibility: str
    classes: list[str]


@dataclass
class Architecture:
    """A recovered software architecture."""
    components: list[Component]
    rationale: str

    def component_of(self, fqn: str) -> str | None:
        """Find which component a class belongs to."""
        for comp in self.components:
            if fqn in comp.classes:
                return comp.name
        return None

    def component_dependencies(
        self, dep_graph: DependencyGraph
    ) -> list[tuple[str, str]]:
        """Compute component-level dependencies from class-level edges."""
        comp_edges: set[tuple[str, str]] = set()
        for src, tgt, _ in dep_graph.edges:
            src_comp = self.component_of(src)
            tgt_comp = self.component_of(tgt)
            if src_comp and tgt_comp and src_comp != tgt_comp:
                comp_edges.add((src_comp, tgt_comp))
        return sorted(comp_edges)


def recover_architecture(dep_graph: DependencyGraph) -> Architecture:
    """Recover software architecture using Claude.

    Sends the dependency graph and package structure to Claude,
    which identifies logical components and assigns classes.
    """
    # Build the context for Claude
    package_summary = _build_package_summary(dep_graph)
    dependency_summary = _build_dependency_summary(dep_graph)

    system_prompt = """You are a software architecture expert. Your task is to recover
the high-level architectural components of a Java software system by analyzing its
dependency structure and package organization.

Group related classes into logical architectural components based on:
1. Package structure (classes in the same package often belong together)
2. Dependency patterns (classes that depend on each other heavily likely belong together)
3. Naming conventions (classes with similar prefixes/suffixes often serve similar roles)
4. Separation of concerns (UI, business logic, data access, utilities, etc.)

Aim for 5-15 components for a medium-sized system. Each component should have a clear,
single responsibility."""

    prompt = f"""Analyze this Java system and identify its architectural components.

## Package Structure and Classes
{package_summary}

## Dependencies Between Classes
{dependency_summary}

Respond with ONLY valid JSON in this exact format:
{{
    "components": [
        {{
            "name": "ComponentName",
            "responsibility": "One-sentence description of what this component does",
            "classes": ["com.example.ClassA", "com.example.ClassB"]
        }}
    ],
    "rationale": "Brief explanation of the overall architectural style and key design decisions"
}}

IMPORTANT:
- Every class listed in the package structure MUST be assigned to exactly one component.
- Component names should be descriptive (e.g., "DataAccess", "UserInterface", "CoreEngine").
- Do NOT leave any class unassigned."""

    if MOCK_MODE:
        return _package_based_recovery(dep_graph)

    result = ask_claude_json(prompt, system=system_prompt)

    components = [
        Component(
            name=c["name"],
            responsibility=c["responsibility"],
            classes=c["classes"],
        )
        for c in result["components"]
    ]

    return Architecture(
        components=components,
        rationale=result.get("rationale", ""),
    )


def _package_based_recovery(dep_graph: DependencyGraph) -> Architecture:
    """Fallback: group classes by meaningful package segments (mock/no-LLM mode)."""
    # Find the common prefix to strip (e.g., "edu.usc.softarch.arcade")
    all_pkgs = [e.package for e in dep_graph.entities.values() if e.package]
    common = _common_prefix_segments(all_pkgs) if all_pkgs else []

    groups: dict[str, list[str]] = {}
    for fqn, entity in dep_graph.entities.items():
        parts = entity.package.split(".")
        # Strip common prefix, then use the next 1-2 segments as component key
        remainder = parts[len(common):]
        if remainder:
            key = ".".join(remainder[:2])
        else:
            key = parts[-1] if parts[0] else "(default)"
        groups.setdefault(key, []).append(fqn)

    components = []
    for key in sorted(groups.keys()):
        name = key.split(".")[-1] if "." in key else key
        name = name.replace("_", " ").title().replace(" ", "")
        components.append(Component(
            name=name,
            responsibility=f"Classes in {key}",
            classes=sorted(groups[key]),
        ))

    return Architecture(
        components=components,
        rationale="Package-based grouping (mock mode — no LLM). Run without ARCADE_MOCK=1 for AI-powered recovery.",
    )


def _common_prefix_segments(packages: list[str]) -> list[str]:
    """Find the longest common package prefix across all packages."""
    if not packages:
        return []
    split_pkgs = [p.split(".") for p in packages]
    prefix = []
    for segments in zip(*split_pkgs):
        if len(set(segments)) == 1:
            prefix.append(segments[0])
        else:
            break
    return prefix


def _build_package_summary(dep_graph: DependencyGraph) -> str:
    """Build a concise package structure summary."""
    lines = []
    for pkg in sorted(dep_graph.packages.keys()):
        classes = dep_graph.packages[pkg]
        lines.append(f"\n### {pkg or '(default package)'} ({len(classes)} classes)")
        for fqn in sorted(classes):
            entity = dep_graph.entities[fqn]
            extras = []
            if entity.superclass:
                extras.append(f"extends {entity.superclass}")
            if entity.interfaces:
                extras.append(f"implements {', '.join(entity.interfaces)}")
            suffix = f"  [{', '.join(extras)}]" if extras else ""
            lines.append(f"  - {entity.name}{suffix}")
    return "\n".join(lines)


def _build_dependency_summary(dep_graph: DependencyGraph) -> str:
    """Build a concise dependency summary (package-level to save tokens)."""
    # Aggregate to package-level dependencies
    pkg_deps: dict[tuple[str, str], int] = {}
    for src, tgt, rel_type in dep_graph.edges:
        src_entity = dep_graph.entities.get(src)
        tgt_entity = dep_graph.entities.get(tgt)
        if src_entity and tgt_entity:
            src_pkg = src_entity.package
            tgt_pkg = tgt_entity.package
            if src_pkg != tgt_pkg:
                key = (src_pkg, tgt_pkg)
                pkg_deps[key] = pkg_deps.get(key, 0) + 1

    lines = []
    for (src_pkg, tgt_pkg), count in sorted(
        pkg_deps.items(), key=lambda x: -x[1]
    ):
        lines.append(f"  {src_pkg} -> {tgt_pkg}  ({count} edges)")

    if not lines:
        return "  (no cross-package dependencies found)"

    # Limit to top 100 to save tokens
    if len(lines) > 100:
        lines = lines[:100]
        lines.append(f"  ... and {len(pkg_deps) - 100} more package-level dependencies")

    return "\n".join(lines)
