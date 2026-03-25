# Analyzing ARCADE with ARCADE-Next: Self-Analysis Results

**Date:** 2026-03-25
**Tool:** ARCADE-Next (AI-powered, using Claude CLI + tree-sitter)
**Subject:** ARCADE Core v1.2.0 (`src/main/java/edu/`)
**Analysis time:** 169 seconds

---

## At a Glance

| Metric | Value |
|--------|-------|
| Java classes parsed | 162 |
| Dependency edges extracted | 465 |
| Packages | 38 |
| Recovered components | 10 |
| Architectural smells | 2 (both HIGH severity) |

---

## Recovered Architecture

Claude identified **10 architectural components** from ARCADE's 162 classes and 465 dependency edges. The architecture follows a layered pipeline design:

```
DependencyExtraction → ClusteringEngine → AntipatternDetection
                            ↓
                       TopicModeling
                            ↓
                     MetricsComputation
                            ↓
                  ChangeEvolutionAnalysis → DesignDecisionTracking → IssueCommitIntegration
                            ↓
                       Visualization
                            ↓
                     CoreInfrastructure (shared utilities)
```

### Component Breakdown

| Component | Classes | Responsibility |
|-----------|---------|----------------|
| **ClusteringEngine** | 44 | Implements clustering algorithms (ACDC, ARC, WCA, Limbo) to recover architectural components from source code dependencies. Includes similarity measures (Jaccard, UEM, SCM, etc.), stopping/serialization criteria, and ACDC's pattern-based approach (BodyHeader, SubGraph, OrphanAdoption). |
| **CoreInfrastructure** | 24 | Shared utilities: JSON serialization, graph data structures (TypedEdgeGraph, StringEdge), file I/O (FileUtil), CLI handling, statistics (CentralTendency), collection utilities (EnhancedHashSet, EnhancedTreeSet), and matrix operations. |
| **MetricsComputation** | 23 | Computes architectural quality metrics: decay metrics (BasicMQ, TurboMQ, ArchitecturalStability), evolution metrics (A2a, Cvg, MoJoEvolutionAnalyzer), and cluster-level metrics (IntraConnectivity, InterConnectivity). |
| **Visualization** | 15 | Swing-based GUI for visualizing architectures, clusters, feature vectors, and topic distributions. Includes MVC components (ClustererController, ArchitectureViewer, FeatureVectorViewer). |
| **IssueCommitIntegration** | 13 | Integrates with issue tracking systems (JIRA XML, GitLab REST API) to correlate commits, issues, and code changes. Handles issue records, comments, and commit data. |
| **AntipatternDetection** | 11 | Detects 11 architectural smells across 4 categories: concern-based (ConcernOverload, ScatteredParasiticFunctionality), dependency-based (DependencyCycle, LinkOverload), coupling-based (CodeMaatHelper), and interface-based (DependencyFinderProcessing). |
| **DesignDecisionTracking** | 10 | RecovAr engine: tracks architectural design decisions by correlating cluster changes, code element changes, and smell evolution across versions. Generates version trees and decision rankings. |
| **DependencyExtraction** | 8 | Extracts dependencies from multiple sources: Java bytecode (Classycle), C source code, SciTools Understand CSV, ODEM format, Makefile dependencies. Converts to RSF (Recoverable Software Format). |
| **TopicModeling** | 8 | Wraps Mallet for LDA topic modeling on source code. Manages topic distributions per code element (DocTopics), concern identification, and topic composition parsing. |
| **ChangeEvolutionAnalysis** | 6 | Analyzes software changes across versions: dependency graph evolution, version mapping, version tree construction, and change/decision tracking. |

### Architectural Rationale (from Claude)

> This system implements a layered architecture for software architecture recovery and analysis. The core workflow involves: (1) extracting dependencies from source code, (2) clustering classes into architectural components using similarity measures and topic models, (3) detecting architectural problems, (4) computing quality metrics, (5) tracking evolution and design decisions over time, (6) correlating with development artifacts, and (7) presenting results through a GUI. All components rely on shared CoreInfrastructure for common utilities. The architecture follows separation of concerns with distinct components for analysis (clustering, metrics, smells), data extraction (dependencies, issues), evolution tracking (changes, decisions), and presentation (visualization).

---

## Detected Architectural Smells

### Smell 1: Dependency Cycle (HIGH)

**What:** Circular dependency among 6 of 10 components:

```
ChangeEvolutionAnalysis ↔ ClusteringEngine ↔ CoreInfrastructure ↔ DependencyExtraction ↔ MetricsComputation ↔ TopicModeling
```

**Component-level dependency edges forming the cycle:**

| From | To |
|------|----|
| ClusteringEngine | ChangeEvolutionAnalysis |
| ChangeEvolutionAnalysis | ClusteringEngine |
| ClusteringEngine | MetricsComputation |
| MetricsComputation | ClusteringEngine |
| ClusteringEngine | TopicModeling |
| TopicModeling | ClusteringEngine |
| ClusteringEngine | CoreInfrastructure |
| CoreInfrastructure | ClusteringEngine |
| DependencyExtraction | ChangeEvolutionAnalysis |
| ChangeEvolutionAnalysis | DependencyExtraction |

**Why it matters:** 6 out of 10 components are locked in a dependency cycle. You cannot change, test, or deploy any of these components independently. This hinders maintainability, increases build complexity, and makes the system harder to reason about. The cycle means that a change in the metrics module could ripple through clustering, topic modeling, evolution analysis, and back.

