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
)
from permutation import Permutation, group_order
from preprocessing import (
    is_tree, is_forest, find_components, tree_canonical_label,
    tree_automorphisms,
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

class _BranchingContext:
    """Pre-computed state shared across all recursive calls for a pair
    of graphs, avoiding repeated allocation."""

    __slots__ = ("adj", "all_vertices", "verts_g", "verts_h",
                 "n_g", "base_colouring")

    def __init__(self, graph_g: Graph, graph_h: Graph, adj: Dict):
        self.adj = adj
        self.verts_g = list(graph_g)
        self.verts_h = list(graph_h)
        self.n_g = len(self.verts_g)
        self.all_vertices = self.verts_g + self.verts_h
        self.base_colouring = {v: 0 for v in self.all_vertices}

    def refine_and_check(self, D: list, I: list):
        """Run colour refinement with α(D,I) and classify the result.

        Returns (partition, status) where status is 0 (unbalanced),
        1 (bijection), or 2 (branch needed).
        """
        # Build colouring: modify base, refine, then restore
        base = self.base_colouring
        depth = len(D)
        for i in range(depth):
            c = i + 1
            base[D[i]] = c
            base[I[i]] = c

        partition = fast_colour_refine(self.all_vertices, self.adj, base)

        # Restore base colouring to all-zeros
        for i in range(depth):
            base[D[i]] = 0
            base[I[i]] = 0

        if not is_balanced_pair(self.verts_g, self.verts_h, partition):
            return None, 0
        if is_discrete_pair(self.verts_g, self.verts_h, partition):
            return partition, 1
        return partition, 2


def is_balanced_pair(verts_g: list, verts_h: list, partition: Partition) -> bool:
    """Fast balanced check for exactly two graphs."""
    vc = partition.vertex_colour
    counts_g: Dict[int, int] = {}
    for v in verts_g:
        c = vc[v]
        counts_g[c] = counts_g.get(c, 0) + 1
    for v in verts_h:
        c = vc[v]
        cnt = counts_g.get(c, 0) - 1
        if cnt < 0:
            return False
        counts_g[c] = cnt
    return all(c == 0 for c in counts_g.values())


def is_discrete_pair(verts_g: list, verts_h: list, partition: Partition) -> bool:
    """Check discrete for two graphs (fast, no set allocation)."""
    vc = partition.vertex_colour
    n = len(verts_g)
    if n != len(verts_h):
        return False
    # A discrete colouring has n distinct colours per graph
    # Since balanced, just check one graph
    seen = set()
    for v in verts_g:
        c = vc[v]
        if c in seen:
            return False
        seen.add(c)
    return True


def _choose_branching_class(verts_g: list, verts_h: list,
                            partition: Partition
                            ) -> Tuple[List[Vertex], List[Vertex]]:
    """Choose the smallest non-trivial colour class to branch on."""
    vc = partition.vertex_colour
    colours_g: Dict[int, list] = {}
    colours_h: Dict[int, list] = {}

    for v in verts_g:
        c = vc[v]
        if c in colours_g:
            colours_g[c].append(v)
        else:
            colours_g[c] = [v]
    for v in verts_h:
        c = vc[v]
        if c in colours_h:
            colours_h[c].append(v)
        else:
            colours_h[c] = [v]

    best_colour = -1
    best_size = 0x7FFFFFFF

    for colour, vg in colours_g.items():
        lg = len(vg)
        if lg < 2:
            continue
        vh = colours_h.get(colour)
        if vh is None or len(vh) < 2:
            continue
        if lg < best_size:
            best_size = lg
            best_colour = colour

    return colours_g[best_colour], colours_h[best_colour]


def _extract_bijection(verts_g: list, verts_h: list,
                       partition: Partition) -> Dict[Vertex, Vertex]:
    """Extract the vertex mapping f: V(G) → V(H) from a bijection partition."""
    vc = partition.vertex_colour
    colour_to_h: Dict[int, Vertex] = {}
    for v in verts_h:
        colour_to_h[vc[v]] = v
    return {v: colour_to_h[vc[v]] for v in verts_g}


# ---------------------------------------------------------------------------
# GI branching  (Algorithm 2 — CountIsomorphism)
# ---------------------------------------------------------------------------

def count_isomorphisms(graph_g: Graph,
                       graph_h: Graph,
                       D: List[Vertex],
                       I: List[Vertex],
                       adj: Dict,
                       gi_only: bool = False) -> int:
    """Count isomorphisms from *graph_g* to *graph_h* following (D, I).

    Algorithm 2 (CountIsomorphism) from Chapter 3.
    """
    ctx = _BranchingContext(graph_g, graph_h, adj)

    def _count(D: list, I: list) -> int:
        partition, status = ctx.refine_and_check(D, I)
        if status == 0:
            return 0
        if status == 1:
            return 1

        cg, ch = _choose_branching_class(ctx.verts_g, ctx.verts_h, partition)
        x = cg[0]

        num = 0
        D.append(x)
        for y in ch:
            I.append(y)
            num += _count(D, I)
            I.pop()
            if gi_only and num > 0:
                D.pop()
                return num
        D.pop()
        return num

    return _count(list(D), list(I))


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

    return _count_aut_core(graph, adj, None)



def _count_aut_core(graph: Graph, adj: Dict,
                    pre_colouring: Optional[Dict]) -> int:
    """Core #Aut via generating sets + Lemma 5.11 pruning.

    Args:
        graph:          The graph (possibly twin-reduced).
        adj:            Pre-computed adjacency lists.
        pre_colouring:  Optional initial colouring from twin reduction.
    """
    graph_copy, vertex_map = _copy_graph(graph)

    for v in graph_copy:
        adj[v] = v.neighbours

    orig_verts = list(graph.vertices)
    copy_verts = list(graph_copy.vertices)
    copy_to_orig = {copy_verts[i]: orig_verts[i]
                    for i in range(len(orig_verts))}

    ctx = _BranchingContext(graph, graph_copy, adj)

    # Apply pre-colouring if provided (from twin reduction)
    if pre_colouring is not None:
        for v in orig_verts:
            ctx.base_colouring[v] = pre_colouring.get(v, 0)
        for i, v in enumerate(copy_verts):
            ctx.base_colouring[v] = pre_colouring.get(orig_verts[i], 0)

    generating_set: List[Permutation] = []

    def _to_permutation(partition: Partition) -> Permutation:
        bijection = _extract_bijection(ctx.verts_g, ctx.verts_h, partition)
        return Permutation({v: copy_to_orig[bijection[v]] for v in orig_verts})

    D: list = []
    I: list = []

    def _update() -> None:
        """Algorithm 9 — recursive branching with Lemma 5.11 pruning."""
        partition, status = ctx.refine_and_check(D, I)
        if status == 0:
            return
        if status == 1:
            perm = _to_permutation(partition)
            if not perm.is_identity():
                generating_set.append(perm)
            return

        cg, ch = _choose_branching_class(ctx.verts_g, ctx.verts_h, partition)
        x = cg[0]
        x_copy = vertex_map[x]
        others = [y for y in ch if y is not x_copy]

        D.append(x)
        if x_copy in ch:
            I.append(x_copy)
            _update()
            I.pop()

        for y in others:
            I.append(y)
            _find_one(cg, ch)
            I.pop()
        D.pop()

    def _find_one(parent_cg, parent_ch) -> bool:
        """Find one automorphism in this non-trivial branch."""
        partition, status = ctx.refine_and_check(D, I)
        if status == 0:
            return False
        if status == 1:
            perm = _to_permutation(partition)
            if perm.is_identity():
                return False
            generating_set.append(perm)
            return True

        cg, ch = _choose_branching_class(ctx.verts_g, ctx.verts_h, partition)
        x = cg[0]
        D.append(x)
        for y in ch:
            I.append(y)
            found = _find_one(cg, ch)
            I.pop()
            if found:
                D.pop()
                return True
        D.pop()
        return False

    _update()
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


def _are_isomorphic(graph_g: Graph, graph_h: Graph, adj: Dict) -> bool:
    """Decide whether *graph_g* and *graph_h* are isomorphic."""
    if len(graph_g) != len(graph_h):
        return False
    if len(graph_g.edges) != len(graph_h.edges):
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
