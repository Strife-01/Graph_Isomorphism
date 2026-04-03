"""
Branching — Individualization-Refinement for GI and #Aut.

When fast colour refinement yields a stable colouring that is balanced
but not discrete, branching resolves the ambiguity by picking a vertex
x in graph G from a non-trivial colour class, trying every possible
mapping x → y in the same colour class of graph H, and recursing.

Two branching strategies are provided:

  * ``count_isomorphisms``  (Algorithm 2, Chapter 3)
    Enumerates all isomorphisms — used for GI and as a fallback.

  * ``count_automorphisms`` (Algorithm 9, Chapter 5)
    Builds a *generating set* of Aut(G) and computes its order via
    the orbit-stabiliser theorem.  Prunes redundant branches with
    Lemma 5.11, making it feasible even for graphs with 10^33+
    automorphisms (e.g. bigtrees3).
"""

from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from graph import Graph, Vertex, Edge
from graph_io import load_graph
from fast_colorref import (
    colour_refine_graphs,
    _build_neighbour_index,
    fast_colour_refine,
    Partition,
    get_colour_signature,
    is_balanced,
    is_discrete_for_graph,
    defines_bijection,
)
from permutation import Permutation, IDENTITY, group_order
from preprocessing import (
    is_tree, is_forest, find_components, tree_canonical_label,
    tree_automorphisms, find_twin_groups,
)
from math import factorial


# ---------------------------------------------------------------------------
# Graph copy utility
# ---------------------------------------------------------------------------

def _copy_graph(graph: Graph) -> Tuple[Graph, Dict[Vertex, Vertex]]:
    """Create an independent copy of *graph* with fresh vertex objects.

    Returns:
        (copy, mapping) where mapping maps each original vertex to its
        copy counterpart (by position in the vertex list).
    """
    copy = Graph(directed=graph.directed, n=len(graph))
    copy_verts = list(copy.vertices)
    orig_verts = list(graph.vertices)
    index_of = {v: i for i, v in enumerate(orig_verts)}
    vertex_map = {orig_verts[i]: copy_verts[i] for i in range(len(orig_verts))}

    seen_edges: set = set()
    for e in graph.edges:
        ti, hi = index_of[e.tail], index_of[e.head]
        edge_key = (min(ti, hi), max(ti, hi))
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            copy.add_edge(Edge(copy_verts[ti], copy_verts[hi]))

    return copy, vertex_map


# ---------------------------------------------------------------------------
# Branching helpers
# ---------------------------------------------------------------------------

def _refine_and_check(graph_g: Graph,
                      graph_h: Graph,
                      D: List[Vertex],
                      I: List[Vertex],
                      adj: Dict[Vertex, List[Vertex]]
                      ) -> Tuple[Optional[Partition], str]:
    """Run colour refinement with the α(D,I) initial colouring and
    classify the result.

    Returns:
        (partition, status) where status is one of:
          "unbalanced"  — no isomorphism follows (D, I)
          "bijection"   — unique isomorphism follows (D, I)
          "branch"      — balanced but not discrete, needs branching
    """
    all_vertices = list(graph_g) + list(graph_h)
    initial_colouring: Dict[Vertex, int] = {v: 0 for v in all_vertices}
    for i, (d, iv) in enumerate(zip(D, I)):
        initial_colouring[d] = i + 1
        initial_colouring[iv] = i + 1

    partition = fast_colour_refine(all_vertices, adj, initial_colouring)

    if not is_balanced([graph_g, graph_h], partition):
        return None, "unbalanced"
    if defines_bijection(graph_g, graph_h, partition):
        return partition, "bijection"
    return partition, "branch"


