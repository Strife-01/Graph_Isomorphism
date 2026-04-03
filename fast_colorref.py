"""
Fast Colour Refinement — O(m log n) Hopcroft-style partition refinement.

Based on the DFA minimisation algorithm (Hopcroft, 1971) adapted for
the Graph Isomorphism problem as described in Chapter 4 of the reader.

Refine(C) for GI:  For each colour class D, partition D by the number
of neighbours each vertex has inside C.  If D splits, apply the
"add-smaller-to-queue" rule (Lemma 4.9).
"""

from collections import deque
from typing import Dict, List, Tuple, Optional
from graph import Graph, Vertex


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class Partition:
    """Partition of vertices into colour classes.

    ``classes[colour]`` is a ``set`` of vertices.
    ``vertex_colour[v]`` gives the colour of vertex v.
    """

    __slots__ = ("classes", "vertex_colour", "_next_colour")

    def __init__(self):
        self.classes: Dict[int, set] = {}
        self.vertex_colour: Dict = {}
        self._next_colour: int = 0

    def add_class(self, members: set) -> int:
        c = self._next_colour
        self._next_colour += 1
        self.classes[c] = members
        vc = self.vertex_colour
        for v in members:
            vc[v] = c
        return c

    @property
    def num_classes(self) -> int:
        return len(self.classes)


# ---------------------------------------------------------------------------
# Adjacency helper
# ---------------------------------------------------------------------------

def _build_neighbour_index(vertices) -> Dict:
    """Pre-compute adjacency lists for fast iteration."""
    return {v: v.neighbours for v in vertices}


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def fast_colour_refine(vertices: list,
                       adj: Dict,
                       initial_colouring: Dict) -> Partition:
    """Run fast colour refinement to a stable partition.

    Args:
        vertices:  All vertices (disjoint union).
        adj:       vertex → neighbour list.
        initial_colouring:  vertex → initial colour.

    Returns:
        The stable Partition.
    """
    partition = Partition()

    # Build initial partition
    groups: Dict[int, set] = {}
    for v in vertices:
        c = initial_colouring[v]
        if c in groups:
            groups[c].add(v)
        else:
            groups[c] = {v}

    queue: deque = deque()
    in_queue: set = set()
    for _, members in sorted(groups.items()):
        colour = partition.add_class(members)
        queue.append(colour)
        in_queue.add(colour)

    # Local aliases
    p_classes = partition.classes
    p_vc = partition.vertex_colour
    p_nc = [partition._next_colour]  # mutable ref for inline splits

    while queue:
        rc = queue.popleft()
        in_queue.discard(rc)

        refine_members = p_classes.get(rc)
        if refine_members is None:
            continue

        # === Refine(C) — tight inlined loop ===

        # Count how many neighbours each vertex has in C.
        neighbour_count: Dict = {}
        for u in refine_members:
            for w in adj[u]:
                if w in neighbour_count:
                    neighbour_count[w] += 1
                else:
                    neighbour_count[w] = 1

        # Group affected vertices by their current colour class.
        affected_by_colour: Dict[int, list] = {}
        for w in neighbour_count:
            wc = p_vc[w]
            if wc in affected_by_colour:
                affected_by_colour[wc].append(w)
            else:
                affected_by_colour[wc] = [w]

        # For each affected colour class, split if vertices disagree on count.
        for d_colour, affected_list in affected_by_colour.items():
            d_members = p_classes.get(d_colour)
            if d_members is None:
                continue

            d_size = len(d_members)
            affected_count = len(affected_list)

            # Group affected vertices by their count
            count_groups: Dict[int, list] = {}
            for v in affected_list:
                cnt = neighbour_count[v]
                if cnt in count_groups:
                    count_groups[cnt].append(v)
                else:
                    count_groups[cnt] = [v]

            unaffected_count = d_size - affected_count

            # How many distinct groups?
            num_groups = len(count_groups)
            if unaffected_count > 0:
                num_groups += 1
            if num_groups <= 1:
                continue

            # Find largest fragment to keep in original colour
            largest_key = 0  # 0 means the unaffected group
            largest_size = unaffected_count

            for cnt, grp in count_groups.items():
                gs = len(grp)
                if gs > largest_size:
                    largest_size = gs
                    largest_key = cnt

            # Perform splits
            d_in_queue = d_colour in in_queue
            nc_val = p_nc[0]

            if largest_key == 0:
                # Keep unaffected in original; split out all count groups
                for cnt, grp in count_groups.items():
                    grp_set = set(grp)
                    d_members -= grp_set
                    p_classes[nc_val] = grp_set
                    for v in grp:
                        p_vc[v] = nc_val
                    if d_in_queue or nc_val not in in_queue:
                        queue.append(nc_val)
                        in_queue.add(nc_val)
                    nc_val += 1
            else:
                # Keep the largest count group; split out rest
                if unaffected_count > 0:
                    unaff = d_members - set(affected_list)
                    d_members -= unaff
                    p_classes[nc_val] = unaff
                    for v in unaff:
                        p_vc[v] = nc_val
                    if d_in_queue or nc_val not in in_queue:
                        queue.append(nc_val)
                        in_queue.add(nc_val)
                    nc_val += 1

                for cnt, grp in count_groups.items():
                    if cnt == largest_key:
                        continue
                    grp_set = set(grp)
                    d_members -= grp_set
                    p_classes[nc_val] = grp_set
                    for v in grp:
                        p_vc[v] = nc_val
                    if d_in_queue or nc_val not in in_queue:
                        queue.append(nc_val)
                        in_queue.add(nc_val)
                    nc_val += 1

            p_nc[0] = nc_val

    partition._next_colour = p_nc[0]
    return partition


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def colour_refine_graphs(graphs: List[Graph],
                         initial_colouring: Optional[Dict] = None
                         ) -> Partition:
    """Run fast colour refinement on a list of graphs (disjoint union)."""
    all_vertices = [v for G in graphs for v in G]
    if initial_colouring is None:
        initial_colouring = {v: 0 for v in all_vertices}
    adj = _build_neighbour_index(all_vertices)
    return fast_colour_refine(all_vertices, adj, initial_colouring)


