# Graph Isomorphism Project — Complete Reference Guide

> **Purpose**: A self-contained, human-readable reference so you can understand every piece of this codebase even years from now. Every algorithm is explained, linked to the study material where it comes from, and mapped to the exact functions in the code.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The Two Problems We Solve](#2-the-two-problems-we-solve)
3. [Architecture & Pipeline](#3-architecture--pipeline)
4. [Module-by-Module Guide](#4-module-by-module-guide)
   - 4.1 [graph.py — Graph Data Structure](#41-graphpy--graph-data-structure)
   - 4.2 [graph_io.py — File I/O](#42-graph_iopy--file-io)
   - 4.3 [colorref.py — Basic Colour Refinement](#43-colorrefpy--basic-colour-refinement)
   - 4.4 [fast_colorref.py — Fast Colour Refinement (Hopcroft)](#44-fast_colorrefpy--fast-colour-refinement-hopcroft)
   - 4.5 [branching.py — Individualization-Refinement & #Aut](#45-branchingpy--individualization-refinement--aut)
   - 4.6 [permutation.py — Permutation Group Algebra](#46-permutationpy--permutation-group-algebra)
   - 4.7 [preprocessing.py — Trees, Twins, Components](#47-preprocessingpy--trees-twins-components)
5. [Algorithm Deep-Dives](#5-algorithm-deep-dives)
   - 5.1 [Basic Colour Refinement](#51-basic-colour-refinement)
   - 5.2 [Fast Colour Refinement (Hopcroft-style)](#52-fast-colour-refinement-hopcroft-style)
   - 5.3 [Branching / Individualization-Refinement for GI](#53-branching--individualization-refinement-for-gi)
   - 5.4 [Generating Sets & Pruning for #Aut](#54-generating-sets--pruning-for-aut)
   - 5.5 [Orbit-Stabiliser & Group Order](#55-orbit-stabiliser--group-order)
   - 5.6 [AHU Tree Isomorphism](#56-ahu-tree-isomorphism)
   - 5.7 [Twin Detection & Reduction](#57-twin-detection--reduction)
6. [Study Material Cross-Reference](#6-study-material-cross-reference)
7. [Key Data Structures](#7-key-data-structures)
8. [How to Run](#8-how-to-run)
9. [Glossary](#9-glossary)

---

## 1. Project Overview

This project implements a solver for two problems on simple, undirected, finite graphs:

- **Graph Isomorphism (GI)**: Given graphs G and H, are they "the same" up to vertex relabelling?
- **Automorphism Counting (#Aut)**: Given graph G, how many symmetries (self-isomorphisms) does it have?

The solver combines multiple algorithms into a pipeline that handles everything from trivially small graphs to graphs with 10^33+ automorphisms.

**No external dependencies.** Only Python 3.10+ standard library.

---

## 2. The Two Problems We Solve

### Graph Isomorphism (GI)

> **Reader**: Chapter 1, Definition 1.4-1.5  
> **Lecture 1**: Slides 3-4  

An **isomorphism** between graphs G and H is a bijection f : V(G) -> V(H) such that {u,v} is an edge in G if and only if {f(u), f(v)} is an edge in H. Two graphs are **isomorphic** if such a bijection exists.

**In plain English**: Can you relabel the vertices of G to get exactly H? If yes, they're isomorphic.

**What our code does**: Given a `.grl` file containing multiple graphs, partition them into equivalence classes of mutually isomorphic graphs.

### Automorphism Counting (#Aut)

> **Reader**: Chapter 1, Definition 1.6-1.7  
> **Lecture 1**: Slide 6 (kick-off); **Lecture 4**: Slide 2-3  

An **automorphism** of G is an isomorphism from G to itself — a permutation of vertices that preserves all edges. The set of all automorphisms forms a **group** under composition, called Aut(G).

**In plain English**: How many ways can you shuffle the vertices of G and still have the same graph? That count is |Aut(G)|.

**Example**: A cycle C_6 has 12 automorphisms (6 rotations x 2 reflections). A path P_3 has 2 (identity + flip).

**What our code does**: Given a graph (`.gr`) or list of graphs (`.grl`), compute |Aut(G)| for each.

---

## 3. Architecture & Pipeline

> **Reader**: Chapter 1, Figure 1.2 (page 4)  
> **Lecture 2**: Slide 3 (overview flowchart)  
> **Lecture 3**: Slide 2 (same flowchart)

```
Input: .grl or .gr file
        |
        v
  [Preprocessing]  -- Is it a tree/forest? Solve in O(n) via AHU
        |                (preprocessing.py)
        | (if not a tree)
        v
  [Disconnected?]  -- Decompose into components, solve each independently
        |               multiply by k! for groups of k isomorphic components
        | (if connected)
        v
  [Twin Reduction]  -- Collapse twin groups, multiply by k! per group
        |               solve reduced graph with pre-colouring
        | (if twins found, or pass through)
        v
  [Fast Colour Refinement]  -- Compute stable colouring in O(m log n)
        |                       (fast_colorref.py)
        v
  [Check result]
     |         |          |
  Unbalanced  Bijection   Balanced but
  -> not iso  -> unique   not discrete
              isomorphism     |
                              v
                        [Branching]  -- Individualize vertices, recurse
                              |         (branching.py)
                              v
                        [For #Aut: use Generating Sets]
                              |    Build gen set X of Aut(G)
                              |    Compute |<X>| via orbit-stabiliser
                              |    (permutation.py)
                              v
                          Output
```

**Entry point**: `branching.py:solve(filename)` — detects problem type from filename and orchestrates everything.

---

## 4. Module-by-Module Guide

### 4.1 `graph.py` — Graph Data Structure

> **Study material**: "Python graph class slides" (entire presentation)  
> **Reader**: Provided as project framework

This file was **provided by the course** — we didn't write it. It defines the core data structures:

#### Classes

| Class | Purpose |
|-------|---------|
| `Vertex` | A node in a graph. Has `.label`, `.graph`, `.neighbours`, `.degree`, `.incidence` |
| `Edge` | An edge between two vertices. Has `.tail`, `.head`, `.weight`, `.other_end(v)` |
| `Graph` | Container for vertices and edges. Has `.vertices`, `.edges`, `.add_vertex()`, `.add_edge()`, `.is_adjacent()` |
| `UnsafeGraph` | Faster subclass that skips safety checks on add operations |
| `GraphError` | Exception for invalid graph operations |

#### Key design choices

- **Adjacency is stored per-vertex** via `Vertex._incidence` — a dict mapping each neighbour to the set of edges connecting them. This gives O(1) adjacency testing and O(degree) neighbour iteration.
- **Both a set and a list** of vertices are maintained (`Graph._v` set for O(1) membership, `Graph._vlist` list for ordered iteration).
- Vertices can have a `.colour` attribute dynamically added — this is how colour refinement works.

#### Important: How neighbours work

```python
# v._incidence is: {neighbour_vertex: {edge1, edge2, ...}}
# So v.neighbours returns list(v._incidence.keys())
# And v.degree counts ALL incident edges (including multi-edges)
```

---

### 4.2 `graph_io.py` — File I/O

> **Study material**: "Python graph class slides"  
> **Reader**: Provided as project framework

Also **provided by the course**. Reads/writes the `.gr` and `.grl` file formats.

#### File formats

- **`.gr`**: Single graph. First line = number of vertices. Then edge list as `tail,head` or `tail,head:weight`. Vertices are numbered 0 to n-1.
- **`.grl`**: Multiple graphs separated by `--- Next graph:` lines.

#### Key functions

| Function | Purpose |
|----------|---------|
| `load_graph(f, graph_class, read_list)` | Main entry. `read_list=True` returns `List[Graph]`, `False` returns single `Graph` |
| `save_graph(graph_list, f)` | Write graph(s) to file |
| `write_dot(graph, f, ...)` | Export to Graphviz .dot format for visualization |
| `write_graphml(graph, f, ...)` | Export to .graphML format (for Gephi) |

---

### 4.3 `colorref.py` — Basic Colour Refinement

> **Reader**: Chapter 2 (entire chapter), Algorithm 1 (page 16)  
> **Lecture 1**: Slides 7-16 (colour refinement definition, examples, pseudocode)  

This implements the **naive O(n^2 m)** version of colour refinement. It's the conceptually simplest version — useful for understanding, but too slow for large graphs. The fast version in `fast_colorref.py` replaces it in practice.

#### What colour refinement does (the big picture)

1. Start: every vertex gets the same colour (colour 1).
2. Each round: vertices with the same colour but **different-coloured neighbourhoods** get split into different colours.
3. Repeat until no more splits happen — the colouring is now **stable**.
4. Check: if two graphs have different colour distributions, they're **not isomorphic**. If every colour appears exactly once in both graphs (discrete + balanced), they **are** isomorphic.

#### Functions

| Function | What it does | Lines |
|----------|-------------|-------|
| `set_default_colouring(graph, mode)` | Sets `v.colour` for all vertices. "uniform" = all get 1, "degree" = colour by degree | 23-32 |
| `partition_vertices(vertices)` | Groups vertices by signature `(own_colour, sorted_neighbour_colours)` | 39-57 |
| `get_sorted_partition(vertices)` | Returns partition cells sorted by signature (deterministic ordering) | 60-73 |
| `assign_colours_from_partition(partition)` | Gives each cell a new integer colour 0, 1, 2, ... | 80-92 |
| `basic_colorref(filename)` | **Main API**: runs full refinement on a .grl file, returns equivalence classes | 98-173 |

#### How `basic_colorref` works step by step

```
1. Load all graphs from file
2. Give every vertex colour = 1
3. Pool ALL vertices from ALL graphs into one list (disjoint union)
4. Loop:
   a. Compute signature for each vertex: (its_colour, sorted list of neighbour colours)
   b. Group vertices by signature
   c. If number of groups == last time → STABLE, stop
   d. Else: assign new colour = group index, repeat
5. Group graphs by their colour distribution (sorted multiset of vertex colours)
6. Graphs with identical distributions are "possibly isomorphic"
```

**Why disjoint union?** By refining all graphs in one global colour space, isomorphic graphs automatically get the same colours. If two graphs end up with different colour distributions, colour refinement has *proven* they're non-isomorphic.

#### Complexity

- Each iteration: O(n * (n + m)) to compute all signatures (each vertex looks at all its neighbours)
- Number of iterations: at most n (each iteration creates at least one new colour)
- **Total: O(n^2 * (n + m)) = O(n^2 m)** for sparse graphs

---

### 4.4 `fast_colorref.py` — Fast Colour Refinement (Hopcroft)

> **Reader**: Chapter 4 (entire chapter), especially Section 4.3 "Faster Minimisation Algorithm"  
> **Lecture 3**: Slides 1-18 (DFA minimisation → fast partition refinement)  

This is the **O(m log n)** version based on Hopcroft's 1971 DFA minimisation algorithm, adapted for graph colour refinement. It's the workhorse of the solver — called on every refinement step, including inside branching recursion.

#### The key insight (why it's faster)

**Basic version**: Each round, recompute the signature of EVERY vertex. Cost: O(n * m) per round, O(n) rounds = O(n^2 m).

**Fast version**: Instead of recomputing everything, maintain a **work queue** of colour classes that might cause splits. When class C is processed, only vertices with neighbours IN C need updating. The "add smaller half to queue" trick (Lemma 4.9) ensures each vertex enters the queue O(log n) times total.

> **Lecture 3 Lemma (Refine operation)**: Let C be a colour class. For each other class D, let A = {vertices in D with a neighbour in C}. If A is non-empty and A ≠ D, split D into A and D\A. This maintains the refinement invariant.

#### Classes

**`Partition`** (lines 21-47): The core data structure.
- `classes`: dict mapping colour (int) → set of vertices
- `vertex_colour`: dict mapping vertex → its current colour
- `_next_colour`: counter for fresh colour IDs
- `add_class(members)`: creates a new colour class, returns its ID

#### Functions

| Function | What it does | Lines |
|----------|-------------|-------|
| `_build_neighbour_index(vertices)` | Pre-computes `{v: v.neighbours}` dict for fast lookup | 53-55 |
| `fast_colour_refine(vertices, adj, initial_colouring)` | **Core algorithm**: returns stable `Partition` | 62-208 |
| `colour_refine_graphs(graphs, initial_colouring)` | Convenience wrapper: refine a list of graphs | 215-223 |
| `get_colour_signature(graph, partition)` | Canonical signature: sorted `(colour, count)` pairs | 226-233 |
| `is_balanced(graphs, partition)` | Do all graphs have the same colour distribution? | 236-244 |
| `is_discrete_for_graph(graph, partition)` | Does every vertex have a unique colour? | 247-254 |
| `defines_bijection(graph_a, graph_b, partition)` | Is the partition discrete for both graphs? | 257-261 |
| `basic_colorref_fast(filename)` | Drop-in replacement for `basic_colorref` using fast algorithm | 264-287 |

#### How `fast_colour_refine` works (the main loop, lines 98-207)

```
Initialize:
  - Build initial partition from initial_colouring
  - Add ALL colour classes to the work queue

While queue not empty:
  1. Pop colour class C from queue (the "refining class")
  
  2. Count neighbours in C:
     For each vertex u in C, for each neighbour w of u:
       neighbour_count[w] += 1
     
  3. Group affected vertices by their current colour class D
  
  4. For each affected class D:
     - Sub-group vertices in D by their neighbour_count value
     - Also consider vertices in D with count=0 (no neighbours in C)
     - If all vertices agree (only one sub-group) → no split, skip
     - Otherwise: SPLIT
       - The LARGEST fragment keeps D's colour
       - Each smaller fragment gets a new colour
       - Add non-largest fragments to queue (Lemma 4.9 trick)
```

#### The "add smaller to queue" trick (Lemma 4.9)

> **Reader**: Lemma 4.9, page 47  

When D splits into fragments, we only add the **non-largest** fragment(s) to the queue. Why? The largest fragment staying means we've already refined with respect to the "bulk" of D. We only need to check the new, smaller parts.

This is the key to O(m log n): each vertex can be in the "smaller half" at most O(log n) times before its class has size 1.

#### Performance optimizations in the code

The inner loop (lines 98-207) is heavily optimized:
- **Local aliases** (`p_classes`, `p_vc`, `p_nc`) avoid repeated attribute lookups
- **Inline dict operations** instead of `defaultdict` to reduce overhead
- **`p_nc` is a list `[int]`** instead of a plain int — this is a Python trick to allow mutation inside nested functions/closures

---

### 4.5 `branching.py` — Individualization-Refinement & #Aut

> **Reader**: Chapter 3 (branching), Chapter 5 (automorphism groups)  
> **Lecture 2**: Slides 5-18 (branching for GI)  
> **Lecture 4**: Slides 10-16 (generating sets for automorphisms)  

This is the main solver module. It handles the case when colour refinement alone can't decide isomorphism (balanced but not discrete colouring).

#### The branching idea

> **Lecture 2, Slide 10**: "Individualisation Refinement Overview"

When colour refinement gives a balanced colouring that isn't discrete, there are colour classes with 2+ vertices in each graph. We pick a vertex x from G in such a class, try mapping it to each possible vertex y in H's matching class, and recurse. Each choice is a "branch".

**Encoding the choice**: Give x and y a unique new colour, then re-run colour refinement. This propagates the constraint "x maps to y" through the graph structure.

#### `_copy_graph` (line 44)

Creates an independent copy of a graph with fresh `Vertex` and `Edge` objects. Returns `(copy, vertex_map)` where `vertex_map` maps each original vertex to its counterpart in the copy. Used by `_count_aut_core` to build the pair (G, H=copy of G) needed for automorphism detection — comparing a graph to its own copy finds self-isomorphisms.

#### Partition helpers: `is_balanced_pair`, `is_discrete_pair`, `_extract_bijection` (lines 115-193)

These are **optimized two-graph versions** of the general partition checks in `fast_colorref.py`:

| Function | Lines | Purpose |
|----------|-------|---------|
| `is_balanced_pair(verts_g, verts_h, partition)` | 115-128 | Checks if two graphs have identical colour distributions. Faster than the general `is_balanced` — uses a single counter dict instead of comparing signatures. |
| `is_discrete_pair(verts_g, verts_h, partition)` | 131-145 | Checks if every vertex in G has a unique colour (since the partition is balanced, H is discrete too). Avoids set allocation overhead of the general version. |
| `_extract_bijection(verts_g, verts_h, partition)` | 186-193 | When the partition is discrete and balanced, extracts the unique vertex mapping f: V(G) → V(H) by matching vertices that share the same colour. Used by `_count_aut_core` to convert a discrete partition into a `Permutation` object. |

These are called from `_BranchingContext.refine_and_check` on every recursive call, so their performance matters.

#### Key helper: `_BranchingContext` (lines 72-112)

This class pre-computes and caches data shared across all recursive calls for a pair of graphs G and H:
- `adj`: pre-computed adjacency lists
- `verts_g`, `verts_h`: vertex lists for G and H
- `base_colouring`: shared dict, modified in-place for each branch then restored (avoids allocation)
- `refine_and_check(D, I)`: the core operation — set up colouring from (D,I) sequences, run fast refinement, classify result as unbalanced (0), bijection (1), or needs-more-branching (2)

#### `_choose_branching_class` (lines 148-183)

> **Reader**: Section 3.5 "Improvements" (page 36)

Picks the **smallest** non-trivial colour class (size ≥ 2 in both graphs) to branch on. This minimizes the branching factor at each level.

**Why smallest?** If a class has k vertices, branching on it creates k recursive calls. Choosing the smallest class minimizes k, reducing the search tree.

#### `count_isomorphisms` (lines 200-234) — Algorithm 2

> **Reader**: Chapter 3, Algorithm 2 "CountIsomorphism" (page 28)  
> **Lecture 2**: Slides 10-18  

```
CountIso(G, H, D, I):
  1. Run colour refinement with α(D,I) colouring
  2. If unbalanced → return 0 (no isomorphism possible)
  3. If defines bijection → return 1 (exactly one isomorphism)
  4. Choose smallest non-trivial class C_G, C_H
  5. Fix x = C_G[0]
  6. For each y in C_H:
       count += CountIso(G, H, D+[x], I+[y])
  7. Return count
```

The `gi_only=True` parameter short-circuits after finding the first isomorphism (returns 1 instead of counting all).

#### `count_automorphisms` — Entry point for #Aut

> **Reader**: Chapter 5, Section 5.4 "Pruning the Branching Tree"  
> **Lecture 4**: Slides 10-16  

This orchestrates the full #Aut pipeline:
1. **Forest fast-path**: If the graph is a forest, solve in O(n) via AHU (`_forest_automorphisms`).
2. **Component decomposition**: If disconnected (non-forest), decompose into connected components via `_disconnected_automorphisms`. Each component is solved independently; isomorphic components contribute an additional k! factor.
3. **Twin reduction**: For connected non-forest graphs, call `reduce_twins` to iteratively collapse twin groups, accumulate the k! factors, and pass the reduced graph (with pre-colouring) to `_count_aut_core`. Skipped if no twins are found.
4. **General case**: Call `_count_aut_core` which builds a generating set.

#### `_disconnected_automorphisms` — Component decomposition for #Aut

Builds subgraphs for each connected component via `_component_graph`, solves each independently (dispatching to AHU for trees, generating sets for general graphs), groups isomorphic components (using vertex/edge count checks + exact branching), and multiplies by k! for each group of k isomorphic components.

#### `_are_isomorphic` — Quick isomorphism check

Decides whether two graphs are isomorphic with early exits for different vertex counts and edge counts before running the expensive branching algorithm.

#### `_count_aut_core` (lines 383-479) — Algorithm 9 with Lemma 5.11 pruning

> **Reader**: Chapter 5, Algorithm 9 "UpdateGeneratingSet" (page 63)  
> **Lecture 4**: Slides 13-14 "Basic Algorithmic Idea"  

This is the most sophisticated part of the codebase. Instead of enumerating all automorphisms (which can be 10^33+), it finds a small **generating set** X such that ⟨X⟩ = Aut(G), then computes |⟨X⟩| algebraically.

**How it works**:
1. Create a copy H of graph G.
2. Compare G to H using branching (like GI, but G=H means we're finding self-isomorphisms).
3. Build generating set X:

```
_update(D, I):                    [Algorithm 9]
  Refine with α(D,I)
  If unbalanced → return
  If bijection → extract permutation σ, if σ ≠ id add to X, return
  Choose branching class C_G, C_H; let x = C_G[0], x' = copy of x in H
  
  TRIVIAL BRANCH: D+[x], I+[x']
    Call _update recursively  ← finds ALL automorphisms fixing x → x'
                                 (the stabiliser of x)
  
  NON-TRIVIAL BRANCHES: for each y ≠ x' in C_H:
    D+[x], I+[y]
    Call _find_one            ← find just ONE automorphism mapping x → y
                                 then STOP (Lemma 5.11 pruning!)
```

**Lemma 5.11 pruning** (the key optimization):

> **Reader**: Lemma 5.11, page 63  
> **Lecture 4**: Slide 15 "Correctness"

After exploring the trivial branch (x → x'), we have all generators for Stab_x (automorphisms that fix x). For each non-trivial branch (x → y), we only need **one** automorphism σ with σ(x) = y. Combined with the stabiliser generators, this single σ generates ALL automorphisms mapping x to y (because any other such automorphism τ satisfies τσ⁻¹ ∈ Stab_x).

**This is why bigtrees3 (2.8 × 10^33 automorphisms) solves in milliseconds**: we find O(n) generators instead of enumerating 10^33 permutations.

4. After `_update` completes, compute |⟨X⟩| via `group_order()` from `permutation.py`.

#### `_tree_equivalence_classes` (line 486) — Tree GI fast-path

When all input graphs are trees, this function bypasses branching entirely. It computes the AHU canonical label for each tree and groups graphs with identical labels — two trees are isomorphic if and only if their canonical labels match. Runs in O(n) per tree.

#### `find_equivalence_classes` (lines 508-551) — GI with fast-path

> **Not directly from any single reader algorithm** — this is our own optimization.

For the GI problem with multiple graphs:
1. **Fast-path**: Run colour refinement on ALL graphs at once. Group by colour signature. Graphs with different signatures are definitely non-isomorphic — no branching needed.
2. **Branching only within groups**: For groups of graphs with the same colour signature, pairwise test isomorphism via `count_isomorphisms(..., gi_only=True)`.

This avoids branching on most graph pairs.

#### `solve` — Main entry point

Detects problem type from filename:
- `*GI.grl` → equivalence classes only
- `*Aut.grl` or `*.gr` → automorphism counts only
- `*GIAut.grl` → both

Also detects if all graphs are trees (for AHU fast-path).

---

### 4.6 `permutation.py` — Permutation Group Algebra

> **Reader**: Chapter 5, Sections 5.1-5.5  
> **Lecture 4**: Slides 3-9 (permutations, groups, generating sets)  

This module provides the algebraic machinery to compute |Aut(G)| from a generating set without enumerating all group elements.

#### `Permutation` class (lines 25-93)

> **Reader**: Section 5.1, Definition 5.1-5.3  
> **Lecture 4**: Slides 4-5  

A permutation σ on a finite set, stored as a dictionary mapping only **non-fixed points** (elements that actually move). The identity permutation is an empty dict.

**Convention**: Composition follows the reader: `(p * q)(x) = p(q(x))` — apply q first, then p.

| Method | What it does |
|--------|-------------|
| `__call__(x)` | Apply permutation: return σ(x) |
| `__mul__(other)` | Compose: (self * other)(x) = self(other(x)) |
| `inverse()` | Return σ⁻¹ |
| `is_identity()` | True if no element moves |
| `support` | Set of elements moved by this permutation |

#### `orbit_and_transversal` (lines 102-124) — Algorithm 10

> **Reader**: Section 5.5.4, Algorithm 10 (page 70)  
> **Lecture 4**: (implicit in the orbit-stabiliser discussion)

Given generators X and an element α, compute:
- **Orbit**: all elements reachable from α by applying generators: Δ = {g₁g₂...gₖ(α) : gᵢ ∈ X}
- **Transversal**: for each β in the orbit, a specific permutation that maps α → β

Uses BFS: start from α, repeatedly apply each generator, discover new orbit elements.

```
orbit = {α}, transversal = {α: identity}
queue = [α]
while queue:
  β = queue.pop()
  for each generator g:
    γ = g(β)
    if γ not seen:
      orbit.add(γ)
      transversal[γ] = g ∘ transversal[β]  // composition that maps α → γ
      queue.append(γ)
```

#### `group_order` (lines 207-234) — Proposition 5.18

> **Reader**: Proposition 5.18 (page 68), Theorem 5.19 (Schreier-Sims)  
> **Lecture 4**: (orbit-stabiliser theorem discussion)

Computes |⟨generators⟩| using a **stabiliser chain**.

**Orbit-Stabiliser Theorem**: |G| = |orbit of α| × |stabiliser of α|

Applied recursively:
```
|G| = |Δ₁| × |G^(1)|
    = |Δ₁| × |Δ₂| × |G^(2)|
    = |Δ₁| × |Δ₂| × ... × |Δₖ|
```
where Δᵢ is the orbit of base point βᵢ under G^(i-1), and G^(i) = Stab(β₁,...,βᵢ).

**Stabiliser generators** are computed via **Schreier's Lemma**: for each orbit element β and generator g, the Schreier generator is u(g(β))⁻¹ ∘ g ∘ u(β), where u is the transversal.

#### `_StabiliserLevel` (line 131) — Chain data structure

Internal data class representing one level of a stabiliser chain. Stores:
- `alpha`: the base point for this level
- `orbit`: set of elements reachable from `alpha` under the level's generators
- `transversal`: dict mapping each orbit element to a permutation that sends `alpha` to it
- `generators`: the generating set for the stabiliser at this level

Used by `_build_chain` and `group_order` to walk the chain.

#### `_build_chain` (lines 147-183) — Schreier-Sims

> **Reader**: Section 5.5, Theorem 5.19  

Builds the stabiliser chain: at each level, computes orbit + transversal, then derives Schreier generators for the next level's stabiliser.

#### `_choose_base` (lines 186-204) — Base selection

Selects a sequence of base points for the stabiliser chain. Picks elements from the vertex list that are actually moved by the generators (i.e., in some generator's support). A good base keeps the chain short — only elements that the group acts non-trivially on are chosen.

#### `is_member` (lines 241-273) — Proposition 5.20 (Sifting)

> **Reader**: Proposition 5.20 (page 71)

Tests if a permutation belongs to ⟨generators⟩ by "sifting" it through the stabiliser chain. At each level, check if σ(αᵢ) is in the orbit; if so, adjust σ by the transversal element and continue to the next level.

---

### 4.7 `preprocessing.py` — Trees, Twins, Components

> **Reader**: Chapter 6 "Graph Structures and Preprocessing"  
> **Lecture 4**: (briefly mentioned; mostly reader material)

This module handles special graph structures that can be solved faster than the general case.

#### Connected Components (lines 25-60)

> **Reader**: Section 6.4 "Components" (page 79)  

`find_components(graph)`: Standard BFS component discovery. Returns list of vertex lists.

`is_connected(graph)`: True if exactly one component.

In `branching.py`, disconnected graphs are automatically decomposed into components for #Aut computation. Each component is solved independently (AHU for trees, generating sets for general graphs), and isomorphic components contribute a k! permutation factor. This is handled by `_disconnected_automorphisms` and `_component_graph`.

#### Tree/Forest Detection (lines 67-85)

> **Reader**: Section 6.2 "Trees" (page 76)  

- `is_tree(graph)`: Connected AND |E| = |V| - 1
- `is_forest(graph)`: |E| = |V| - |components|  (each component is a tree)

#### AHU Algorithm for Trees (lines 88-210)

> **Reader**: Section 6.2 "Trees" (page 76-78)  
> This is based on the AHU (Aho, Hopcroft, Ullman) tree isomorphism algorithm.

**Problem**: Given two unrooted trees, are they isomorphic? And how many automorphisms does a tree have?

**Key idea**: Compute a **canonical label** for each tree. Two trees are isomorphic iff their labels match. The label is a recursively-defined nested tuple.

##### `_find_center(vertices)` (lines 88-115)

Find the **center** of a tree: iteratively peel off leaves until 1 or 2 vertices remain.

```
remaining = all vertices
while |remaining| > 2:
  leaves = vertices with degree ≤ 1 in remaining
  remove all leaves from remaining
  update degrees of their neighbours
return remaining (1 or 2 center vertices)
```

The center is unique and invariant under isomorphism, so it gives a canonical root.

##### `ahu_label(root, parent, vertex_set)` (lines 118-137)

Compute the canonical label for a **rooted** subtree:
```
label(v) = sorted_tuple(label(child₁), label(child₂), ...)
label(leaf) = ()
```

Two rooted trees have the same label iff they're isomorphic.

##### `tree_canonical_label(vertices)` (lines 140-161)

For an **unrooted** tree:
1. Find center (1 or 2 vertices)
2. If 1 center: root there, compute label
3. If 2 centers: root at each, take lexicographic minimum of the two labels

##### `tree_automorphisms(vertices)` (lines 164-211)

Count |Aut(T)| using the tree structure:

For a rooted tree:
```
|Aut(T)| = product over all vertices v of:
  (number of children with identical subtree labels)! × product of children's |Aut|
```

**Intuition**: If vertex v has 3 children with identical subtrees, those 3 children can be permuted (3! = 6 ways). This multiplies through the whole tree.

For unrooted tree with 2 centers: if the two halves are isomorphic, multiply by 2 (you can swap them).

For forests: compute per-component, then multiply by k! for each group of k isomorphic components.

#### Twin Detection (lines 218-241)

> **Reader**: Section 6.3 "Twins" (page 78)  

**True twins**: Vertices u,v are true twins if they're adjacent AND N(u)\{v} = N(v)\{u}. Equivalently: N(u) ∪ {u} = N(v) ∪ {v}.

**False twins**: Vertices u,v are false twins if N(u) = N(v) (identical neighbourhoods, not adjacent to each other).

`find_twin_groups(graph)`: Hash each vertex's neighbourhood signature. Vertices with the same signature are twins. O(n + m) time.

#### Twin Reduction (lines 248-368)

> **Reader**: Section 6.3 "Twins" (page 78)  

`reduce_twins(graph)`: Iteratively collapse twin groups:
1. Detect all twin groups (both true and false)
2. For each group of k twins: keep 1 representative, remove k-1 others, multiply aut_factor by k!
3. Repeat until no more twins found (new twins may appear after collapsing)
4. Return (reduced_graph, aut_factor, initial_colouring)

**Integration**: `reduce_twins` is called from `count_automorphisms` in `branching.py` for connected non-forest graphs. If twins are found (reduced graph is smaller), the reduced graph with its pre-colouring is passed to `_count_aut_core`, and the result is multiplied by the accumulated k! factor. If no twins are found, the reduction is skipped and the original graph is used directly.

---

## 5. Algorithm Deep-Dives

### 5.1 Basic Colour Refinement

> **Reader**: Chapter 2, Algorithm 1 (page 16)  
> **Lecture 1**: Slides 7-16  

**File**: `colorref.py`  
**Complexity**: O(n^2 m)  
**What it solves**: Computes a stable colouring that any isomorphism must preserve.

#### The invariant

> **Lecture 1, Slide 9**: "Every isomorphism f from G to H is colour preserving."

At every step, the colouring satisfies: if f is an isomorphism, then α(v) = α(f(v)) for all v. This means isomorphisms can only map vertices to same-coloured vertices in the other graph.

#### Stable colouring outcomes

> **Lecture 1, Slides 17-18**: Nomenclature  

Three possible outcomes after reaching stability:
1. **Unbalanced**: some colour has different count in G vs H → **not isomorphic** (certain)
2. **Discrete & balanced**: every vertex has unique colour, same in both graphs → **isomorphic** with the unique bijection matching colours
3. **Balanced but not discrete**: some colours have 2+ vertices → **inconclusive**, need branching

---

### 5.2 Fast Colour Refinement (Hopcroft-style)

> **Reader**: Chapter 4 (entire chapter)  
> **Lecture 3**: Slides 1-18  

**File**: `fast_colorref.py`  
**Complexity**: O(m log n)  

#### Connection to DFA minimisation

> **Lecture 3, Slides 3-7**: DFA equivalence and minimisation  

The algorithm originated from Hopcroft's 1971 DFA minimisation algorithm. The connection:
- DFA states ↔ graph vertices
- DFA transitions ↔ graph edges
- Equivalent DFA states ↔ same-coloured vertices

The refinement operation is the same: split a class D based on how its elements relate to a "refining" class C.

#### The Refine(C) operation for graphs

> **Reader**: Section 4.4 "Application on the GI/#Aut Problems" (page 50)  
> **Lecture 3, Slide 9**: Lemma (Operation Refine(C, x))  

For graphs, Refine(C) works as:
1. For each vertex w, count how many neighbours w has in C.
2. Vertices in the same class D that disagree on this count → split D.

This is the graph analog of "split D based on which states transition into C."

#### Why O(m log n)?

Each edge is "processed" when one of its endpoints is in the refining class C. The "add smaller half" trick ensures each vertex enters the queue at most O(log n) times. Each time a vertex is in the queue, all its edges get processed. Total edge processing: O(m log n).

---

### 5.3 Branching / Individualization-Refinement for GI

> **Reader**: Chapter 3 (entire chapter), Algorithm 2  
> **Lecture 2**: Slides 5-18  

**File**: `branching.py`, function `count_isomorphisms`  
**Complexity**: Worst case exponential, but fast in practice with colour refinement pruning  

#### The idea

> **Lecture 2, Slides 8-9**: "Better than Enumeration: Recursive Colour Refinement"

When colour refinement gives a balanced-but-not-discrete colouring:
1. Pick a vertex x in G from a non-trivial colour class
2. Try each possible image y in H (from the same colour class)
3. **Individualize**: give x and y a unique colour, re-run refinement
4. This often makes the colouring discrete (resolving ambiguity) or unbalanced (pruning the branch)
5. Recurse if still undecided

**Encoding via (D, I) sequences**: D = [x₁, x₂, ...] are vertices in G, I = [y₁, y₂, ...] are their images in H. The initial colouring α(D,I) gives each pair (xᵢ, yᵢ) a unique colour i+1, all others get colour 0.

---

### 5.4 Generating Sets & Pruning for #Aut

> **Reader**: Chapter 5, Sections 5.2-5.4, Algorithm 9  
> **Lecture 4**: Slides 8-16  

**File**: `branching.py`, function `_count_aut_core`  
**Key insight**: Don't enumerate automorphisms — find generators.

#### Why generating sets work

> **Lecture 4, Slide 8**: "Computing with Permutation Groups"

A group with 10^33 elements can have a generating set of size O(n log n). From generators, we can:
- Compute the group order (via orbit-stabiliser)
- Test membership (via sifting)
- Represent the entire group compactly

#### The pruning strategy (Lemma 5.11)

> **Reader**: Lemma 5.11, page 63  
> **Lecture 4**: Slide 15  

The branching tree for automorphisms has a special structure:
- **Trivial branch** (x → x'): explores Stab(x), the stabiliser. We need ALL generators for this subgroup.
- **Non-trivial branches** (x → y, y ≠ x'): we only need ONE automorphism from each. Combined with the stabiliser, one generator per coset suffices.

This is because Aut(G) decomposes as a union of cosets of Stab(x), and each coset is determined by a single representative.

---

### 5.5 Orbit-Stabiliser & Group Order

> **Reader**: Section 5.5, Proposition 5.18, Theorem 5.19  
> **Lecture 4**: (implicit)  

**File**: `permutation.py`

#### The orbit-stabiliser theorem

For a group G acting on set Ω, and element α:
```
|G| = |orbit(α)| × |Stab(α)|
```

Applied recursively with a **base** B = (β₁, ..., βₖ):
```
|G| = |orbit₁| × |orbit₂| × ... × |orbitₖ|
```

where orbitᵢ is computed at stabiliser level i.

#### Schreier generators

To get generators for Stab(α) from generators of G:
```
For each β in orbit(α), for each generator g:
  schreier_gen = u(g(β))⁻¹ ∘ g ∘ u(β)
```
where u is the transversal. These generate Stab(α).

---

### 5.6 AHU Tree Isomorphism

> **Reader**: Section 6.2 (pages 76-78)  
> **Not covered in lectures** — only in the reader.  

**File**: `preprocessing.py`

This is a **polynomial-time** (actually linear O(n)) algorithm for tree isomorphism. It's one of the few graph classes where GI is known to be in P.

#### Why trees are special

Trees have no cycles, so their structure is fully determined by parent-child relationships from any root. The center of a tree is a canonical choice of root, making comparison straightforward.

#### The canonical label

Recursively: a vertex's label is the **sorted tuple** of its children's labels. Leaves get the empty tuple `()`.

**Example**:
```
    a            label(a) = ((),(()))
   / \           label(b) = ()
  b   c          label(c) = (())
      |          label(d) = ()
      d
```

Two trees are isomorphic ↔ same canonical label from center.

#### Automorphism counting

The formula `|Aut(T)| = ∏_v k_v! × ∏_children |Aut(T_c)|` counts:
- For each vertex, the ways to permute children with identical subtrees (k_v! factor)
- Multiplied by the automorphisms of each child's subtree

---

### 5.7 Twin Detection & Reduction

> **Reader**: Section 6.3 (page 78)  
> **Not covered in lectures** — only in the reader.  

**File**: `preprocessing.py`

#### True twins

Vertices u, v where:
- u and v are adjacent
- Every other vertex is a neighbour of both or neither
- Formally: N(u) ∪ {u} = N(v) ∪ {v}

#### False twins

Vertices u, v where:
- u and v are NOT adjacent
- They have identical neighbourhoods: N(u) = N(v)

#### Why twins matter for #Aut

If k vertices are pairwise (false) twins, they can be arbitrarily permuted among themselves, contributing k! to |Aut(G)|. Collapsing them reduces the graph size.

#### Implementation note

The `reduce_twins` function is fully integrated into the `count_automorphisms` pipeline in `branching.py`. For connected non-forest graphs, twins are iteratively collapsed before branching. The pre-colouring encodes the twin type (true/false), group size, and elimination round, ensuring colour refinement can distinguish structurally different representatives in the reduced graph. The accumulated k! factor from all collapsed twin groups is multiplied with the automorphism count of the reduced graph.

---

## 6. Study Material Cross-Reference

### By Code Module

| Code file | Reader chapter(s) | Lecture(s) | Key algorithms/theorems |
|-----------|-------------------|------------|------------------------|
| `graph.py` | Provided framework | Python Graph Class slides | — |
| `graph_io.py` | Provided framework | Python Graph Class slides | — |
| `colorref.py` | **Ch. 2** (all sections) | **L1** slides 7-16 | Algorithm 1, Def 2.10, Obs 2.14, Def 2.15 |
| `fast_colorref.py` | **Ch. 4** (all sections) | **L3** slides 1-18 | Lemma 4.9, Hopcroft 1971 |
| `branching.py` (GI part) | **Ch. 3** (Sec 3.1-3.4) | **L2** slides 5-18 | Algorithm 2 |
| `branching.py` (#Aut part) | **Ch. 5** (Sec 5.2-5.4) | **L4** slides 10-16 | Algorithm 9, Lemma 5.11 |
| `branching.py` (trees) | **Ch. 6** (Sec 6.2) | Not in lectures | AHU algorithm |
| `permutation.py` | **Ch. 5** (Sec 5.1, 5.5) | **L4** slides 3-9 | Algorithm 10, Prop 5.18, Thm 5.19, Prop 5.20 |
| `preprocessing.py` (trees) | **Ch. 6** (Sec 6.2) | Not in lectures | AHU, center-finding |
| `preprocessing.py` (twins) | **Ch. 6** (Sec 6.3) | Not in lectures | Twin detection/reduction |
| `preprocessing.py` (components) | **Ch. 6** (Sec 6.4) | Not in lectures | BFS components |

### By Reader Chapter

| Chapter | Topic | Code location |
|---------|-------|---------------|
| Ch. 1 | Definitions (GI, #Aut, isomorphism, automorphism) | Conceptual — no direct code |
| Ch. 2 | Colour Refinement | `colorref.py` (all functions) |
| Ch. 3 | Branching | `branching.py:count_isomorphisms`, `_choose_branching_class` |
| Ch. 4 | Fast Colour Refinement | `fast_colorref.py:fast_colour_refine`, `Partition` class |
| Ch. 5 | Automorphism Groups | `branching.py:_count_aut_core`, `permutation.py` (all) |
| Ch. 6 | Preprocessing | `preprocessing.py` (all functions) |

### By Lecture

| Lecture | Topic | What to re-read for review |
|---------|-------|---------------------------|
| **Kick-off** | Project overview, GI/Aut definitions | Reader Ch. 1 |
| **L1** | Colour refinement: concept, examples, stable/balanced/discrete | Reader Ch. 2, `colorref.py` |
| **L2** | Branching: individualization-refinement, recursion tree | Reader Ch. 3, `branching.py:count_isomorphisms` |
| **L3** | Fast colour refinement via DFA minimisation, O(m log n) | Reader Ch. 4, `fast_colorref.py` |
| **L4** | Automorphism groups: generators, orbits, Schreier-Sims, pruning | Reader Ch. 5, `permutation.py`, `branching.py:_count_aut_core` |
| **Python slides** | Graph class API | `graph.py`, `graph_io.py` |

---

## 7. Key Data Structures

### Vertex colouring (basic)

In `colorref.py`, each `Vertex` object gets a `.colour` attribute set dynamically:
```python
v.colour = 3  # vertex v has colour 3
```

### Partition (fast refinement)

In `fast_colorref.py`, the `Partition` class stores:
```python
partition.classes = {0: {v1, v5, v9}, 1: {v2, v3}, 2: {v4, v6, v7, v8}}
partition.vertex_colour = {v1: 0, v2: 1, v3: 1, v4: 2, ...}
```

### Permutation

In `permutation.py`, a `Permutation` stores only moved elements:
```python
p = Permutation({0: 1, 1: 0})  # swaps 0 and 1, fixes everything else
p(0)  # → 1
p(2)  # → 2 (not in dict → fixed)
p.is_identity()  # False
```

### Generating set

A list of `Permutation` objects that together generate the full automorphism group:
```python
generators = [Permutation({0:1, 1:0}), Permutation({2:3, 3:2})]
# These generate all permutations that independently swap {0,1} and {2,3}
# Group order = 2 × 2 = 4
```

### Stabiliser chain

Built by `_build_chain` in `permutation.py`:
```
Level 0: base point β₁, orbit of β₁, transversal, generators for G
Level 1: base point β₂, orbit of β₂ under Stab(β₁), generators for Stab(β₁)
Level 2: ...
|G| = |orbit₀| × |orbit₁| × |orbit₂| × ...
```

---

## 8. How to Run

```bash
# GI only (filename contains "GI")
python3 branching.py path/to/instanceGI.grl

# #Aut only (filename contains "Aut")
python3 branching.py path/to/instanceAut.grl

# Both GI and #Aut (filename contains "GIAut")
python3 branching.py path/to/instanceGIAut.grl

# Single graph .gr file (defaults to #Aut)
python3 branching.py path/to/instance.gr

# Run on all sample graphs
for f in SampleGraphsBasicColourRefinement/*.grl; do
    echo "=== $(basename $f) ==="
    python3 branching.py "$f"
    echo
done
```

---

## 9. Glossary

| Term | Definition | Where defined |
|------|-----------|---------------|
| **Isomorphism** | Bijection f: V(G)→V(H) preserving edges | Reader Def 1.4 |
| **Automorphism** | Isomorphism from G to itself | Reader Def 1.6 |
| **Colouring** | Function α: V(G) → {1,...,k} assigning colours | Reader Def 2.2 |
| **Stable colouring** | Same-coloured vertices have identically-coloured neighbourhoods | Reader Def 2.13 |
| **Balanced colouring** | Each colour appears equally often in G and H | Reader Def 2.15 |
| **Discrete colouring** | Every vertex has a unique colour | Reader Def 2.12 |
| **Colour class** | Set of vertices with the same colour | Reader Def 2.7 |
| **Partition** | Grouping of vertices into disjoint cells | Reader Sec 2.5 |
| **Individualization** | Giving a vertex a unique colour to "fix" it | Reader Ch. 3 |
| **Branching** | Trying all possible vertex mappings recursively | Reader Ch. 3 |
| **Generating set** | Set X where ⟨X⟩ = full group (every element is a product of elements in X) | Reader Def 5.6 |
| **Orbit** | Set of elements reachable from α by applying generators | Reader Def 5.12 |
| **Stabiliser** | Subgroup of elements that fix a point: Stab(α) = {g : g(α) = α} | Reader Def 5.13 |
| **Transversal** | For each orbit element β, a specific group element mapping α→β | Reader Sec 5.5.4 |
| **Schreier generator** | u(g(β))⁻¹ ∘ g ∘ u(β) — generates the stabiliser subgroup | Reader Thm 5.19 |
| **AHU** | Aho-Hopcroft-Ullman tree isomorphism algorithm | Reader Sec 6.2 |
| **True twins** | Adjacent vertices with same closed neighbourhood | Reader Sec 6.3 |
| **False twins** | Non-adjacent vertices with same open neighbourhood | Reader Sec 6.3 |
| **Tree center** | 1-2 vertices remaining after iterative leaf removal | Standard graph theory |