def _choose_branching_class(graph_g: Graph,
                            graph_h: Graph,
                            partition: Partition
                            ) -> Tuple[List[Vertex], List[Vertex]]:
    """Choose a non-trivial colour class to branch on.

    Branching rule: pick the colour class with the *smallest* number of
    vertices per graph (≥ 2 per graph, so ≥ 4 total).  This minimises
    the branching factor at each level.

    Returns:
        (vertices_in_G, vertices_in_H) for the chosen colour class.
    """
    colours_g: Dict[int, List[Vertex]] = defaultdict(list)
    colours_h: Dict[int, List[Vertex]] = defaultdict(list)

    for v in graph_g:
        colours_g[partition.vertex_colour[v]].append(v)
    for v in graph_h:
        colours_h[partition.vertex_colour[v]].append(v)

    best_colour = None
    best_size = float("inf")

    for colour, verts_g in colours_g.items():
        if len(verts_g) < 2:
            continue
        verts_h = colours_h.get(colour, [])
        if len(verts_h) < 2:
            continue
        if len(verts_g) < best_size:
            best_size = len(verts_g)
            best_colour = colour

    return colours_g[best_colour], colours_h[best_colour]


def _extract_bijection(graph_g: Graph,
                       graph_h: Graph,
                       partition: Partition) -> Dict[Vertex, Vertex]:
    """Extract the vertex mapping f: V(G) → V(H) from a partition that
    defines a bijection (each colour used exactly once per graph)."""
    colour_to_h: Dict[int, Vertex] = {}
    for v in graph_h:
        colour_to_h[partition.vertex_colour[v]] = v

    mapping: Dict[Vertex, Vertex] = {}
    for v in graph_g:
        mapping[v] = colour_to_h[partition.vertex_colour[v]]
    return mapping


# ---------------------------------------------------------------------------
# GI branching  (Algorithm 2 — CountIsomorphism)
# ---------------------------------------------------------------------------

def count_isomorphisms(graph_g: Graph,
                       graph_h: Graph,
                       D: List[Vertex],
                       I: List[Vertex],
                       adj: Dict[Vertex, List[Vertex]],
                       gi_only: bool = False) -> int:
    """Count isomorphisms from *graph_g* to *graph_h* following (D, I).

    Algorithm 2 (CountIsomorphism) from Chapter 3 of the reader.
    Used for the GI decision problem (with ``gi_only=True``).

    Args:
        graph_g:  The first graph.
        graph_h:  The second graph.
        D, I:     Vertex-mapping sequences already fixed.
        adj:      Pre-computed adjacency lists for all vertices.
        gi_only:  If True, return 0 or 1 (stop after first isomorphism).

    Returns:
        Number of isomorphisms following (D, I).
    """
    partition, status = _refine_and_check(graph_g, graph_h, D, I, adj)

    if status == "unbalanced":
        return 0
    if status == "bijection":
        return 1

    colour_class_g, colour_class_h = _choose_branching_class(
        graph_g, graph_h, partition
    )
    x = colour_class_g[0]

    num = 0
    for y in colour_class_h:
        num += count_isomorphisms(
            graph_g, graph_h, D + [x], I + [y], adj, gi_only
        )
        if gi_only and num > 0:
            return num
    return num


# ---------------------------------------------------------------------------
# Preprocessing: forest automorphisms
# ---------------------------------------------------------------------------

def _forest_automorphisms(graph: Graph) -> int:
    """Count |Aut(F)| for a forest F using AHU (O(n)).

    Each component's automorphisms are computed independently, then
    multiplied together.  Isomorphic components can be permuted,
    contributing an additional k! factor per group of k isomorphic trees.
    """
    components = find_components(graph)

    # Group components by their canonical tree label
    label_groups: Dict[Tuple, List[List[Vertex]]] = defaultdict(list)
    for comp in components:
        label = tree_canonical_label(comp)
        label_groups[label].append(comp)

    total = 1
    for label, comps in label_groups.items():
        for comp in comps:
            total *= tree_automorphisms(comp)
        # k isomorphic components can be permuted: ×k!
        total *= factorial(len(comps))

    return total


# ---------------------------------------------------------------------------
# #Aut branching  (Algorithm 9 — UpdateGeneratingSet + pruning)
# ---------------------------------------------------------------------------

