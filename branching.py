"""
Branching — Individualization-Refinement for GI and #Aut.

When fast colour refinement yields a stable colouring that is balanced
but not discrete, branching resolves the ambiguity by picking a vertex
x in graph G from a non-trivial colour class, trying every possible
mapping x → y in the same colour class of graph H, and recursing.

Implements Algorithm 2 (CountIsomorphism) from Chapter 3 of the reader.

For the GI problem we compare pairs of graphs; for the #Aut problem we
compare a graph to a copy of itself.  In both cases the core routine is
``count_isomorphisms``, which counts colour-preserving bijections that
follow given vertex-mapping sequences (D, I).
"""

from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from graph import Graph, Vertex
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


# ---------------------------------------------------------------------------
# Core branching routine
# ---------------------------------------------------------------------------

def count_isomorphisms(graph_g: Graph,
                       graph_h: Graph,
                       D: List[Vertex],
                       I: List[Vertex],
                       adj: Dict[Vertex, List[Vertex]],
                       gi_only: bool = False) -> int:
    """Count the number of isomorphisms from *graph_g* to *graph_h*
    that follow the vertex-mapping sequences (D, I).

    This is Algorithm 2 (CountIsomorphism) from the reader.

    Args:
        graph_g:  The first graph.
        graph_h:  The second graph (may be the same object for #Aut).
        D:        Sequence of vertices in graph_g already mapped.
        I:        Sequence of vertices in graph_h already mapped.
        adj:      Pre-computed adjacency lists for all vertices.
        gi_only:  If True, return as soon as one isomorphism is found
                  (sufficient for the GI decision problem).

    Returns:
        The number of isomorphisms following (D, I).
        If *gi_only* is True, returns 0 or 1.
    """
    # Build initial colouring α(D, I):
    #   D[i] and I[i] get colour i+1, everything else gets colour 0
    all_vertices = list(graph_g) + list(graph_h)
    initial_colouring: Dict[Vertex, int] = {v: 0 for v in all_vertices}
    for i, (d, iv) in enumerate(zip(D, I)):
        initial_colouring[d] = i + 1
        initial_colouring[iv] = i + 1

    # Compute coarsest stable colouring
    partition = fast_colour_refine(all_vertices, adj, initial_colouring)

    # Base case 1: unbalanced → no isomorphism follows (D, I)
    if not is_balanced([graph_g, graph_h], partition):
        return 0

    # Base case 2: defines a bijection → exactly one isomorphism
    if defines_bijection(graph_g, graph_h, partition):
        return 1

    # Recursive case: choose a colour class C with |C| ≥ 4 (≥ 2 per graph)
    # and branch on all possible mappings x → y
    colour_class_g, colour_class_h = _choose_branching_class(
        graph_g, graph_h, partition
    )

    # Fix x as the first vertex in the chosen class of G
    x = colour_class_g[0]

    num = 0
    for y in colour_class_h:
        num += count_isomorphisms(
            graph_g, graph_h,
            D + [x], I + [y],
            adj, gi_only
        )
        if gi_only and num > 0:
            return num

    return num


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
    # Group vertices by colour, separated by graph
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
        # Branching rule: smallest non-trivial class
        if len(verts_g) < best_size:
            best_size = len(verts_g)
            best_colour = colour

    return colours_g[best_colour], colours_h[best_colour]


# ---------------------------------------------------------------------------
# GI problem — find equivalence classes
# ---------------------------------------------------------------------------

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
    # First pass: group by colour signature (fast, no branching)
    partition = colour_refine_graphs(graphs)
    sig_groups: Dict[Tuple, List[int]] = defaultdict(list)
    for i, G in enumerate(graphs):
        sig = get_colour_signature(G, partition)
        sig_groups[sig].append(i)

    # Second pass: within each signature group, use branching to
    # resolve balanced-but-not-discrete cases
    equivalence_classes: List[List[int]] = []

    for indices in sig_groups.values():
        if len(indices) == 1:
            equivalence_classes.append(indices)
            continue

        # Check pairwise isomorphism within this group
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
# #Aut problem — count automorphisms
# ---------------------------------------------------------------------------

def count_automorphisms(graph: Graph,
                        adj: Dict[Vertex, List[Vertex]]) -> int:
    """Count the number of automorphisms of *graph*.

    Compares the graph against a *separate copy* of itself so that
    the disjoint union has distinct vertex objects for G and H.

    Args:
        graph:  The graph.
        adj:    Pre-computed adjacency lists (must include both
                original and copy vertices).

    Returns:
        |Aut(graph)|
    """
    graph_copy = _copy_graph(graph)

    # Extend adj with the copy's adjacency
    for v in graph_copy:
        adj[v] = v.neighbours

    return count_isomorphisms(graph, graph_copy, [], [], adj)


def _copy_graph(graph: Graph) -> Graph:
    """Create an independent copy of *graph* with fresh vertex objects."""
    copy = Graph(directed=graph.directed, n=len(graph))
    copy_verts = list(copy.vertices)
    orig_verts = list(graph.vertices)
    index_of = {v: i for i, v in enumerate(orig_verts)}

    # Avoid adding duplicate edges (undirected: each edge stored once)
    seen_edges = set()
    from graph import Edge
    for e in graph.edges:
        ti, hi = index_of[e.tail], index_of[e.head]
        edge_key = (min(ti, hi), max(ti, hi))
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            copy.add_edge(Edge(copy_verts[ti], copy_verts[hi]))

    return copy


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

    # If neither tag is present, default to GI for .grl, Aut for .gr
    if not do_gi and not do_aut:
        if filename.endswith(".gr"):
            do_aut = True
        else:
            do_gi = True

    is_single = filename.endswith(".gr")

    if is_single:
        # Single graph → #Aut only
        with open(filename, "r") as f:
            graph = load_graph(f, graph_class=Graph, read_list=False)
        adj = _build_neighbour_index(list(graph))
        aut = count_automorphisms(graph, adj)
        print(f"Number of automorphisms: {aut}")
        return

    # Multiple graphs from .grl file
    with open(filename, "r") as f:
        graphs = load_graph(f, graph_class=Graph, read_list=True)

    # Build adjacency index for all vertices across all graphs
    all_verts = [v for G in graphs for v in G]
    adj = _build_neighbour_index(all_verts)

    if do_gi and not do_aut:
        # GI only
        classes = find_equivalence_classes(graphs, adj)
        print("Sets of isomorphic graphs:")
        for eq_class in classes:
            print(eq_class)

    elif do_aut and not do_gi:
        # #Aut only
        print("Number of automorphisms for each graph:")
        for i, G in enumerate(graphs):
            local_adj = _build_neighbour_index(list(G))
            aut = count_automorphisms(G, local_adj)
            print(f"{i}: {aut}")

    else:
        # Both GI and #Aut
        classes = find_equivalence_classes(graphs, adj)

        # Compute automorphisms for one representative per class
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