def get_colour_signature(graph: Graph, partition: Partition) -> Tuple:
    """Canonical signature: sorted (colour, count) pairs."""
    counts: Dict[int, int] = {}
    vc = partition.vertex_colour
    for v in graph:
        c = vc[v]
        counts[c] = counts.get(c, 0) + 1
    return tuple(sorted(counts.items()))


def is_balanced(graphs: List[Graph], partition: Partition) -> bool:
    """Check balanced colouring across graphs."""
    if len(graphs) < 2:
        return True
    ref = get_colour_signature(graphs[0], partition)
    for G in graphs[1:]:
        if get_colour_signature(G, partition) != ref:
            return False
    return True


def is_discrete_for_graph(graph: Graph, partition: Partition) -> bool:
    """Check if every vertex in the graph has a unique colour."""
    n = len(graph)
    seen = set()
    vc = partition.vertex_colour
    for v in graph:
        seen.add(vc[v])
    return len(seen) == n


def defines_bijection(graph_a: Graph, graph_b: Graph,
                      partition: Partition) -> bool:
    """Check if the partition defines a bijection between two graphs."""
    return (is_discrete_for_graph(graph_a, partition) and
            is_discrete_for_graph(graph_b, partition))


def basic_colorref_fast(filename: str) -> List[Tuple[List[int], List[int], int, bool]]:
    """Drop-in replacement for basic_colorref using fast colour refinement."""
    from graph_io import load_graph
    with open(filename, 'r') as file:
        graphs = load_graph(file, graph_class=Graph, read_list=True)
    all_vertices = [v for G in graphs for v in G]
    initial_colouring = {v: 0 for v in all_vertices}
    adj = _build_neighbour_index(all_vertices)
    partition = fast_colour_refine(all_vertices, adj, initial_colouring)

    eq_classes: Dict[Tuple, List[int]] = {}
    for i, G in enumerate(graphs):
        sig = get_colour_signature(G, partition)
        if sig in eq_classes:
            eq_classes[sig].append(i)
        else:
            eq_classes[sig] = [i]

    result = []
    for sig, indices in eq_classes.items():
        sizes = sorted(count for _, count in sig)
        result.append((sorted(indices), sizes, 0, all(s == 1 for s in sizes)))
    return sorted(result, key=lambda x: x[0][0])