def count_automorphisms(graph: Graph,
                        adj: Dict[Vertex, List[Vertex]]) -> int:
    """Count |Aut(graph)| using generating sets and pruning.

    Preprocessing (Chapter 6):
      - Trees/forests are solved in O(n) via AHU.
      - Disconnected graphs are decomposed into components.

    General case (Chapters 3+5):
      1. Build a generating set X of Aut(G) by comparing G to a copy H.
      2. Prune branches using Lemma 5.11.
      3. Compute |Aut(G)| = |⟨X⟩| via the orbit-stabiliser theorem.

    Args:
        graph:  The graph.
        adj:    Pre-computed adjacency lists.

    Returns:
        |Aut(graph)|
    """
    # Preprocessing: forests are solved directly via AHU
    if is_forest(graph):
        return _forest_automorphisms(graph)

    graph_copy, vertex_map = _copy_graph(graph)

    for v in graph_copy:
        adj[v] = v.neighbours

    orig_verts = list(graph.vertices)
    copy_verts = list(graph_copy.vertices)
    copy_to_orig = {copy_verts[i]: orig_verts[i]
                    for i in range(len(orig_verts))}

    generating_set: List[Permutation] = []

    def _to_permutation(partition: Partition) -> Permutation:
        """Convert a bijection-defining partition to a Permutation on
        orig_verts."""
        bijection = _extract_bijection(graph, graph_copy, partition)
        perm_map = {v: copy_to_orig[bijection[v]] for v in orig_verts}
        return Permutation(perm_map)

    def _update(D: List[Vertex], I: List[Vertex]) -> bool:
        """Algorithm 9 — recursive branching with Lemma 5.11 pruning.

        Returns True if a NEW non-trivial automorphism was added to the
        generating set (signals the caller to prune).
        """
        partition, status = _refine_and_check(graph, graph_copy, D, I, adj)

        if status == "unbalanced":
            return False

        if status == "bijection":
            perm = _to_permutation(partition)
            if perm.is_identity():
                return False
            generating_set.append(perm)
            return True

        # Branch
        colour_class_g, colour_class_h = _choose_branching_class(
            graph, graph_copy, partition
        )
        x = colour_class_g[0]
        x_copy = vertex_map[x]

        # Process the trivial mapping (x → x_copy) first to collect
        # all automorphisms that fix x (the stabiliser at this level).
        others = [y for y in colour_class_h if y is not x_copy]

        # Trivial branch: x → x_copy (walk down the trivial path)
        if x_copy in colour_class_h:
            _update(D + [x], I + [x_copy])

        # Non-trivial branches: x → y for y ≠ x_copy
        # By Lemma 5.11, once we find one automorphism mapping x→y,
        # our generating set already generates ALL automorphisms with
        # that mapping.  So we stop exploring that branch immediately.
        for y in others:
            _find_one_automorphism(D + [x], I + [y])

        return False

    def _find_one_automorphism(D: List[Vertex], I: List[Vertex]) -> bool:
        """Explore a non-trivial branch, stopping as soon as any single
        automorphism is found at any depth (Lemma 5.11 pruning)."""
        partition, status = _refine_and_check(graph, graph_copy, D, I, adj)

        if status == "unbalanced":
            return False

        if status == "bijection":
            perm = _to_permutation(partition)
            if perm.is_identity():
                return False
            generating_set.append(perm)
            return True

        # Must branch further, but still looking for just ONE automorphism
        colour_class_g, colour_class_h = _choose_branching_class(
            graph, graph_copy, partition
        )
        x = colour_class_g[0]

        for y in colour_class_h:
            if _find_one_automorphism(D + [x], I + [y]):
                return True  # Found one — prune immediately
        return False

    _update([], [])

    return group_order(generating_set, orig_verts)


# ---------------------------------------------------------------------------
# GI problem — find equivalence classes
# ---------------------------------------------------------------------------

def _tree_equivalence_classes(graphs: List[Graph]) -> List[List[int]]:
    """Partition trees into equivalence classes using AHU canonical labels.

    O(n) per tree — no branching needed.
    """
    label_groups: Dict[Tuple, List[int]] = defaultdict(list)
    for i, G in enumerate(graphs):
        label = tree_canonical_label(list(G.vertices))
        label_groups[label].append(i)
    return sorted([sorted(g) for g in label_groups.values()],
                  key=lambda c: c[0])


