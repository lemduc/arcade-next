"""CLI entry point for ARCADE-Next."""

import argparse
import sys
import time
from pathlib import Path

from arcade_next.ingestion import ingest
from arcade_next.facts import extract_dependencies
from arcade_next.recovery import recover_architecture
from arcade_next.smells import detect_smells
from arcade_next.report import generate_report


def main():
    parser = argparse.ArgumentParser(
        prog="arcade-next",
        description="AI-powered software architecture recovery",
    )
    parser.add_argument(
        "source",
        help="Git repository URL or local directory path",
    )
    parser.add_argument(
        "-o", "--output",
        default="arcade_report.html",
        help="Output HTML report path (default: arcade_report.html)",
    )
    parser.add_argument(
        "--work-dir",
        default=None,
        help="Working directory for cloned repos (default: temp dir)",
    )
    parser.add_argument(
        "--skip-smells",
        action="store_true",
        help="Skip smell detection (faster, no LLM calls for smells)",
    )
    args = parser.parse_args()

    t0 = time.time()
    print(f"\nARCADE-Next: AI-Powered Architecture Recovery")
    print(f"{'=' * 48}\n")

    # Step 1: Ingest
    print("[1/4] Ingesting repository...")
    work_dir = Path(args.work_dir) if args.work_dir else None
    repo = ingest(args.source, work_dir=work_dir)
    print(f"  -> {repo.name} (version: {repo.version})")
    print(f"  -> Found {len(repo.java_files)} Java files")

    if not repo.java_files:
        print("\nError: No Java files found. ARCADE-Next currently supports Java projects only.")
        sys.exit(1)

    # Step 2: Extract dependencies
    print("\n[2/4] Extracting dependencies (tree-sitter)...")
    dep_graph = extract_dependencies(repo.java_files, repo.path)
    print(f"  -> {dep_graph.num_entities} classes, {dep_graph.num_edges} dependency edges")
    print(f"  -> {len(dep_graph.packages)} packages")

    if dep_graph.num_entities == 0:
        print("\nError: No Java classes extracted. Check that the source contains valid Java code.")
        sys.exit(1)

    # Step 3: Recover architecture
    print("\n[3/4] Recovering architecture (Claude)...")
    architecture = recover_architecture(dep_graph)
    print(f"  -> Identified {len(architecture.components)} components")
    for comp in architecture.components:
        print(f"     - {comp.name} ({len(comp.classes)} classes)")

    # Step 4: Detect smells
    smells = []
    if not args.skip_smells:
        print("\n[4/4] Detecting architectural smells...")
        smells = detect_smells(architecture, dep_graph)
        if smells:
            print(f"  -> Found {len(smells)} smell(s):")
            for s in smells:
                print(f"     [{s.severity.upper()}] {s.smell_type}: {s.description[:80]}")
        else:
            print("  -> No architectural smells detected")
    else:
        print("\n[4/4] Skipping smell detection (--skip-smells)")

    # Generate report
    output_path = Path(args.output)
    print(f"\nGenerating report...")
    generate_report(
        repo_name=repo.name,
        version=repo.version,
        dep_graph=dep_graph,
        architecture=architecture,
        smells=smells,
        output_path=output_path,
    )

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"Report saved to: {output_path.resolve()}")

    # Cleanup temp directory if needed
    repo.cleanup()


if __name__ == "__main__":
    main()
