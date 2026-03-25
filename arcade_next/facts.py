"""Dependency extraction from Java source using tree-sitter."""

from dataclasses import dataclass, field
from pathlib import Path

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser


JAVA_LANGUAGE = Language(tsjava.language())


@dataclass
class JavaEntity:
    """A Java class, interface, or enum."""
    name: str
    fqn: str  # fully qualified name
    package: str
    file_path: str
    imports: list[str] = field(default_factory=list)
    superclass: str | None = None
    interfaces: list[str] = field(default_factory=list)


@dataclass
class DependencyGraph:
    """Dependency graph extracted from source code."""
    entities: dict[str, JavaEntity]  # fqn -> entity
    edges: list[tuple[str, str, str]]  # (source_fqn, target_fqn, relation_type)
    packages: dict[str, list[str]]  # package -> [fqn, ...]

    @property
    def num_entities(self) -> int:
        return len(self.entities)

    @property
    def num_edges(self) -> int:
        return len(self.edges)

    def to_adjacency(self) -> dict[str, list[str]]:
        """Convert to adjacency list (ignoring edge types)."""
        adj: dict[str, list[str]] = {fqn: [] for fqn in self.entities}
        for src, tgt, _ in self.edges:
            if src in adj:
                adj[src].append(tgt)
        return adj


def _collect_nodes(node, type_name: str) -> list:
    """Recursively collect all descendant nodes of a given type."""
    results = []
    if node.type == type_name:
        results.append(node)
    for child in node.children:
        results.extend(_collect_nodes(child, type_name))
    return results


def _get_child_by_field(node, field_name: str):
    """Get a child node by field name."""
    return node.child_by_field_name(field_name)


def _get_text(node) -> str:
    """Get the text content of a node."""
    if node is None:
        return ""
    return node.text.decode()


def _extract_package(root_node) -> str:
    """Extract the package declaration from a Java file."""
    for child in root_node.children:
        if child.type == "package_declaration":
            for sub in child.children:
                if sub.type == "scoped_identifier":
                    return _get_text(sub)
    return ""


def _extract_imports(root_node) -> list[str]:
    """Extract all import declarations."""
    imports = []
    for child in root_node.children:
        if child.type == "import_declaration":
            for sub in child.children:
                if sub.type == "scoped_identifier":
                    imports.append(_get_text(sub))
    return imports


def _extract_type_declarations(root_node) -> list[dict]:
    """Extract class, interface, and enum declarations with inheritance info."""
    decls = []
    for node in root_node.children:
        if node.type in ("class_declaration", "interface_declaration", "enum_declaration"):
            decl = _parse_type_declaration(node)
            if decl:
                decls.append(decl)
    return decls


def _parse_type_declaration(node) -> dict | None:
    """Parse a single type declaration node."""
    name_node = _get_child_by_field(node, "name")
    if not name_node:
        return None

    decl = {
        "name": _get_text(name_node),
        "superclass": None,
        "interfaces": [],
    }

    for child in node.children:
        # Superclass: (superclass (type_identifier))
        if child.type == "superclass":
            for sub in child.children:
                if sub.type == "type_identifier":
                    decl["superclass"] = _get_text(sub)
                    break

        # Interfaces: (super_interfaces (type_list ...))
        if child.type == "super_interfaces":
            for sub in child.children:
                if sub.type == "type_list":
                    for type_node in sub.children:
                        if type_node.type == "type_identifier":
                            decl["interfaces"].append(_get_text(type_node))

    return decl


def extract_dependencies(java_files: list[Path], root: Path) -> DependencyGraph:
    """Extract dependency graph from Java source files.

    Args:
        java_files: List of .java file paths.
        root: Root directory of the project (for computing relative paths).

    Returns:
        DependencyGraph with entities, edges, and package info.
    """
    parser = Parser(JAVA_LANGUAGE)

    entities: dict[str, JavaEntity] = {}
    edges: list[tuple[str, str, str]] = []
    packages: dict[str, list[str]] = {}

    # First pass: collect all entities
    for java_file in java_files:
        try:
            source = java_file.read_bytes()
            tree = parser.parse(source)
        except Exception:
            continue

        root_node = tree.root_node
        package = _extract_package(root_node)
        imports = _extract_imports(root_node)
        rel_path = str(java_file.relative_to(root))

        type_decls = _extract_type_declarations(root_node)
        for decl in type_decls:
            class_name = decl["name"]
            fqn = f"{package}.{class_name}" if package else class_name

            entity = JavaEntity(
                name=class_name,
                fqn=fqn,
                package=package,
                file_path=rel_path,
                imports=imports,
                superclass=decl["superclass"],
                interfaces=decl["interfaces"],
            )

            entities[fqn] = entity
            packages.setdefault(package, []).append(fqn)

    # Build name -> fqn index (for resolving simple names)
    fqn_index: dict[str, str] = {}
    for entity in entities.values():
        fqn_index[entity.name] = entity.fqn

    # Second pass: resolve dependencies
    for entity in entities.values():
        # Import edges
        for imp in entity.imports:
            target = imp
            if target in entities:
                edges.append((entity.fqn, target, "import"))
            else:
                simple = imp.split(".")[-1]
                if simple in fqn_index and fqn_index[simple] != entity.fqn:
                    edges.append((entity.fqn, fqn_index[simple], "import"))

        # Inheritance edge
        if entity.superclass:
            target_fqn = _resolve_name(entity.superclass, entity, fqn_index, entities)
            if target_fqn:
                edges.append((entity.fqn, target_fqn, "extends"))

        # Interface edges
        for iface in entity.interfaces:
            target_fqn = _resolve_name(iface, entity, fqn_index, entities)
            if target_fqn:
                edges.append((entity.fqn, target_fqn, "implements"))

    # Deduplicate edges
    edges = list(set(edges))

    return DependencyGraph(entities=entities, edges=edges, packages=packages)


def _resolve_name(
    simple_name: str,
    source_entity: JavaEntity,
    fqn_index: dict[str, str],
    entities: dict[str, JavaEntity],
) -> str | None:
    """Resolve a simple class name to its FQN."""
    if simple_name in entities:
        return simple_name

    for imp in source_entity.imports:
        if imp.endswith(f".{simple_name}") and imp in entities:
            return imp

    same_pkg_fqn = f"{source_entity.package}.{simple_name}"
    if same_pkg_fqn in entities:
        return same_pkg_fqn

    if simple_name in fqn_index:
        return fqn_index[simple_name]

    return None
