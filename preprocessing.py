"""
Preprocessing — structural detection and simplification (Chapter 6).

Before running the full branching algorithm, we can detect special graph
structures and handle them more efficiently:

  * **Trees / Forests**:  Isomorphism and #Aut solved in O(n) via the
    AHU algorithm (Section 6.2).
  * **Twins / False twins**:  Sets of (false) twins are collapsed; the
    automorphism count is multiplied by k! per set of k twins (Section 6.3).
  * **Connected components**:  Decompose disconnected graphs and solve
    per-component (Section 6.4).
"""

from collections import defaultdict, deque
from math import factorial
from typing import Dict, List, Optional, Set, Tuple
from graph import Graph, Vertex


# ---------------------------------------------------------------------------
# Component decomposition  (Section 6.4)
# ---------------------------------------------------------------------------

def find_components(graph: Graph) -> List[List[Vertex]]:
    """Find connected components via BFS.

    Args:
        graph:  The graph.

    Returns:
        A list of components, each a list of vertices.
    """
    visited: Set[Vertex] = set()
    components: List[List[Vertex]] = []

    for start in graph:
        if start in visited:
            continue
        component: List[Vertex] = []
        queue: deque = deque([start])
        visited.add(start)
        while queue:
            v = queue.popleft()
            component.append(v)
            for u in v.neighbours:
                if u not in visited:
                    visited.add(u)
                    queue.append(u)
        components.append(component)

    return components


def is_connected(graph: Graph) -> bool:
    """Check whether *graph* is connected."""
    if len(graph) == 0:
        return True
    components = find_components(graph)
    return len(components) == 1


# ---------------------------------------------------------------------------
# Tree / Forest detection  (Section 6.2)
# ---------------------------------------------------------------------------

def is_tree(graph: Graph) -> bool:
    """Check whether *graph* is a tree (connected acyclic graph)."""
    n = len(graph)
    if n == 0:
        return True
    return is_connected(graph) and len(graph.edges) == n - 1


def is_forest(graph: Graph) -> bool:
    """Check whether *graph* is a forest (acyclic graph, possibly
    disconnected)."""
    components = find_components(graph)
    n = len(graph)
    m = len(graph.edges)
    return m == n - len(components)


# ---------------------------------------------------------------------------
# AHU algorithm for rooted tree isomorphism  (Section 6.2)
# ---------------------------------------------------------------------------

def _find_center(vertices: List[Vertex]) -> List[Vertex]:
    """Find the center of a tree (1 or 2 vertices).

    Iteratively removes leaves until 1 or 2 vertices remain.
    """
    if len(vertices) <= 2:
        return list(vertices)

    vertex_set = set(vertices)
    degree: Dict[Vertex, int] = {}
    for v in vertex_set:
        degree[v] = sum(1 for u in v.neighbours if u in vertex_set)

    remaining = set(vertex_set)
    leaves = [v for v in remaining if degree[v] <= 1]

    while len(remaining) > 2:
        new_leaves: List[Vertex] = []
        for leaf in leaves:
            remaining.discard(leaf)
            for u in leaf.neighbours:
                if u in remaining:
                    degree[u] -= 1
                    if degree[u] == 1:
                        new_leaves.append(u)
        leaves = new_leaves

    return list(remaining)


def ahu_label(root: Vertex, parent: Optional[Vertex],
              vertex_set: Set[Vertex]) -> Tuple:
    """Compute the AHU canonical label for a rooted subtree.

    The label is a recursively-defined sorted tuple of children's labels.
    Leaves get label ``()``.

    Args:
        root:        The root of the subtree.
        parent:      The parent of *root* (None for the actual root).
        vertex_set:  The set of vertices belonging to this tree component.

    Returns:
        A hashable canonical label (nested tuples).
    """
    children_labels = []
    for child in root.neighbours:
        if child != parent and child in vertex_set:
            children_labels.append(ahu_label(child, root, vertex_set))
    return tuple(sorted(children_labels))


def tree_canonical_label(vertices: List[Vertex]) -> Tuple:
    """Compute a canonical label for an unrooted tree.

    Roots at the center (1 or 2 vertices).  If there are 2 centers,
    we use both and pick the lexicographically smallest.

    Args:
        vertices:  The vertices of a single tree component.

    Returns:
        A canonical label (hashable) that is identical for isomorphic trees.
    """
    vertex_set = set(vertices)
    centers = _find_center(vertices)

    if len(centers) == 1:
        return ahu_label(centers[0], None, vertex_set)

    # Two centers — root at each and take the canonical minimum
    label_a = ahu_label(centers[0], None, vertex_set)
    label_b = ahu_label(centers[1], None, vertex_set)
    return min(label_a, label_b)


def tree_automorphisms(vertices: List[Vertex]) -> int:
    """Count |Aut(T)| for a tree T using the AHU structure.

    For a rooted tree, |Aut(T)| = ∏_v (k_v! × ∏_{children c of v} |Aut(T_c)|)
    where k_v is the number of children of v with identical subtree labels
    (grouped by label, each group contributing group_size!).

    For an unrooted tree, we root at the center.  If there are two centers
    connected by an edge and their subtrees are isomorphic, we multiply by 2.
    """
    vertex_set = set(vertices)
    centers = _find_center(vertices)

    def _count_rooted(root: Vertex, parent: Optional[Vertex]) -> Tuple[int, Tuple]:
        """Returns (aut_count, canonical_label) for rooted subtree."""
        children_data: List[Tuple[int, Tuple]] = []
        for child in root.neighbours:
            if child != parent and child in vertex_set:
                children_data.append(_count_rooted(child, root))

        # Group children by their canonical label
        label_groups: Dict[Tuple, int] = defaultdict(int)
        aut = 1
        for child_aut, child_label in children_data:
            aut *= child_aut
            label_groups[child_label] += 1

        # For each group of k identical subtrees: multiply by k!
        for count in label_groups.values():
            aut *= factorial(count)

        label = tuple(sorted(child_label for _, child_label in children_data))
        return aut, label

    if len(centers) == 1:
        aut, _ = _count_rooted(centers[0], None)
        return aut

    # Two centers
    aut_a, label_a = _count_rooted(centers[0], centers[1])
    aut_b, label_b = _count_rooted(centers[1], centers[0])
    total = aut_a * aut_b

    # If the two halves are isomorphic, we can also swap them → ×2
    if label_a == label_b:
        total *= 2

    return total


# ---------------------------------------------------------------------------
# Twins detection  (Section 6.3)
# ---------------------------------------------------------------------------

def find_twin_groups(graph: Graph) -> Tuple[List[Set[Vertex]], List[Set[Vertex]]]:
    """Detect sets of true twins and false twins.

    True twins: u,v adjacent AND N(u)\\{v} = N(v)\\{u}.
    False twins: N(u) = N(v) (not adjacent to each other).

    Returns:
        (true_twin_groups, false_twin_groups) — each a list of sets,
        where each set has ≥ 2 vertices.
    """
    # Signature for false twins: frozenset of neighbours
    # Signature for true twins: frozenset of neighbours ∪ {self}
    false_sig: Dict[frozenset, List[Vertex]] = defaultdict(list)
    true_sig: Dict[frozenset, List[Vertex]] = defaultdict(list)

    for v in graph:
        nbrs = frozenset(v.neighbours)
        false_sig[nbrs].append(v)
        true_sig[nbrs | {v}].append(v)

    false_groups = [set(g) for g in false_sig.values() if len(g) >= 2]
    true_groups = [set(g) for g in true_sig.values() if len(g) >= 2]

    return true_groups, false_groups