**Suggested fix:** Break the cycle by introducing interfaces/abstractions at key boundaries. Specifically:
- CoreInfrastructure should not depend on ClusteringEngine — if it does, those utility classes likely belong in a different component
- MetricsComputation should depend on ClusteringEngine's output (Architecture data structures) via an interface, not on the engine itself
- TopicModeling should provide data to ClusteringEngine without depending back on it

### Smell 2: Concern Overload (HIGH)

**What:** CoreInfrastructure (24 classes) is a utility dumping ground mixing unrelated concerns:
- JSON serialization (`EnhancedJsonGenerator`, `EnhancedJsonParser`, `JsonSerializable`)
- Graph data structures (`StringEdge`, `TypedEdgeGraph`, `LabeledEdge`)
- File I/O (`FileUtil`, `DirCleaner`, `Version`)
- CLI handling (`CLI`, `Terminal`)
- Statistics (`CentralTendency`, `C2C2CSV`)
- Collection utilities (`EnhancedHashSet`, `EnhancedSet`, `EnhancedTreeSet`, `MapUtil`)
- Matrix operations (`SparseMatrix`, etc.)

**Why it matters:** This component violates the Single Responsibility Principle. Changes to JSON serialization logic could inadvertently affect graph utilities. It becomes a growing catchall where any new utility gets dumped. Developers cannot understand the component's purpose at a glance, and testing becomes complex due to diverse dependencies.

**Suggested refactoring:** Split CoreInfrastructure into 6 focused components:
1. **GraphDataStructures** — `StringEdge`, `TypedEdgeGraph`, `LabeledEdge`
2. **JsonSerialization** — `EnhancedJsonGenerator`, `EnhancedJsonParser`, `JsonSerializable`
3. **FileUtilities** — `FileUtil`, `DirCleaner`, `Version`
4. **CLIFramework** — `CLI`, `Terminal`
5. **MathStatistics** — `CentralTendency`, statistic package classes
6. **CollectionUtilities** — `EnhancedHashSet`, `EnhancedSet`, `EnhancedTreeSet`, `MapUtil`

---

## Observations: ARCADE Analyzing Itself

This self-analysis reveals an ironic finding that the ARCADE paper itself acknowledges: **ARCADE's own architecture has undergone design decay.** The paper states:

> "ARCADE's own architecture has undergone design decay due to changes by multiple developers, necessitating major refactoring."

Our AI-powered analysis confirms this with concrete evidence:

1. **60% of components are in a dependency cycle** — the very smell ARCADE is designed to detect in other systems. The cycle involves the core pipeline components (clustering, metrics, topic modeling, dependencies, evolution analysis, and utilities).

2. **The utility component is a concern-overloaded catchall** — mixing JSON, graphs, files, CLI, statistics, and collections into one component. This is the "Functionality Overload" smell from ARCADE's own taxonomy.

3. **The largest component (ClusteringEngine, 44 classes) participates in the most dependency edges** — it depends on and is depended upon by nearly every other component, making it a hub of coupling.

### Comparison: What Original ARCADE Might Find vs. ARCADE-Next

| Aspect | Original ARCADE | ARCADE-Next |
|--------|----------------|-------------|
| **Setup time** | Hours (install SciTools Understand, configure dirs, tune Mallet params) | 0 — just point at source dir |
| **Recovery method** | LDA topic modeling (50 topics, bag-of-words) → agglomerative clustering | Claude CLI (semantic understanding of code structure and naming) |
| **Component naming** | Auto-generated cluster IDs (Cluster_0, Cluster_1, ...) | Semantically meaningful names (ClusteringEngine, AntipatternDetection, ...) |
| **Smell output** | JSON with component IDs and smell types | Plain English: what it is, why it matters, how to fix it |
| **Actionability** | Requires expert interpretation | Directly actionable refactoring suggestions |
| **Cost** | SciTools Understand license ($$) | Free (tree-sitter + local Claude CLI) |

---

## Raw Data: Component Dependencies

The full component-level dependency matrix (extracted from 465 class-level edges):

| From → To | Clust | Anti | DepEx | Change | Design | Issue | Metric | Topic | Vis | Core |
|-----------|-------|------|-------|--------|--------|-------|--------|-------|-----|------|
| **ClusteringEngine** | - | | | x | | | x | x | | x |
| **AntipatternDetection** | x | - | | | | | | x | | x |
| **DependencyExtraction** | x | | - | x | | | | | | x |
| **ChangeEvolutionAnalysis** | x | | x | - | | | | | | x |
| **DesignDecisionTracking** | x | x | | x | - | x | | | | x |
| **IssueCommitIntegration** | | | | x | | - | | | | x |
| **MetricsComputation** | x | | | | | | - | | | x |
| **TopicModeling** | x | | | | | | | - | | x |
| **Visualization** | x | | | | | | | x | - | x |
| **CoreInfrastructure** | x | | | | | | | | | - |

**Key observations from the matrix:**
- CoreInfrastructure is depended upon by all 9 other components (expected for a utility layer)
- But CoreInfrastructure also depends back on ClusteringEngine — creating the cycle
- ClusteringEngine is the most connected component: 4 incoming + 4 outgoing edges
- DesignDecisionTracking has the most outgoing dependencies (6) — it touches almost every other component
- Only Visualization has no incoming dependencies from other components (pure consumer)

---

*Generated by ARCADE-Next — analyzing ARCADE with AI-powered architecture recovery.*