def _are_isomorphic(graph_g: Graph, graph_h: Graph,
                    adj: Dict[Vertex, List[Vertex]]) -> bool:
    """Decide whether *graph_g* and *graph_h* are isomorphic."""
    if len(graph_g) != len(graph_h):
        return False
    return count_isomorphisms(graph_g, graph_h, [], [], adj, gi_only=True) > 0


def find_equivalence_classes(graphs: List[Graph],
                             adj: Dict[Vertex, List[Vertex]]
                             ) -> List[List[int]]:
    """Partition graphs into equivalence classes of isomorphic graphs.

    Uses fast colour refinement as a first pass to cheaply separate
    obviously non-isomorphic graphs, then applies branching only within
    groups that colour refinement cannot distinguish.

    Args:
        graphs:  List of Graph objects.
        adj:     Pre-computed adjacency lists for all vertices.

    Returns:
        A sorted list of sorted graph-index lists.
    """
    partition = colour_refine_graphs(graphs)
    sig_groups: Dict[Tuple, List[int]] = defaultdict(list)
    for i, G in enumerate(graphs):
        sig = get_colour_signature(G, partition)
        sig_groups[sig].append(i)

    equivalence_classes: List[List[int]] = []
    for indices in sig_groups.values():
        if len(indices) == 1:
            equivalence_classes.append(indices)
            continue

        remaining = set(indices)
        for i in indices:
            if i not in remaining:
                continue
            eq_class = [i]
            remaining.remove(i)
            to_remove = []
            for j in remaining:
                if _are_isomorphic(graphs[i], graphs[j], adj):
                    eq_class.append(j)
                    to_remove.append(j)
            for j in to_remove:
                remaining.remove(j)
            equivalence_classes.append(sorted(eq_class))

    return sorted(equivalence_classes, key=lambda c: c[0])


# ---------------------------------------------------------------------------
# Public API — solve from file
# ---------------------------------------------------------------------------

def solve(filename: str) -> None:
    """Solve the GI and/or #Aut problem for the given file and print results.

    Automatically detects the problem type from the filename:
        - ``*GI.grl``     → equivalence classes only
        - ``*Aut.grl/gr`` → automorphism counts only
        - ``*GIAut.grl``  → both

    Args:
        filename:  Path to a ``.grl`` or ``.gr`` file.
    """
    name = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    do_gi = "GI" in name
    do_aut = "Aut" in name

    if not do_gi and not do_aut:
        if filename.endswith(".gr"):
            do_aut = True
        else:
            do_gi = True

    is_single = filename.endswith(".gr")

    if is_single:
        with open(filename, "r") as f:
            graph = load_graph(f, graph_class=Graph, read_list=False)
        adj = _build_neighbour_index(list(graph))
        aut = count_automorphisms(graph, adj)
        print(f"Number of automorphisms: {aut}")
        return

    with open(filename, "r") as f:
        graphs = load_graph(f, graph_class=Graph, read_list=True)

    all_verts = [v for G in graphs for v in G]
    adj = _build_neighbour_index(all_verts)

    # Preprocessing: if ALL graphs are trees, use AHU for both GI and #Aut
    all_trees = all(is_tree(G) for G in graphs)

    if do_gi and not do_aut:
        if all_trees:
            classes = _tree_equivalence_classes(graphs)
        else:
            classes = find_equivalence_classes(graphs, adj)
        print("Sets of isomorphic graphs:")
        for eq_class in classes:
            print(eq_class)

    elif do_aut and not do_gi:
        print("Number of automorphisms for each graph:")
        for i, G in enumerate(graphs):
            local_adj = _build_neighbour_index(list(G))
            aut = count_automorphisms(G, local_adj)
            print(f"{i}: {aut}")

    else:
        if all_trees:
            classes = _tree_equivalence_classes(graphs)
        else:
            classes = find_equivalence_classes(graphs, adj)
        print("Sets of isomorphic graphs with automorphisms:")
        for eq_class in classes:
            rep = eq_class[0]
            local_adj = _build_neighbour_index(list(graphs[rep]))
            aut = count_automorphisms(graphs[rep], local_adj)
            print(f"{eq_class}: {aut}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python branching.py <graph_file.grl|.gr>")
        sys.exit(1)
    solve(sys.argv[1])
