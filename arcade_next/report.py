"""HTML report generation using Jinja2 and Mermaid.js."""

from pathlib import Path

from jinja2 import Template

from arcade_next.facts import DependencyGraph
from arcade_next.recovery import Architecture
from arcade_next.smells import SmellInstance


REPORT_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARCADE-Next: {{ repo_name }} ({{ version }})</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6; color: #1a1a2e; background: #f8f9fa;
            max-width: 1200px; margin: 0 auto; padding: 2rem;
        }
        h1 { font-size: 1.8rem; margin-bottom: 0.25rem; }
        h2 { font-size: 1.3rem; margin: 2rem 0 1rem; border-bottom: 2px solid #e0e0e0; padding-bottom: 0.5rem; }
        h3 { font-size: 1.1rem; margin: 1rem 0 0.5rem; }
        .subtitle { color: #666; margin-bottom: 2rem; }
        .stats {
            display: flex; gap: 1.5rem; margin-bottom: 2rem; flex-wrap: wrap;
        }
        .stat-card {
            background: white; border-radius: 8px; padding: 1rem 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); min-width: 140px;
        }
        .stat-card .number { font-size: 1.8rem; font-weight: 700; color: #2563eb; }
        .stat-card .label { font-size: 0.85rem; color: #666; }
        .card {
            background: white; border-radius: 8px; padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 1rem;
        }
        .mermaid { text-align: center; margin: 1rem 0; }
        table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
        th, td { text-align: left; padding: 0.75rem; border-bottom: 1px solid #e0e0e0; }
        th { background: #f1f5f9; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; }
        td { font-size: 0.9rem; }
        .class-list { font-family: monospace; font-size: 0.8rem; color: #555; max-width: 500px; }
        .smell {
            border-left: 4px solid #ccc; padding: 1rem 1.5rem; margin-bottom: 1rem;
            background: white; border-radius: 0 8px 8px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .smell.high { border-left-color: #ef4444; }
        .smell.medium { border-left-color: #f59e0b; }
        .smell.low { border-left-color: #3b82f6; }
        .smell-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; }
        .badge {
            font-size: 0.7rem; font-weight: 600; padding: 0.2rem 0.6rem;
            border-radius: 99px; text-transform: uppercase;
        }
        .badge.high { background: #fef2f2; color: #dc2626; }
        .badge.medium { background: #fffbeb; color: #d97706; }
        .badge.low { background: #eff6ff; color: #2563eb; }
        .smell-detail { margin: 0.5rem 0; font-size: 0.9rem; }
        .smell-detail strong { display: inline-block; width: 100px; color: #555; }
        .rationale { background: #f8fafc; padding: 1rem; border-radius: 6px; font-style: italic; color: #555; }
        footer { margin-top: 3rem; text-align: center; color: #999; font-size: 0.8rem; }
    </style>
</head>
<body>
    <h1>ARCADE-Next Architecture Report</h1>
    <p class="subtitle">{{ repo_name }} &mdash; version {{ version }}</p>

    <div class="stats">
        <div class="stat-card">
            <div class="number">{{ num_entities }}</div>
            <div class="label">Classes</div>
        </div>
        <div class="stat-card">
            <div class="number">{{ num_edges }}</div>
            <div class="label">Dependencies</div>
        </div>
        <div class="stat-card">
            <div class="number">{{ num_components }}</div>
            <div class="label">Components</div>
        </div>
        <div class="stat-card">
            <div class="number">{{ num_smells }}</div>
            <div class="label">Smells Detected</div>
        </div>
    </div>

    <h2>Architecture Diagram</h2>
    <div class="card">
        <pre class="mermaid">
{{ mermaid_diagram }}
        </pre>
    </div>

    {% if rationale %}
    <div class="rationale">{{ rationale }}</div>
    {% endif %}

    <h2>Components</h2>
    <table>
        <thead>
            <tr>
                <th>Component</th>
                <th>Responsibility</th>
                <th>#</th>
                <th>Classes</th>
            </tr>
        </thead>
        <tbody>
        {% for comp in components %}
            <tr>
                <td><strong>{{ comp.name }}</strong></td>
                <td>{{ comp.responsibility }}</td>
                <td>{{ comp.classes | length }}</td>
                <td class="class-list">{{ comp.classes[:8] | join(', ') }}{% if comp.classes | length > 8 %}, ... (+{{ comp.classes | length - 8 }} more){% endif %}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>

    <h2>Architectural Smells ({{ num_smells }})</h2>
    {% if smells %}
    {% for smell in smells %}
    <div class="smell {{ smell.severity }}">
        <div class="smell-header">
            <span class="badge {{ smell.severity }}">{{ smell.severity }}</span>
            <strong>{{ smell.smell_type }}</strong>
        </div>
        <p class="smell-detail">{{ smell.description }}</p>
        <p class="smell-detail"><strong>Why:</strong> {{ smell.explanation }}</p>
        <p class="smell-detail"><strong>Fix:</strong> {{ smell.suggestion }}</p>
        <p class="smell-detail"><strong>Affects:</strong> {{ smell.affected_components | join(', ') }}</p>
    </div>
    {% endfor %}
    {% else %}
    <div class="card">
        <p>No architectural smells detected. The architecture appears well-structured.</p>
    </div>
    {% endif %}

    <h2>Dependency Summary</h2>
    <div class="card">
        <table>
            <thead><tr><th>Package</th><th>Classes</th></tr></thead>
            <tbody>
            {% for pkg, classes in packages %}
                <tr>
                    <td><code>{{ pkg or '(default)' }}</code></td>
                    <td>{{ classes | length }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>

    <footer>
        Generated by ARCADE-Next &mdash; AI-powered architecture recovery
    </footer>

    <script>mermaid.initialize({ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' });</script>
</body>
</html>
""")


def generate_report(
    repo_name: str,
    version: str,
    dep_graph: DependencyGraph,
    architecture: Architecture,
    smells: list[SmellInstance],
    output_path: Path,
) -> Path:
    """Generate an HTML architecture report."""
    mermaid = _build_mermaid_diagram(architecture, dep_graph)

    packages = sorted(dep_graph.packages.items(), key=lambda x: -len(x[1]))

    html = REPORT_TEMPLATE.render(
        repo_name=repo_name,
        version=version,
        num_entities=dep_graph.num_entities,
        num_edges=dep_graph.num_edges,
        num_components=len(architecture.components),
        num_smells=len(smells),
        mermaid_diagram=mermaid,
        rationale=architecture.rationale,
        components=architecture.components,
        smells=smells,
        packages=packages,
    )

    output_path.write_text(html)
    return output_path


def _build_mermaid_diagram(
    architecture: Architecture,
    dep_graph: DependencyGraph,
) -> str:
    """Build a Mermaid.js flowchart of the architecture."""
    lines = ["graph TD"]

    # Sanitize node IDs for Mermaid (no spaces, special chars)
    def node_id(name: str) -> str:
        return name.replace(" ", "_").replace("-", "_").replace(".", "_")

    # Add component nodes with class counts
    for comp in architecture.components:
        nid = node_id(comp.name)
        label = f"{comp.name}\\n({len(comp.classes)} classes)"
        lines.append(f"    {nid}[\"{label}\"]")

    # Add edges between components
    comp_deps = architecture.component_dependencies(dep_graph)
    seen_edges = set()
    for src, tgt in comp_deps:
        edge_key = (node_id(src), node_id(tgt))
        if edge_key not in seen_edges:
            lines.append(f"    {edge_key[0]} --> {edge_key[1]}")
            seen_edges.add(edge_key)

    return "\n".join(lines)
